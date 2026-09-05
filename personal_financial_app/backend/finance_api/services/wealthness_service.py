"""Wealthness — how the user's finances are actually doing.

This adds no new data. It reads what the other domains already record
(records, debts, assets, snapshots) and answers four questions:

  Is money coming in faster than it goes out?   -> net flow
  Is the overall picture improving?             -> net worth trend
  How much of what comes in is kept?            -> savings rate
  How long could you survive with no income?    -> emergency fund

A note on the thresholds below: they are the conventional rules of thumb of
personal finance (three to six months of expenses saved; a debt-to-income
ratio under 36%), not results derived from this user's data. They are stated
explicitly, in one place, so they can be argued with and changed — rather
than hidden inside a single opaque "score" that would imply more precision
than any of this has.
"""
from datetime import date
from decimal import Decimal

from ..models import Asset, FinancialRecord, FinancialSnapshot
from . import currency_service, patrimony_service
from .snapshot_service import ESSENTIAL_CATEGORIES

# Months of essential spending covered by liquid assets.
EMERGENCY_FUND_BANDS = [
    (Decimal('6'), 'strong', 'Six months or more of essentials covered.'),
    (Decimal('3'), 'adequate', 'Three to six months covered — the usual target.'),
    (Decimal('1'), 'low', 'Under three months. A single setback would hurt.'),
    (Decimal('0'), 'critical', 'Under one month of cover.'),
]

# Share of income kept.
SAVINGS_RATE_BANDS = [
    (Decimal('20'), 'strong', 'Keeping a fifth or more of income.'),
    (Decimal('10'), 'adequate', 'Keeping between a tenth and a fifth.'),
    (Decimal('0'), 'low', 'Keeping less than a tenth.'),
]

# Minimum debt payments as a share of income. 36% is the long-standing
# mortgage-underwriting comfort line; 43% is where lenders usually stop.
DEBT_TO_INCOME_BANDS = [
    (Decimal('43'), 'critical', 'Above the level most lenders will accept.'),
    (Decimal('36'), 'high', 'Above the usual comfort line of 36%.'),
    (Decimal('0'), 'healthy', 'Within the usual comfort line.'),
]

# How much net worth must move before it counts as a direction rather than
# noise, over the whole window.
TREND_THRESHOLD_PCT = Decimal('2')

# Months of history used to average out a one-off month.
LOOKBACK_MONTHS = 6


def _band(value, bands, default=('unknown', 'Not enough data yet.')):
    """First band whose floor the value clears."""
    if value is None:
        return {'status': default[0], 'note': default[1]}
    value = Decimal(str(value))
    for floor, status, note in bands:
        if value >= floor:
            return {'status': status, 'note': note}
    return {'status': default[0], 'note': default[1]}


