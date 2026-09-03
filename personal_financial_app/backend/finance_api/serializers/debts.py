"""Serializers for debts."""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from ..models.debts import Debt


class DebtSerializer(serializers.ModelSerializer):
    """
    Serializer for user debts.
    """
    debt_type_display = serializers.CharField(source='get_debt_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    remaining_balance = serializers.SerializerMethodField()
    months_remaining = serializers.SerializerMethodField()
    monthly_interest = serializers.SerializerMethodField()

    class Meta:
        model = Debt
        fields = [
            'id', 'name', 'debt_type', 'debt_type_display', 'original_amount',
            'current_balance', 'currency', 'interest_rate', 'minimum_payment', 'due_date',
            'start_date', 'end_date', 'status', 'status_display', 'creditor',
            'notes', 'progress_percentage', 'remaining_balance', 'months_remaining',
            'monthly_interest', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    @extend_schema_field(serializers.FloatField)
    def get_progress_percentage(self, obj):
        if obj.original_amount and obj.original_amount > 0:
            return round(float((obj.original_amount - obj.current_balance) / obj.original_amount * 100), 2)
        return 0.0

    @extend_schema_field(serializers.FloatField)
    def get_remaining_balance(self, obj):
        return float(obj.current_balance) if obj.current_balance else 0.0

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_months_remaining(self, obj):
        if obj.current_balance and obj.minimum_payment and obj.minimum_payment > 0:
            return round(float(obj.current_balance / obj.minimum_payment), 1)
        return None

    @extend_schema_field(serializers.FloatField)
    def get_monthly_interest(self, obj):
        return round(float(obj.monthly_interest), 2)