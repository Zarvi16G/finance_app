"""Currency conversion utilities: COP-based exchange rates.

COP is the base currency. Every foreign currency has a rate telling
how many COP one unit of that currency equals.  COP itself is 1.0.
"""
from decimal import Decimal

from ..models import CurrencyRate


def get_rate_map():
    """Return a dict of {currency_code: rate_to_cop}, including COP: 1.0."""
    rates = {'COP': Decimal('1.0')}
    for row in CurrencyRate.objects.all():
        rates[row.currency_code] = row.rate_to_cop
    return rates


def convert_to_cop(amount, currency_code):
    """Convert `amount` in `currency_code` to COP.

    If the currency is unknown / not in the rate table, the amount is
    returned unchanged (treated as COP) so the app never breaks on a
    missing rate.  Always returns a float for consistency with callers.
    """
    if currency_code is None or currency_code == 'COP':
        return float(amount)
    try:
        rate = CurrencyRate.objects.get(currency_code=currency_code).rate_to_cop
    except CurrencyRate.DoesNotExist:
        return float(amount)
    if not rate or rate == 0:
        return float(amount)
    return float(Decimal(str(amount)) * rate)


def convert_from_cop(cop_amount, currency_code):
    """Convert a COP amount back to `currency_code`."""
    if currency_code is None or currency_code == 'COP':
        return float(cop_amount)
    try:
        rate = CurrencyRate.objects.get(currency_code=currency_code).rate_to_cop
    except CurrencyRate.DoesNotExist:
        return float(cop_amount)
    if not rate or rate == 0:
        return float(cop_amount)
    return float(Decimal(str(cop_amount)) / rate)
