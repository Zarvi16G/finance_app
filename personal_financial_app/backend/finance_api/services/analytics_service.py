"""Financial analytics computation for the dashboard and ratios."""
import math
from datetime import timedelta

from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from ..models import FinancialRecord, FinancialSnapshot, Debt
from ..services.currency import convert_to_cop, get_rate_map

ESSENTIAL_CATEGORIES = ['Rent & Housing', 'Utilities', 'Food & Dining', 'Healthcare', 'Transportation']


def build_dashboard_data(owner, start_date, end_date):
    """Live dashboard computation (used when snapshots are incomplete)."""
    records = FinancialRecord.objects.filter(owner=owner, date__gte=start_date, date__lte=end_date)

    income_data = records.filter(type='income').annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    expense_data = records.filter(type='expense').annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    expense_by_category = records.filter(type='expense').values('category').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    income_by_category = records.filter(type='income').values('category').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')

    debts = Debt.objects.filter(owner=owner, status='active')

    return {
        'period': {'start': start_date, 'end': end_date},
        'income_vs_expenses': format_monthly_data(income_data, expense_data),
        'expense_by_category': list(expense_by_category),
        'income_by_category': list(income_by_category),
        'monthly_trends': get_monthly_trends(records, start_date, end_date),
        'financial_ratios': calculate_financial_ratios(owner, records, start_date, end_date),
        'debt_summary': get_debt_summary(debts),
        'summary': get_summary_stats(records),
    }


