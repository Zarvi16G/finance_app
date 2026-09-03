"""Exchange rates and money conversion.

Provider
--------
Rates come from ExchangeRate-API's free tier, reached through a small seam
(`_PROVIDERS`) so a different source can be dropped in without touching any
caller. The API key lives in the environment, not in a user's settings row:
the USD->COP rate is the same for everybody, so one server-wide key and one
shared cache serve every account. (Contrast with the AI keys, which are
per user because each person spends their own quota.)

Caching
-------
A rate is fetched at most once per base currency per day and stored in
ExchangeRate. The free tier is metered and rates only move daily, so a
dashboard render must never reach the network.

Money
-----
Every amount is a Decimal, converted with ROUND_HALF_EVEN and quantized to
the target currency's own decimal places. Rounding half up on every
conversion biases totals upward over thousands of rows; half-even does not.
"""
import logging
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_EVEN

import requests
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from ..models import Currency, ExchangeRate

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
DEFAULT_BASE = 'COP'

# How long a stored rate is served before we try the provider again.
RATE_TTL = timedelta(days=1)

# How stale a rate may be and still be used when the provider is unreachable.
# Better a slightly old rate than a dashboard that will not render.
STALE_RATE_LIMIT = timedelta(days=14)


class ExchangeRateUnavailable(Exception):
    """No usable rate: nothing cached and the provider could not be reached."""


# --- Providers ----------------------------------------------------------

def _fetch_exchangerate_api(base: str) -> tuple[dict, str]:
    """ExchangeRate-API v6. Returns ({target: rate}, rate_date_iso)."""
    api_key = getattr(settings, 'EXCHANGERATE_API_KEY', '')
    if not api_key:
        raise ExchangeRateUnavailable(
            'EXCHANGERATE_API_KEY is not set — cannot refresh exchange rates.'
        )

    response = requests.get(
        f'https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}',
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code != 200:
        raise ExchangeRateUnavailable(
            f'Exchange rate provider returned HTTP {response.status_code}.'
        )

    payload = response.json()
    if payload.get('result') != 'success':
        raise ExchangeRateUnavailable(
            f"Exchange rate provider error: {payload.get('error-type', 'unknown')}."
        )

    rates = payload.get('conversion_rates') or {}
    if not rates:
        raise ExchangeRateUnavailable('Exchange rate provider returned no rates.')

    # The provider reports its own publication timestamp; fall back to today.
    day = timezone.now().date()
    return rates, day.isoformat()


# Add a provider by writing a function with this signature and registering it
# here, then pointing FX_PROVIDER at its name.
_PROVIDERS = {
    'exchangerate-api': _fetch_exchangerate_api,
}


def _provider():
    name = getattr(settings, 'FX_PROVIDER', 'exchangerate-api')
    try:
        return name, _PROVIDERS[name]
    except KeyError:
        raise ExchangeRateUnavailable(f'Unknown FX_PROVIDER: {name!r}.')


# --- Fetching and caching -----------------------------------------------

def refresh_rates(base: str) -> int:
    """Pull every rate for one base currency and store it. Returns how many."""
    base = normalize(base)
    name, fetch = _provider()
    rates, rate_date = fetch(base)

    known = set(
        Currency.objects.filter(is_active=True).values_list('code', flat=True)
    )
    stored = 0
    for target, value in rates.items():
        target = normalize(target)
        # Only cache currencies the app actually offers: the provider returns
        # ~160 and storing all of them for every base is mostly noise.
        if known and target not in known:
            continue
        ExchangeRate.objects.update_or_create(
            base=base, target=target, rate_date=rate_date,
            defaults={'rate': Decimal(str(value)), 'provider': name},
        )
        stored += 1
    return stored


def get_rate(base: str, target: str) -> Decimal:
    """The rate to multiply a `base` amount by to express it in `target`.

    Serves the cache first, refreshes when it is older than a day, and falls
    back to the last known rate when the provider is unreachable.
    """
    base, target = normalize(base), normalize(target)
    if base == target:
        return Decimal('1')

    fresh_after = timezone.now().date() - RATE_TTL
    cached = _latest_rate(base, target)
    if cached is not None and cached.rate_date >= fresh_after:
        return cached.rate

    try:
        refresh_rates(base)
    except (ExchangeRateUnavailable, requests.RequestException) as exc:
        logger.warning('Exchange rate refresh failed for base=%s: %s', base, exc)
    else:
        refreshed = _latest_rate(base, target)
        if refreshed is not None:
            return refreshed.rate

    # Provider down: an old rate still beats no dashboard at all.
    if cached is not None and cached.rate_date >= (timezone.now().date() - STALE_RATE_LIMIT):
        logger.warning(
            'Serving stale rate %s->%s from %s', base, target, cached.rate_date
        )
        return cached.rate

    # Last resort: derive it from the inverse pair if we happen to hold it.
    inverse = _latest_rate(target, base)
    if inverse is not None and inverse.rate:
        return Decimal('1') / inverse.rate

    raise ExchangeRateUnavailable(
        f'No exchange rate available for {base} -> {target}.'
    )


def _latest_rate(base: str, target: str):
    return (
        ExchangeRate.objects
        .filter(base=base, target=target)
        .order_by('-rate_date')
        .first()
    )


# --- Conversion ---------------------------------------------------------

def normalize(code: str) -> str:
    return (code or '').strip().upper()[:3]


def decimals_for(code: str) -> int:
    """How many decimal places this currency is written with."""
    currency = Currency.objects.filter(code=normalize(code)).only('decimals').first()
    return currency.decimals if currency else 2


def quantize(amount: Decimal, code: str) -> Decimal:
    """Round to the currency's own precision, half-even."""
    places = decimals_for(code)
    exponent = Decimal(1).scaleb(-places)  # 2 -> 0.01, 0 -> 1
    return Decimal(amount).quantize(exponent, rounding=ROUND_HALF_EVEN)


def convert(amount, source: str, target: str) -> Decimal:
    """Express `amount` (in `source`) as `target`, rounded for `target`."""
    source, target = normalize(source), normalize(target)
    amount = Decimal(str(amount))
    if source == target:
        return quantize(amount, target)
    return quantize(amount * get_rate(source, target), target)


def convert_safe(amount, source: str, target: str) -> Decimal:
    """convert(), but returns the untouched amount if no rate can be found.

    Aggregations use this so one missing rate degrades a single row instead of
    failing the whole dashboard.
    """
    try:
        return convert(amount, source, target)
    except ExchangeRateUnavailable:
        logger.warning('No rate for %s->%s; leaving amount unconverted', source, target)
        return Decimal(str(amount))


def sum_in(queryset, target: str, field: str = 'amount') -> Decimal:
    """Total a queryset in one currency, honouring each row's own currency.

    Summing mixed currencies in SQL would add pesos to dollars. Grouping by
    currency first keeps the database doing the heavy lifting and leaves only
    one conversion per currency to Python.
    """
    target = normalize(target)
    total = Decimal('0')
    grouped = queryset.values('currency').annotate(total=Sum(field))
    for row in grouped:
        subtotal = row['total'] or Decimal('0')
        total += convert_safe(subtotal, row['currency'] or target, target)
    return quantize(total, target)
