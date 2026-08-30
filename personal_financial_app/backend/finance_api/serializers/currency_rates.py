"""Serializers for currency exchange rates."""
from rest_framework import serializers

from ..models import CurrencyRate


class CurrencyRateSerializer(serializers.ModelSerializer):
    """
    Serializer for CurrencyRate model instances.
    """
    class Meta:
        model = CurrencyRate
        fields = ['id', 'currency_code', 'rate_to_cop', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