def build_dashboard_from_snapshots(owner, start_date, end_date):
    """Build dashboard response from pre-computed monthly snapshots.

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

    snapshots = list(FinancialSnapshot.objects.filter(owner=owner, date__in=months).order_by('date'))
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

    # Compute financial ratios from aggregate
    total_min_payment = sum(
        convert_to_cop(float(d.minimum_payment), d.currency or 'COP')
        for d in Debt.objects.filter(owner=owner, status='active')
    )
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
    prev_snap = FinancialSnapshot.objects.filter(owner=owner, date=prev_date).first()
    if prev_snap:
        prev_income = float(prev_snap.total_income)
        prev_expenses = float(prev_snap.total_expenses)
    else:
        prev_year_start = first_snap.date.replace(year=first_snap.date.year - 1)
        prev_year_end = (prev_year_start.replace(day=1) + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        prev_records = FinancialRecord.objects.filter(
            owner=owner, date__gte=prev_year_start, date__lte=prev_year_end
        )
        prev_income = float(prev_records.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0)
        prev_expenses = float(prev_records.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0)
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


def get_monthly_trends(records, start_date, end_date):
    """Get monthly income/expense trends."""
    monthly = records.annotate(month=TruncMonth('date')).values('month', 'type').annotate(
        total=Sum('amount')
    ).order_by('month')

    # Organize by month
    month_map = {}
    for item in monthly:
        month_key = item['month'].strftime('%Y-%m')
        if month_key not in month_map:
            month_map[month_key] = {'income': 0, 'expenses': 0, 'net': 0}
        if item['type'] == 'income':
            month_map[month_key]['income'] = float(item['total'])
        else:
            month_map[month_key]['expenses'] = float(item['total'])

    # Calculate net
    for month in month_map:
        month_map[month]['net'] = month_map[month]['income'] - month_map[month]['expenses']

    return [{'month': k, **v} for k, v in sorted(month_map.items())]


def calculate_financial_ratios(owner, records, start_date, end_date):
    """Calculate key financial health ratios."""
    total_income = float(records.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0)
    total_expenses = float(records.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0)
    net_cash_flow = total_income - total_expenses

    # Get active debts
    debts = Debt.objects.filter(owner=owner, status='active')
    total_debt = sum(
        convert_to_cop(float(d.current_balance), d.currency or 'COP') for d in debts
    )
    total_min_payment = sum(
        convert_to_cop(float(d.minimum_payment), d.currency or 'COP') for d in debts
    )

    # Liquidity ratios (simplified - using cash flow as proxy)
    # Current ratio: current assets / current liabilities
    # For personal finance: monthly income / monthly debt payments
    current_ratio = total_income / total_min_payment if total_min_payment > 0 else None

    # Quick ratio: (cash + receivables) / current liabilities
    # Simplified: (income - essential expenses) / debt payments
    essential_expenses = float(records.filter(
        type='expense', category__in=ESSENTIAL_CATEGORIES
    ).aggregate(Sum('amount'))['amount__sum'] or 0)

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
        owner=owner, date__gte=prev_year_start, date__lte=prev_year_end
    )
    prev_income = float(prev_records.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0)
    prev_expenses = float(prev_records.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0)

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
            'expenses_per_category': get_expenses_per_category(records),
        }
    }


def get_expenses_per_category(records):
    """Get expense breakdown by category for operational efficiency."""
    expenses = records.filter(type='expense').values('category').annotate(
        total=Sum('amount'),
        avg=Avg('amount'),
        count=Count('id')
    ).order_by('-total')

    total = sum(float(e['total']) for e in expenses)

    result = {}
    for e in expenses:
        cat_total = float(e['total'])
        result[e['category']] = {
            'total': cat_total,
            'average': float(e['avg']),
            'count': e['count'],
            'percentage': round(cat_total / total * 100, 2) if total > 0 else 0
        }

    return result


def get_debt_summary(debts):
    """Get summary of all active debts, grouped by currency.

    COP-converted totals are computed for the flat aggregate fields so
    that mixed-currency debts are not summed naively.  The per-currency
    breakdown preserves native amounts for each currency chart.
    """
    currencies = set(d.currency or 'COP' for d in debts)
    has_multiple_currencies = len(currencies) > 1

    total_balance_cop = sum(
        convert_to_cop(float(d.current_balance), d.currency or 'COP') for d in debts
    )
    total_min_payment_cop = sum(
        convert_to_cop(float(d.minimum_payment), d.currency or 'COP') for d in debts
    )
    total_interest_cop = sum(
        convert_to_cop(float(d.monthly_interest), d.currency or 'COP') for d in debts
    )

    # Per-currency native breakdown (no conversion within each bucket)
    by_currency = {}
    by_currency_cop = {}
    for debt in debts:
        curr = debt.currency or 'COP'
        if curr not in by_currency:
            by_currency[curr] = {'count': 0, 'total_balance': 0, 'total_monthly_payment': 0, 'total_monthly_interest': 0}
            by_currency_cop[curr] = {'total_balance': 0, 'total_monthly_payment': 0, 'total_monthly_interest': 0}
        by_currency[curr]['count'] += 1
        by_currency[curr]['total_balance'] += float(debt.current_balance)
        by_currency[curr]['total_monthly_payment'] += float(debt.minimum_payment)
        by_currency[curr]['total_monthly_interest'] += float(debt.monthly_interest)
        by_currency_cop[curr]['total_balance'] += float(convert_to_cop(float(debt.current_balance), curr))
        by_currency_cop[curr]['total_monthly_payment'] += float(convert_to_cop(float(debt.minimum_payment), curr))
        by_currency_cop[curr]['total_monthly_interest'] += float(convert_to_cop(float(debt.monthly_interest), curr))

    by_type = {}
    for debt in debts:
        if debt.debt_type not in by_type:
            by_type[debt.debt_type] = {'count': 0, 'total_balance': 0, 'currency': debt.currency or 'COP'}
        by_type[debt.debt_type]['count'] += 1
        by_type[debt.debt_type]['total_balance'] += float(debt.current_balance)

    return {
        'total_debts': debts.count(),
        'total_balance': total_balance_cop if has_multiple_currencies else sum(float(d.current_balance) for d in debts),
        'total_monthly_payment': total_min_payment_cop if has_multiple_currencies else sum(float(d.minimum_payment) for d in debts),
        'total_monthly_interest': total_interest_cop if has_multiple_currencies else sum(float(d.monthly_interest) for d in debts),
        'has_multiple_currencies': has_multiple_currencies,
        'active_currencies': sorted(currencies),
        'exchange_rates': get_rate_map(),
        'by_currency': by_currency,
        'by_currency_cop': by_currency_cop,
        'by_type': by_type,
        'payoff_timeline': estimate_payoff_timeline(debts),
    }


def estimate_payoff_timeline(debts):
    """Estimate debt payoff timeline using avalanche method."""
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
        if rate == 0:
            # No interest: simple linear payoff
            if payment <= 0:
                months = float('inf')
            else:
                months = balance / payment
        elif payment <= balance * rate:
            months = float('inf')
        else:
            months = math.log(payment / (payment - balance * rate)) / math.log(1 + rate)

        timeline.append({
            'debt_id': str(debt.id),
            'name': debt.name,
            'type': debt.debt_type,
            'currency': debt.currency or 'COP',
            'balance': balance,
            'interest_rate': float(debt.interest_rate),
            'minimum_payment': min_pay,
            'estimated_months': round(months, 1) if months != float('inf') else None,
            'total_interest': round(balance * rate * months, 2) if months != float('inf') else None,
        })

        # After this debt is paid, add its payment to extra
        extra_payment += min_pay

    return timeline


def get_summary_stats(records):
    """Get summary statistics."""
    total_income = float(records.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0)
    total_expenses = float(records.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0)
    total_other = float(records.exclude(type__in=['income', 'expense']).aggregate(Sum('amount'))['amount__sum'] or 0)
    net = total_income - total_expenses

    return {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_other': total_other,
        'net_cash_flow': net,
        'savings_rate': round(net / total_income * 100, 2) if total_income > 0 else 0,
        'transaction_count': records.count(),
        'avg_income': float(records.filter(type='income').aggregate(Avg('amount'))['amount__avg'] or 0),
        'avg_expense': float(records.filter(type='expense').aggregate(Avg('amount'))['amount__avg'] or 0),
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