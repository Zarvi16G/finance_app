"""Serializers for experience budget lines."""
from rest_framework import serializers

from ..models import ExpectedGoal
from ..models.experiences import ExperienceBudgetItem


class ExperienceBudgetItemSerializer(serializers.ModelSerializer):
    """
    A single budget line.

    `goal` is the security-sensitive field here: it is what ties the line to
    an owner. Its queryset is narrowed to the requesting user's own goals, so
    a crafted payload cannot attach a line to somebody else's trip — DRF
    answers 400 "object does not exist" for any other id, exactly as it does
    for one that never existed.
    """
    goal = serializers.PrimaryKeyRelatedField(queryset=ExpectedGoal.objects.none())
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    variance = serializers.SerializerMethodField()

    class Meta:
        model = ExperienceBudgetItem
        fields = [
            'id', 'goal', 'label', 'category', 'category_display',
            'estimated_amount', 'actual_amount', 'variance', 'currency',
            'is_booked', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated:
            self.fields['goal'].queryset = ExpectedGoal.objects.filter(owner=request.user)

    def get_variance(self, obj):
        """Actual minus estimated, once the money is spent.

        Positive means it cost more than planned.
        """
        if obj.actual_amount is None:
            return None
        return float(obj.actual_amount - obj.estimated_amount)

    def validate_estimated_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('A budget line cannot be negative.')
        return value
