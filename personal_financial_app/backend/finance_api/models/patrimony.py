"""Asset registry — the other half of net worth.

Debts already covered what the user owes. This covers what they own, so net
worth stops being a placeholder: net worth = assets - liabilities, both
converted to the owner's base currency at read time.
"""
from django.conf import settings
from django.db import models


class Asset(models.Model):
    """Something the user owns and can put a value on."""

    ASSET_TYPES = [
        ('cash', 'Cash'),
        ('savings', 'Savings Account'),
        ('investment', 'Investment'),
        ('retirement', 'Retirement Fund'),
        ('property', 'Property'),
        ('vehicle', 'Vehicle'),
        ('business', 'Business Stake'),
        ('receivable', 'Money Owed to Me'),
        ('other', 'Other'),
    ]

    # Assets you could turn into cash within days. This is what separates an
    # emergency fund from a house, and it is what the Wealthness metrics will
    # measure against monthly expenses.
    LIQUID_TYPES = {'cash', 'savings', 'investment', 'receivable'}

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assets',
        help_text="The user this asset belongs to",
    )
    name = models.CharField(max_length=120)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES, default='other')
    # Wider than the transaction models on purpose: a property priced in COP
    # runs to hundreds of millions.
    current_value = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(
        max_length=3, default='COP',
        help_text="ISO 4217 code the value above is expressed in",
    )
    is_liquid = models.BooleanField(
        default=False,
        help_text="Convertible to cash within days; drives the emergency-fund metrics",
    )
    valued_at = models.DateField(
        null=True, blank=True,
        help_text="When this valuation was taken — a stale one quietly distorts net worth",
    )
    acquired_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-current_value', 'name']

    def __str__(self):
        return f'{self.name} ({self.asset_type}): {self.current_value} {self.currency}'
