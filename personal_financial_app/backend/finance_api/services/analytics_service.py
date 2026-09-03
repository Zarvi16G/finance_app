"""Financial analytics computation for the dashboard and ratios.

Totals are expressed in the user's base currency. Records keep the currency
they happened in, so sums go through `currency_service.sum_in` instead of a
plain SQL Sum — adding pesos to dollars would be silently wrong.
"""
import math
from datetime import timedelta

from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from ..models import FinancialRecord, FinancialSnapshot, Debt
from . import currency_service
from .snapshot_service import base_currency_for

ESSENTIAL_CATEGORIES = ['Rent & Housing', 'Utilities', 'Food & Dining', 'Healthcare', 'Transportation']


def build_dashboard_data(start_date, end_date, user):
    """Live dashboard computation for one user (when snapshots are incomplete)."""
    base = base_currency_for(user)
    records = FinancialRecord.objects.filter(
        owner=user, date__gte=start_date, date__lte=end_date
    )

    income_data = _monthly_totals(records.filter(type='income'), base)
    expense_data = _monthly_totals(records.filter(type='expense'), base)

    debts = Debt.objects.filter(owner=user, status='active')

    return {
        'period': {'start': start_date, 'end': end_date},
        'base_currency': base,
        'income_vs_expenses': format_monthly_data(income_data, expense_data),
        'expense_by_category': _totals_by_category(records.filter(type='expense'), base),
        'income_by_category': _totals_by_category(records.filter(type='income'), base),
        'monthly_trends': get_monthly_trends(records, start_date, end_date, base),
        'financial_ratios': calculate_financial_ratios(records, start_date, end_date, user, base),
        'debt_summary': get_debt_summary(debts, base),
        'summary': get_summary_stats(records, base),
    }


