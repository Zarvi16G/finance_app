"""Monthly financial snapshot computation."""
from django.db.models import Sum, Avg, Count

from ..models import FinancialRecord, FinancialSnapshot, Debt

ESSENTIAL_CATEGORIES = ['Rent & Housing', 'Utilities', 'Food & Dining', 'Healthcare', 'Transportation']


def compute_monthly_snapshot(date):
    """Compute and store a complete monthly financial snapshot."""
    snapshot, _ = FinancialSnapshot.objects.get_or_create(date=date.replace(day=1))

    records = FinancialRecord.objects.filter(
        date__year=date.year, date__month=date.month
    )

    total_income = float(records.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0)
    total_expenses = float(records.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0)
    net_cash_flow = total_income - total_expenses
    savings_rate = (net_cash_flow / total_income * 100) if total_income > 0 else 0

    # Expense category breakdown
    expenses = records.filter(type='expense').values('category').annotate(
        total=Sum('amount'),
        avg=Avg('amount'),
        count=Count('id')
    ).order_by('-total')
    total_expense_amount = sum(float(e['total']) for e in expenses)
    expenses_per_category = {}
    for e in expenses:
        cat_total = float(e['total'])
        expenses_per_category[e['category']] = {
            'total': cat_total,
            'average': float(e['avg']),
            'count': e['count'],
            'percentage': round(cat_total / total_expense_amount * 100, 2) if total_expense_amount > 0 else 0
        }

    # Debts
    debts = Debt.objects.filter(status='active')
    total_liabilities = sum(float(d.current_balance) for d in debts)
    total_min_payment = sum(float(d.minimum_payment) for d in debts)

    # Liquidity ratios
    current_ratio = (total_income / total_min_payment) if total_min_payment > 0 else None
    essential_expenses = float(records.filter(
        type='expense', category__in=ESSENTIAL_CATEGORIES
    ).aggregate(Sum('amount'))['amount__sum'] or 0)
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
        date__year=prev_year, date__month=date.month
    )
    prev_income = float(prev_records.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0)
    prev_expenses = float(prev_records.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0)
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