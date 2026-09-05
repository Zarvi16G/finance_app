"""Serializers for financial snapshots."""
from rest_framework import serializers

from ..models.snapshots import FinancialSnapshot


class FinancialSnapshotSerializer(serializers.ModelSerializer):
    """
    Serializer for financial health snapshots.
    """
    class Meta:
        model = FinancialSnapshot
        fields = [
            'id', 'date', 'total_income', 'total_expenses', 'net_savings',
            'savings_rate', 'current_ratio', 'quick_ratio', 'cash_ratio',
            'net_profit_margin', 'expense_ratio',
            'debt_to_income', 'debt_to_asset',
            'income_growth_yoy', 'expense_growth_yoy', 'net_worth_growth',
            'expenses_per_category', 'total_liabilities', 'total_assets',
            'net_worth', 'liquid_assets', 'emergency_fund_months', 'created_at'
        ]
        read_only_fields = ['created_at']