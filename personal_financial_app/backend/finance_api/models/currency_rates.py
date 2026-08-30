"""Currency exchange rate model: COP-based rates for multi-currency support."""
from django.core.validators import MinValueValidator
from django.db import models


class CurrencyRate(models.Model):
    """
    Exchange rate from a foreign currency to COP (Colombian Pesos).

    rate_to_cop stores how many COP one unit of `currency_code` is worth.
    COP is the implicit base currency (rate = 1.0), so no row is created for COP.
    """
    currency_code = models.CharField(
        max_length=3,
        unique=True,
        help_text="ISO 4217 currency code (e.g. USD, EUR). COP is the base currency and is not stored.",
    )
    rate_to_cop = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(0.0001)],
        help_text="Exchange rate: how many COP one unit of this currency is worth. E.g. 4000.0000 means 1 USD = 4,000 COP.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['currency_code']
        verbose_name = 'Currency Rate'
        verbose_name_plural = 'Currency Rates'

    def __str__(self):
        return f"{self.currency_code} → COP × {self.rate_to_cop}"
