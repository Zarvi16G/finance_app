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

Totals
------
Aggregates are `Total` objects, not bare Decimals, and `Total` refuses to add
itself to a Total in another currency. That is the whole point: adding pesos
to dollars is not an operation, it is a bug, and the type makes it
unwriteable rather than merely discouraged. Anything that could not be
converted is carried along in `unconverted` and is *excluded* from the
figure, so a total is either right or visibly incomplete — never quietly
wrong.
"""
import logging
from dataclasses import dataclass, field as dataclass_field
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


def try_convert(amount, source: str, target: str) -> Decimal | None:
    """convert(), or None when no rate exists.

    None is the honest answer to "how much is this in pesos?" when nobody
    knows. Callers must decide what to do with it; what they must not do is
    substitute the unconverted number, which is how a dollar figure ends up
    added to a column of pesos.
    """
    try:
        return convert(amount, source, target)
    except ExchangeRateUnavailable:
        logger.warning('No rate for %s->%s; amount excluded from totals', source, target)
        return None


# --- Totals -------------------------------------------------------------

@dataclass(frozen=True)
class Unconverted:
    """An amount left out of a total because no rate was available."""
    currency: str
    amount: Decimal

    def as_dict(self) -> dict:
        return {'currency': self.currency, 'amount': float(self.amount)}


@dataclass(frozen=True)
class Total:
    """A sum of money in one stated currency.

    Arithmetic is only defined between Totals of the same currency, and with
    plain scalars (which carry no currency of their own). Everything else
    raises: there is no sensible answer to "pesos plus dollars", so the type
    declines to invent one.

    `unconverted` lists what had to be left out, and it survives arithmetic —
    a figure derived from an incomplete total is itself incomplete, and the
    API says so rather than letting the caller assume otherwise.
    """
    amount: Decimal
    currency: str
    unconverted: tuple[Unconverted, ...] = dataclass_field(default=())

    # -- construction

    @classmethod
    def zero(cls, currency: str) -> 'Total':
        return cls(Decimal('0'), normalize(currency))

    @classmethod
    def of(cls, amount, currency: str) -> 'Total':
        """A Total that is already expressed in `currency` — no conversion."""
        currency = normalize(currency)
        return cls(quantize(Decimal(str(amount)), currency), currency)

    @classmethod
    def converted(cls, amount, source: str, target: str) -> 'Total':
        """`amount` expressed in `target`, or zero plus a record of the miss.

        Zero rather than the raw number, because the raw number is in the
        wrong currency and would corrupt anything it touches.
        """
        source, target = normalize(source), normalize(target)
        value = try_convert(amount, source, target)
        if value is None:
            return cls(
                Decimal('0'), target,
                (Unconverted(source, Decimal(str(amount))),),
            )
        return cls(value, target)

    # -- reading

    @property
    def complete(self) -> bool:
        """False when something had to be left out of this figure."""
        return not self.unconverted

    def __float__(self) -> float:
        return float(self.amount)

    def __str__(self) -> str:
        return f'{self.amount} {self.currency}'

    def __bool__(self) -> bool:
        return bool(self.amount)

    # -- arithmetic

    def _same(self, other: 'Total') -> None:
        if self.currency != other.currency:
            raise ValueError(
                f'Refusing to combine {self.currency} with {other.currency}: '
                'convert one of them first.'
            )

    def __add__(self, other):
        if not isinstance(other, Total):
            return NotImplemented
        self._same(other)
        return Total(
            self.amount + other.amount, self.currency,
            self.unconverted + other.unconverted,
        )

    def __sub__(self, other):
        if not isinstance(other, Total):
            return NotImplemented
        self._same(other)
        return Total(
            self.amount - other.amount, self.currency,
            self.unconverted + other.unconverted,
        )

    def __neg__(self) -> 'Total':
        return Total(-self.amount, self.currency, self.unconverted)

    def __mul__(self, factor):
        """Scaling by a plain number keeps the currency; by a Total does not."""
        if isinstance(factor, Total):
            raise ValueError('Multiplying two amounts of money is not a money amount.')
        return Total(
            quantize(self.amount * Decimal(str(factor)), self.currency),
            self.currency, self.unconverted,
        )

    __rmul__ = __mul__

    def __truediv__(self, divisor):
        """Total / Total is a ratio (no currency); Total / number is a Total."""
        if isinstance(divisor, Total):
            self._same(divisor)
            if not divisor.amount:
                raise ZeroDivisionError('Cannot take a ratio against a zero total.')
            return self.amount / divisor.amount
        divisor = Decimal(str(divisor))
        if not divisor:
            raise ZeroDivisionError
        return Total(
            quantize(self.amount / divisor, self.currency),
            self.currency, self.unconverted,
        )

    # -- comparison

    def _comparable(self, other):
        """Totals compare with same-currency Totals, and with zero.

        Zero is the one number with no currency of its own, and `if total > 0`
        is the check every caller actually wants to write.
        """
        if isinstance(other, Total):
            self._same(other)
            return other.amount
        if isinstance(other, (int, float, Decimal)) and Decimal(str(other)) == 0:
            return Decimal('0')
        raise ValueError(
            f'Cannot compare a {self.currency} amount with {other!r}: '
            'only zero and other amounts in the same currency.'
        )

    def __lt__(self, other):
        return self.amount < self._comparable(other)

    def __le__(self, other):
        return self.amount <= self._comparable(other)

    def __gt__(self, other):
        return self.amount > self._comparable(other)

    def __ge__(self, other):
        return self.amount >= self._comparable(other)


def merge_unconverted(*totals) -> list[str]:
    """The currencies left out across several totals.

    Currencies, not amounts. One response holds overlapping aggregations —
    total assets, liquid assets, and assets by type all cover the same rows —
    so adding up what each of them excluded would count the same money
    several times. Rather than publish a figure that cannot be defended,
    this reports which currencies are unreachable, which is the part that is
    both true and actionable: the fix is to get a rate for them.
    """
    codes: set[str] = set()
    for total in totals:
        if not isinstance(total, Total):
            continue
        codes.update(miss.currency for miss in total.unconverted)
    return sorted(codes)


def conversion_report(*totals) -> dict:
    """The block every aggregate endpoint attaches so a client can tell a
    complete total from a partial one."""
    missing = merge_unconverted(*totals)
    return {
        'complete': not missing,
        'unconvertible_currencies': missing,
    }


def unconvertible_currencies(querysets, target: str) -> list[str]:
    """Which currencies present in these querysets have no rate to `target`.

    A shortcut for endpoints that build their totals through many small
    helpers: rather than threading a Total through every one of them, ask
    once which currencies are unreachable. The answer is the same, because a
    currency either converts or it does not.
    """
    target = normalize(target)
    codes: set[str] = set()
    for queryset in querysets:
        codes.update(
            normalize(code or target)
            for code in queryset.values_list('currency', flat=True).distinct()
        )
    missing = []
    for code in sorted(codes):
        if code == target:
            continue
        if try_convert(Decimal('1'), code, target) is None:
            missing.append(code)
    return missing


def sum_in(queryset, target: str, field: str = 'amount') -> Total:
    """Total a queryset in one currency, honouring each row's own currency.

    Summing mixed currencies in SQL would add pesos to dollars. Grouping by
    currency first keeps the database doing the heavy lifting and leaves only
    one conversion per currency to Python — and a group whose rate is missing
    is left out of the figure and recorded, never folded in unconverted.
    """
    target = normalize(target)
    total = Total.zero(target)
    grouped = queryset.values('currency').annotate(total=Sum(field))
    for row in grouped:
        subtotal = row['total'] or Decimal('0')
        total = total + Total.converted(subtotal, row['currency'] or target, target)
    return Total(quantize(total.amount, target), target, total.unconverted)
