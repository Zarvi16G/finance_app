"""Daily user snapshot model: daily USD exchange rates for currency conversion."""
from django.conf import settings
from django.db import models


class DailyUserSnapshot(models.Model):
    """
    Daily snapshot of USD exchange rates for a specific user.
    Stores a JSON map of currency codes to rates relative to USD.
    e.g. {"EUR": 0.91, "COP": 4100.0} means 1 USD = 0.91 EUR = 4100.0 COP
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_snapshots',
    )
    snapshot_date = models.DateField(unique=True)
    rates = models.JSONField(
        help_text="JSON map of currency codes to rates relative to USD. "
        "E.g. {\"EUR\": 0.91, \"COP\": 4100.0}"
    )

    class Meta:
        ordering = ['-snapshot_date']

    def __str__(self):
        return f"Daily Snapshot {self.snapshot_date}: {self.rates}"


"""FinancialSnapshot model: monthly financial health snapshots for trend analysis."""
from django.db import models


class FinancialSnapshot(models.Model):
    """
    Monthly financial health snapshot for trend analysis.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='financial_snapshots',
        help_text="The user this monthly snapshot belongs to",
    )
    date = models.DateField()  # First day of month; unique per owner (see Meta)
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_savings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    savings_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Liquidity ratios
    current_ratio = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    quick_ratio = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    cash_ratio = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Profitability ratios
    net_profit_margin = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    expense_ratio = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Solvency ratios
    debt_to_income = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    debt_to_asset = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Growth metrics
    income_growth_yoy = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    expense_growth_yoy = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    net_worth_growth = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Operational efficiency
    expenses_per_category = models.JSONField(default=dict, blank=True)

    # Assets and liabilities
    total_liabilities = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_assets = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    net_worth = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['owner', 'date']

    def __str__(self):
        return f"Snapshot {self.date.strftime('%Y-%m')}: Income {self.total_income}, Expenses {self.total_expenses}"