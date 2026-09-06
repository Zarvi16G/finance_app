"""Currency catalog and cached exchange rates.

Two rules shape this module:

1. Money is never stored converted. Every amount keeps the currency it was
   actually spent or earned in; the value in the user's base currency is
   derived when it is read. Overwriting the original would rewrite the past
   every time a rate moves.
2. Rates are cached per day, not fetched per request. The provider's free tier
   is metered, rates only move once a day, and a dashboard would otherwise
   fire dozens of identical calls.
"""
from django.db import models


class Currency(models.Model):
    """An ISO 4217 currency the app can hold amounts in."""

    code = models.CharField(
        max_length=3, primary_key=True,
        help_text="ISO 4217 code, e.g. COP, USD, EUR",
    )
    name = models.CharField(max_length=60)
    symbol = models.CharField(max_length=8, blank=True, default='')
    # ISO 4217 also fixes how many decimals a currency uses: COP and JPY are
    # normally shown with none, USD and EUR with two.
    decimals = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive currencies stay readable but are not offered in pickers",
    )

    class Meta:
        verbose_name_plural = 'Currencies'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} ({self.name})'


class ExchangeRate(models.Model):
    """One base -> target rate for one day, as published by the provider.

    Keyed by date rather than overwritten in place, so a later phase can price
    a three-month-old transaction with the rate that actually applied then.
    """

    base = models.CharField(max_length=3, db_index=True)
    target = models.CharField(max_length=3, db_index=True)
    # Rates span a wide range: 1 USD is ~4000 COP, and the inverse is
    # ~0.00025 — hence the generous precision.
    rate = models.DecimalField(max_digits=24, decimal_places=12)
    rate_date = models.DateField(
        help_text="The day this rate is published for (provider's own date)",
    )
    fetched_at = models.DateTimeField(auto_now=True)
    provider = models.CharField(max_length=40, blank=True, default='')

    class Meta:
        ordering = ['-rate_date', 'base', 'target']
        constraints = [
            models.UniqueConstraint(
                fields=['base', 'target', 'rate_date'],
                name='uniq_rate_base_target_date',
            ),
        ]
        indexes = [
            models.Index(fields=['base', 'target', '-rate_date']),
        ]

    def __str__(self):
        return f'{self.base}->{self.target} {self.rate} ({self.rate_date})'