def _monthly_totals(records, base):
    """[{month, total}] in the base currency, one conversion per month+currency."""
    rows = (
        records.annotate(month=TruncMonth('date'))
        .values('month', 'currency')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    per_month = {}
    for row in rows:
        converted = currency_service.convert_safe(
            row['total'] or 0, row['currency'] or base, base
        )
        per_month[row['month']] = per_month.get(row['month'], 0) + float(converted)
    return [
        {'month': month, 'total': total}
        for month, total in sorted(per_month.items())
    ]


def _totals_by_category(records, base):
    """[{category, total, count}] in the base currency, biggest first."""
    rows = (
        records.values('category', 'currency')
        .annotate(total=Sum('amount'), count=Count('id'))
    )
    totals, counts = {}, {}
    for row in rows:
        category = row['category']
        converted = currency_service.convert_safe(
            row['total'] or 0, row['currency'] or base, base
        )
        totals[category] = totals.get(category, 0) + float(converted)
        counts[category] = counts.get(category, 0) + row['count']
    return [
        {'category': category, 'total': round(total, 2), 'count': counts[category]}
        for category, total in sorted(totals.items(), key=lambda item: -item[1])
    ]


def build_dashboard_from_snapshots(start_date, end_date, user):
    """Build one user's dashboard response from pre-computed monthly snapshots.

    Returns None if not all months in range have snapshots.
    """
    months = []
    current = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    while current <= end_month:
        months.append(current)
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    snapshots = list(
        FinancialSnapshot.objects.filter(owner=user, date__in=months).order_by('date')
    )
    if len(snapshots) != len(months):
        return None

    # Aggregate totals across all snapshots
    total_income = sum(float(s.total_income) for s in snapshots)
    total_expenses = sum(float(s.total_expenses) for s in snapshots)
    net_cash_flow = total_income - total_expenses
    total_other = 0

    # Build monthly trends
    monthly_trends = []
    income_vs_expenses = []
    for s in snapshots:
        month_key = s.date.strftime('%Y-%m')
        income = float(s.total_income)
        expenses = float(s.total_expenses)
        net = income - expenses
        monthly_trends.append({'month': month_key, 'income': income, 'expenses': expenses, 'net': net})
        income_vs_expenses.append({'month': month_key, 'income': income, 'expenses': expenses, 'net': net})

    # Aggregate category breakdowns from all snapshots
    cat_totals = {}
    cat_counts = {}
    for s in snapshots:
        for category, data in s.expenses_per_category.items():
            cat_totals[category] = cat_totals.get(category, 0) + data['total']
            cat_counts[category] = cat_counts.get(category, 0) + data['count']
    expense_by_category = [
        {'category': cat, 'total': round(total, 2), 'count': cat_counts[cat]}
        for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1])
    ]

    # Compute financial ratios from aggregate. Snapshot totals are already in
    # the base currency; debts still have to be converted from their own.
    base = base_currency_for(user)
    total_min_payment = float(currency_service.sum_in(
        Debt.objects.filter(owner=user, status='active'), base, field='minimum_payment'
    ))
    current_ratio = total_income / total_min_payment if total_min_payment > 0 else None
    essential_total = sum(
        cat_totals.get(cat, 0) for cat in ESSENTIAL_CATEGORIES
    )
    quick_ratio = (total_income - essential_total) / total_min_payment if total_min_payment > 0 else None
    cash_ratio = current_ratio
    net_profit_margin = (net_cash_flow / total_income * 100) if total_income > 0 else 0
    savings_rate = (net_cash_flow / total_income * 100) if total_income > 0 else 0
    expense_ratio = (total_expenses / total_income * 100) if total_income > 0 else 0
    debt_to_income = (total_min_payment / total_income * 100) if total_income > 0 else 0

    # YoY growth from first snapshot vs year before
    first_snap = snapshots[0]
    prev_date = first_snap.date.replace(year=first_snap.date.year - 1)
    prev_snap = FinancialSnapshot.objects.filter(owner=user, date=prev_date).first()
    if prev_snap:
        prev_income = float(prev_snap.total_income)
        prev_expenses = float(prev_snap.total_expenses)
    else:
        prev_year_start = first_snap.date.replace(year=first_snap.date.year - 1)
        prev_year_end = (prev_year_start.replace(day=1) + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        prev_records = FinancialRecord.objects.filter(
            owner=user, date__gte=prev_year_start, date__lte=prev_year_end
        )
        prev_income = float(currency_service.sum_in(prev_records.filter(type='income'), base))
        prev_expenses = float(currency_service.sum_in(prev_records.filter(type='expense'), base))
    income_growth_yoy = ((total_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
    expense_growth_yoy = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
    net_worth_growth = income_growth_yoy - expense_growth_yoy

    # Build operational efficiency
    total_expense_amt = sum(cat_totals.values())
    ops_efficiency = {}
    for cat, total in cat_totals.items():
        ops_efficiency[cat] = {
            'total': round(total, 2),
            'average': round(total / cat_counts[cat], 2) if cat_counts[cat] > 0 else 0,
            'count': cat_counts[cat],
            'percentage': round(total / total_expense_amt * 100, 2) if total_expense_amt > 0 else 0
        }

    return {
        'period': {'start': start_date, 'end': end_date},
        'base_currency': base,
        'income_vs_expenses': income_vs_expenses,
        'expense_by_category': expense_by_category,
        'income_by_category': [],
        'monthly_trends': monthly_trends,
        'financial_ratios': {
            'liquidity': {
                'current_ratio': round(current_ratio, 2) if current_ratio else None,
                'quick_ratio': round(quick_ratio, 2) if quick_ratio else None,
                'cash_ratio': round(cash_ratio, 2) if cash_ratio else None,
            },
            'profitability': {
                'net_profit_margin': round(net_profit_margin, 2),
                'savings_rate': round(savings_rate, 2),
                'expense_ratio': round(expense_ratio, 2),
            },
            'solvency': {
                'debt_to_income': round(debt_to_income, 2),
                'debt_to_asset': None,
            },
            'growth': {
                'income_growth_yoy': round(income_growth_yoy, 2),
                'expense_growth_yoy': round(expense_growth_yoy, 2),
                'net_worth_growth': round(net_worth_growth, 2),
            },
            'operational_efficiency': {
                'expenses_per_category': ops_efficiency,
            }
        },
        'summary': {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'total_other': total_other,
            'net_cash_flow': net_cash_flow,
            'savings_rate': round(savings_rate, 2),
        },
    }


def get_monthly_trends(records, start_date, end_date, base):
    """Get monthly income/expense trends, totalled in the base currency."""
    monthly = records.annotate(month=TruncMonth('date')).values(
        'month', 'type', 'currency'
    ).annotate(total=Sum('amount')).order_by('month')

    # Organize by month
    month_map = {}
    for item in monthly:
        month_key = item['month'].strftime('%Y-%m')
        if month_key not in month_map:
            month_map[month_key] = {'income': 0, 'expenses': 0, 'net': 0}
        amount = float(currency_service.convert_safe(
            item['total'] or 0, item['currency'] or base, base
        ))
        if item['type'] == 'income':
            month_map[month_key]['income'] += amount
        else:
            month_map[month_key]['expenses'] += amount

    # Calculate net
    for month in month_map:
        month_map[month]['net'] = month_map[month]['income'] - month_map[month]['expenses']

    return [{'month': k, **v} for k, v in sorted(month_map.items())]


def calculate_financial_ratios(records, start_date, end_date, user, base):
    """Calculate key financial health ratios for one user, in `base`."""
    total_income = float(currency_service.sum_in(records.filter(type='income'), base))
    total_expenses = float(currency_service.sum_in(records.filter(type='expense'), base))
    net_cash_flow = total_income - total_expenses

    # Get active debts
    debts = Debt.objects.filter(owner=user, status='active')
    total_debt = float(currency_service.sum_in(debts, base, field='current_balance'))
    total_min_payment = float(currency_service.sum_in(debts, base, field='minimum_payment'))

    # Liquidity ratios (simplified - using cash flow as proxy)
    # Current ratio: current assets / current liabilities
    # For personal finance: monthly income / monthly debt payments
    current_ratio = total_income / total_min_payment if total_min_payment > 0 else None

    # Quick ratio: (cash + receivables) / current liabilities
    # Simplified: (income - essential expenses) / debt payments
    essential_expenses = float(currency_service.sum_in(
        records.filter(type='expense', category__in=ESSENTIAL_CATEGORIES), base
    ))

    quick_ratio = (total_income - essential_expenses) / total_min_payment if total_min_payment > 0 else None

    # Cash ratio: cash / current liabilities
    cash_ratio = total_income / total_min_payment if total_min_payment > 0 else None

    # Profitability
    net_profit_margin = (net_cash_flow / total_income * 100) if total_income > 0 else 0
    savings_rate = (net_cash_flow / total_income * 100) if total_income > 0 else 0
    expense_ratio = (total_expenses / total_income * 100) if total_income > 0 else 0

    # Solvency
    debt_to_income = (total_min_payment / total_income * 100) if total_income > 0 else 0
    debt_to_asset = None  # Would need asset tracking

    # Growth (YoY comparison)
    current_year = timezone.now().year
    prev_year_start = start_date.replace(year=current_year - 1)
    prev_year_end = end_date.replace(year=current_year - 1)

    prev_records = FinancialRecord.objects.filter(
        owner=user, date__gte=prev_year_start, date__lte=prev_year_end
    )
    prev_income = float(currency_service.sum_in(prev_records.filter(type='income'), base))
    prev_expenses = float(currency_service.sum_in(prev_records.filter(type='expense'), base))

    income_growth_yoy = ((total_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
    expense_growth_yoy = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0

    # Net worth growth (simplified)
    net_worth_growth = income_growth_yoy - expense_growth_yoy

    return {
        'liquidity': {
            'current_ratio': round(current_ratio, 2) if current_ratio else None,
            'quick_ratio': round(quick_ratio, 2) if quick_ratio else None,
            'cash_ratio': round(cash_ratio, 2) if cash_ratio else None,
        },
        'profitability': {
            'net_profit_margin': round(net_profit_margin, 2),
            'savings_rate': round(savings_rate, 2),
            'expense_ratio': round(expense_ratio, 2),
        },
        'solvency': {
            'debt_to_income': round(debt_to_income, 2),
            'debt_to_asset': round(debt_to_asset, 2) if debt_to_asset else None,
        },
        'growth': {
            'income_growth_yoy': round(income_growth_yoy, 2),
            'expense_growth_yoy': round(expense_growth_yoy, 2),
            'net_worth_growth': round(net_worth_growth, 2),
        },
        'operational_efficiency': {
            'expenses_per_category': get_expenses_per_category(records, base),
        }
    }


def get_expenses_per_category(records, base):
    """Get expense breakdown by category, totalled in the base currency."""
    rows = _totals_by_category(records.filter(type='expense'), base)
    total = sum(row['total'] for row in rows)

    result = {}
    for row in rows:
        result[row['category']] = {
            'total': row['total'],
            'average': round(row['total'] / row['count'], 2) if row['count'] else 0,
            'count': row['count'],
            'percentage': round(row['total'] / total * 100, 2) if total > 0 else 0
        }

    return result


def get_debt_summary(debts, base):
    """Get summary of all active debts, totalled in the base currency."""
    total_balance = float(currency_service.sum_in(debts, base, field='current_balance'))
    total_min_payment = float(currency_service.sum_in(debts, base, field='minimum_payment'))
    total_interest = sum(
        float(currency_service.convert_safe(d.monthly_interest, d.currency or base, base))
        for d in debts
    )

    by_type = {}
    for debt in debts:
        if debt.debt_type not in by_type:
            by_type[debt.debt_type] = {'count': 0, 'total_balance': 0}
        by_type[debt.debt_type]['count'] += 1
        by_type[debt.debt_type]['total_balance'] += float(
            currency_service.convert_safe(debt.current_balance, debt.currency or base, base)
        )

    return {
        'total_debts': debts.count(),
        'base_currency': base,
        'total_balance': total_balance,
        'total_monthly_payment': total_min_payment,
        'total_monthly_interest': total_interest,
        'by_type': by_type,
        'payoff_timeline': estimate_payoff_timeline(debts, base),
    }


def estimate_payoff_timeline(debts, base):
    """Estimate debt payoff timeline using avalanche method.

    The payoff maths stay in each debt's own currency — mixing a peso balance
    with a dollar payment would be nonsense — and only the reported figures
    are expressed in the base currency.
    """
    # Sort by interest rate (avalanche)
    sorted_debts = sorted(debts, key=lambda d: float(d.interest_rate), reverse=True)

    timeline = []
    extra_payment = 0  # Could be calculated from budget surplus

    for debt in sorted_debts:
        balance = float(debt.current_balance)
        rate = float(debt.interest_rate) / 100 / 12  # Monthly rate
        min_pay = float(debt.minimum_payment)

        if balance <= 0:
            continue

        payment = min_pay + extra_payment
        if payment <= balance * rate:
            months = float('inf')
        else:
            months = math.log(payment / (payment - balance * rate)) / math.log(1 + rate)

        source = debt.currency or base
        total_interest = balance * rate * months if months != float('inf') else None
        timeline.append({
            'debt_id': str(debt.id),
            'name': debt.name,
            'type': debt.debt_type,
            'currency': source,
            'balance': float(currency_service.convert_safe(balance, source, base)),
            'interest_rate': float(debt.interest_rate),
            'minimum_payment': float(currency_service.convert_safe(min_pay, source, base)),
            'estimated_months': round(months, 1) if months != float('inf') else None,
            'total_interest': (
                float(currency_service.convert_safe(total_interest, source, base))
                if total_interest is not None else None
            ),
        })

        # After this debt is paid, add its payment to extra
        extra_payment += min_pay

    return timeline


def get_summary_stats(records, base):
    """Get summary statistics, totalled in the base currency."""
    income = records.filter(type='income')
    expenses = records.filter(type='expense')
    total_income = float(currency_service.sum_in(income, base))
    total_expenses = float(currency_service.sum_in(expenses, base))
    total_other = float(currency_service.sum_in(
        records.exclude(type__in=['income', 'expense']), base
    ))
    net = total_income - total_expenses

    # Averages are derived from the converted totals rather than a SQL Avg,
    # which would average across currencies.
    income_count = income.count()
    expense_count = expenses.count()

    return {
        'base_currency': base,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_other': total_other,
        'net_cash_flow': net,
        'savings_rate': round(net / total_income * 100, 2) if total_income > 0 else 0,
        'transaction_count': records.count(),
        'avg_income': round(total_income / income_count, 2) if income_count else 0,
        'avg_expense': round(total_expenses / expense_count, 2) if expense_count else 0,
    }


def format_monthly_data(income_data, expense_data):
    """Format monthly income/expense data for charts."""
    months = {}
    for item in income_data:
        month = item['month']
        if month not in months:
            months[month] = {'income': 0, 'expenses': 0}
        months[month]['income'] = float(item['total'])

    for item in expense_data:
        month = item['month']
        if month not in months:
            months[month] = {'income': 0, 'expenses': 0}
        months[month]['expenses'] = float(item['total'])

    return [
        {'month': k, 'income': v['income'], 'expenses': v['expenses'], 'net': v['income'] - v['expenses']}
        for k, v in sorted(months.items())
    ]