"""Serializers for financial records (incomes & expenses)."""
from rest_framework import serializers

from ..models.records import FinancialRecord


class FinancialRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for FinancialRecord model instances.
    Handles data serialization/deserialization and entry validation.
    """
    class Meta:
        model = FinancialRecord
        fields = [
            'id',
            'type',
            'category',
            'amount',
            'date',
            'description',
            'account_bank',
            'account_bank_other',
            'created_at'
        ]