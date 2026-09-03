"""Monthly financial snapshot computation.

Every total here is expressed in the owner's base currency. Amounts are stored
in whatever currency they happened in, so the sums go through
`currency_service.sum_in` rather than a plain SQL Sum, which would happily add
pesos to dollars.
"""
from django.db.models import Sum, Avg, Count

from ..models import FinancialRecord, FinancialSnapshot, Debt, UserSetting
from . import currency_service

ESSENTIAL_CATEGORIES = ['Rent & Housing', 'Utilities', 'Food & Dining', 'Healthcare', 'Transportation']


def base_currency_for(user) -> str:
    """The currency this user reads their totals in."""
    setting = UserSetting.objects.filter(owner=user).only('currency').first()
    return currency_service.normalize(
        setting.currency if setting and setting.currency else currency_service.DEFAULT_BASE
    )


def compute_monthly_snapshot(date, user):
    """Compute and store one user's monthly financial snapshot."""
    snapshot, _ = FinancialSnapshot.objects.get_or_create(
        owner=user, date=date.replace(day=1)
    )

    base = base_currency_for(user)
    records = FinancialRecord.objects.filter(
        owner=user, date__year=date.year, date__month=date.month
    )

    total_income = float(currency_service.sum_in(records.filter(type='income'), base))
    total_expenses = float(currency_service.sum_in(records.filter(type='expense'), base))
    net_cash_flow = total_income - total_expenses
    savings_rate = (net_cash_flow / total_income * 100) if total_income > 0 else 0

    # Expense category breakdown, each category totalled in the base currency
    expense_records = records.filter(type='expense')
    counts = {
        row['category']: row['count']
        for row in expense_records.values('category').annotate(count=Count('id'))
    }
    category_totals = {
        category: float(currency_service.sum_in(
            expense_records.filter(category=category), base
        ))
        for category in counts
    }
    total_expense_amount = sum(category_totals.values())
    expenses_per_category = {}
    for category, cat_total in sorted(category_totals.items(), key=lambda item: -item[1]):
        count = counts[category]
        expenses_per_category[category] = {
            'total': cat_total,
            'average': round(cat_total / count, 2) if count else 0,
            'count': count,
            'percentage': round(cat_total / total_expense_amount * 100, 2) if total_expense_amount > 0 else 0
        }

    # Debts
    debts = Debt.objects.filter(owner=user, status='active')
    total_liabilities = float(currency_service.sum_in(debts, base, field='current_balance'))
    total_min_payment = float(currency_service.sum_in(debts, base, field='minimum_payment'))

    # Liquidity ratios
    current_ratio = (total_income / total_min_payment) if total_min_payment > 0 else None
    essential_expenses = float(currency_service.sum_in(
        records.filter(type='expense', category__in=ESSENTIAL_CATEGORIES), base
    ))
    quick_ratio = (total_income - essential_expenses) / total_min_payment if total_min_payment > 0 else None
    cash_ratio = current_ratio

    # Profitability ratios
    net_profit_margin = (net_cash_flow / total_income * 100) if total_income > 0 else 0
    expense_ratio = (total_expenses / total_income * 100) if total_income > 0 else 0

    # Solvency ratios
    debt_to_income = (total_min_payment / total_income * 100) if total_income > 0 else 0

    # Growth (YoY)
    prev_year = date.year - 1
    prev_records = FinancialRecord.objects.filter(
        owner=user, date__year=prev_year, date__month=date.month
    )
    prev_income = float(currency_service.sum_in(prev_records.filter(type='income'), base))
    prev_expenses = float(currency_service.sum_in(prev_records.filter(type='expense'), base))
    income_growth_yoy = ((total_income - prev_income) / prev_income * 100) if prev_income > 0 else 0
    expense_growth_yoy = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
    net_worth_growth = income_growth_yoy - expense_growth_yoy

    # Update snapshot
    snapshot.total_income = total_income
    snapshot.total_expenses = total_expenses
    snapshot.net_savings = net_cash_flow
    snapshot.savings_rate = savings_rate
    snapshot.current_ratio = round(current_ratio, 2) if current_ratio else None
    snapshot.quick_ratio = round(quick_ratio, 2) if quick_ratio else None
    snapshot.cash_ratio = round(cash_ratio, 2) if cash_ratio else None
    snapshot.net_profit_margin = round(net_profit_margin, 2)
    snapshot.expense_ratio = round(expense_ratio, 2)
    snapshot.debt_to_income = round(debt_to_income, 2)
    snapshot.income_growth_yoy = round(income_growth_yoy, 2)
    snapshot.expense_growth_yoy = round(expense_growth_yoy, 2)
    snapshot.net_worth_growth = round(net_worth_growth, 2)
    snapshot.expenses_per_category = expenses_per_category
    snapshot.total_liabilities = total_liabilities
    snapshot.net_worth = 0  # Would need asset tracking
    snapshot.save()

    return snapshot