def _months_back(reference: date, months: int) -> date:
    """First day of the month `months` before `reference`."""
    total = reference.year * 12 + (reference.month - 1) - months
    return date(total // 12, total % 12 + 1, 1)


def average_monthly_expenses(user, base: str, essential_only: bool = True,
                             months: int = LOOKBACK_MONTHS, today: date = None) -> Decimal:
    """Mean monthly spend over the recent past.

    Averaged rather than taken from the latest month so one unusual month —
    a flight booked, a deposit paid — does not swing the whole picture.
    """
    today = today or date.today()
    start = _months_back(today, months)
    records = FinancialRecord.objects.filter(
        owner=user, type='expense', date__gte=start, date__lte=today
    )
    if essential_only:
        records = records.filter(category__in=ESSENTIAL_CATEGORIES)

    total = currency_service.sum_in(records, base)
    return (total / Decimal(months)) if months else Decimal('0')


def emergency_fund(user, base: str, today: date = None) -> dict:
    """How long the liquid assets would last with no income at all."""
    liquid = currency_service.sum_in(
        Asset.objects.filter(owner=user, is_liquid=True),
        base, field='current_value',
    )
    monthly = average_monthly_expenses(user, base, essential_only=True, today=today)

    months_covered = None
    if monthly > 0:
        months_covered = (liquid / monthly).quantize(Decimal('0.01'))

    return {
        'liquid_assets': float(liquid),
        'avg_monthly_essentials': float(monthly),
        'months_covered': float(months_covered) if months_covered is not None else None,
        # Without spending history there is nothing to divide by, so the
        # honest answer is "unknown", not "infinite cover".
        **_band(months_covered, EMERGENCY_FUND_BANDS,
                default=('unknown', 'No recorded spending yet to measure against.')),
    }


def net_flow_series(user, base: str, months: int = 12, today: date = None) -> list[dict]:
    """Monthly income, expenses and the difference, in the base currency."""
    today = today or date.today()
    start = _months_back(today, months - 1)
    snapshots = FinancialSnapshot.objects.filter(
        owner=user, date__gte=start
    ).order_by('date')

    return [
        {
            'month': snap.date.strftime('%Y-%m'),
            'income': float(snap.total_income),
            'expenses': float(snap.total_expenses),
            'net': float(snap.net_savings),
            'net_worth': float(snap.net_worth),
        }
        for snap in snapshots
    ]


def trend(series: list[dict]) -> dict:
    """Which way the net worth is moving across the window.

    Falls back to cumulative net flow when there is no asset data, so the
    answer is still meaningful for someone who tracks spending but has not
    entered what they own.
    """
    if len(series) < 2:
        return {
            'direction': 'unknown',
            'change_pct': None,
            'basis': None,
            'note': 'At least two months of history are needed to see a direction.',
        }

    first, last = series[0], series[-1]
    basis = 'net_worth'
    start_value, end_value = first['net_worth'], last['net_worth']

    if start_value == 0 and end_value == 0:
        basis = 'net_flow'
        start_value = first['net']
        end_value = sum(row['net'] for row in series)

    if start_value == 0:
        # No baseline to compare against: report the direction only.
        change_pct = None
        direction = 'growing' if end_value > 0 else 'declining' if end_value < 0 else 'stable'
    else:
        change_pct = round((end_value - start_value) / abs(start_value) * 100, 2)
        if Decimal(str(change_pct)) > TREND_THRESHOLD_PCT:
            direction = 'growing'
        elif Decimal(str(change_pct)) < -TREND_THRESHOLD_PCT:
            direction = 'declining'
        else:
            direction = 'stable'

    return {
        'direction': direction,
        'change_pct': change_pct,
        'basis': basis,
        'from': first['month'],
        'to': last['month'],
        'note': (
            'Measured on net worth.' if basis == 'net_worth'
            else 'No assets recorded, so measured on cumulative net flow instead.'
        ),
    }


def overview(user, base: str, months: int = 12, today: date = None) -> dict:
    """The full Wealthness picture."""
    today = today or date.today()
    series = net_flow_series(user, base, months=months, today=today)

    # Savings rate over the window: what share of everything earned was kept.
    total_income = sum(row['income'] for row in series)
    total_expenses = sum(row['expenses'] for row in series)
    net = total_income - total_expenses
    savings_rate = round(net / total_income * 100, 2) if total_income > 0 else None

    patrimony = patrimony_service.summary_for(user, base)
    latest = series[-1] if series else None

    # Debt-to-income on the most recent month with income.
    debt_to_income = None
    recent = FinancialSnapshot.objects.filter(owner=user).order_by('-date').first()
    if recent is not None and recent.debt_to_income is not None:
        debt_to_income = float(recent.debt_to_income)

    return {
        'base_currency': base,
        'period': {'months': months, 'from': series[0]['month'] if series else None,
                   'to': series[-1]['month'] if series else None},
        'net_flow': {
            'series': series,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net': net,
            'latest_month_net': latest['net'] if latest else None,
        },
        'trend': trend(series),
        'savings_rate': {
            'value': savings_rate,
            **_band(savings_rate, SAVINGS_RATE_BANDS,
                    default=('unknown', 'No income recorded in this period.')),
        },
        'emergency_fund': emergency_fund(user, base, today=today),
        'debt_load': {
            'debt_to_income': debt_to_income,
            **_band(
                debt_to_income, DEBT_TO_INCOME_BANDS,
                default=('unknown', 'No snapshot with income yet.'),
            ),
        },
        'net_worth': {
            'current': patrimony['net_worth'],
            'total_assets': patrimony['total_assets'],
            'total_liabilities': patrimony['total_liabilities'],
            'liquid_assets': patrimony['liquid_assets'],
        },
    }
