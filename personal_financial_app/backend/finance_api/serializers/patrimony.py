"""Serializers for the asset registry."""
from rest_framework import serializers

from ..models.patrimony import Asset


class AssetSerializer(serializers.ModelSerializer):
    """
    Serializer for owned assets.
    """
    asset_type_display = serializers.CharField(source='get_asset_type_display', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'name', 'asset_type', 'asset_type_display', 'current_value',
            'currency', 'is_liquid', 'valued_at', 'acquired_date', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_current_value(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'An asset cannot be worth less than zero. Record what you owe as a debt instead.'
            )
        return value

    def create(self, validated_data):
        # Liquidity defaults from the type, but only when the client did not
        # say — marking a savings account illiquid on purpose must stick.
        if 'is_liquid' not in self.initial_data:
            validated_data['is_liquid'] = (
                validated_data.get('asset_type') in Asset.LIQUID_TYPES
            )
        return super().create(validated_data)
