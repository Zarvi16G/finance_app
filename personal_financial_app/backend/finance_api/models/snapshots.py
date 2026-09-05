"""FinancialSnapshot model: monthly financial health snapshots for trend analysis."""
from django.conf import settings
from django.db import models


class FinancialSnapshot(models.Model):
    """
    Monthly financial health snapshot for trend analysis.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='snapshots',
        help_text="The user this snapshot summarizes",
    )
    date = models.DateField()  # First day of month
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
    total_liabilities = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_assets = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    net_worth = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # Financial health (Wealthness). Stored per month so the metrics can be
    # charted over time rather than only shown for today.
    liquid_assets = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Assets convertible to cash within days, at this month's close",
    )
    emergency_fund_months = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Months of essential spending the liquid assets would cover",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            # One snapshot per user per month: previously `date` was globally
            # unique, so a second user's month silently overwrote the first's.
            models.UniqueConstraint(
                fields=['owner', 'date'],
                name='uniq_snapshot_owner_date',
            ),
        ]

    def __str__(self):
        return f"Snapshot {self.date.strftime('%Y-%m')}: Income ${self.total_income}, Expenses ${self.total_expenses}"