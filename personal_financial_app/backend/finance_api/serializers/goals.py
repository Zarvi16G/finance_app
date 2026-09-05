"""Serializers for financial goals."""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from ..models.goals import ExpectedGoal


class ExpectedGoalSerializer(serializers.ModelSerializer):
    """
    Serializer for ExpectedGoal model instances.
    Includes a calculated progress percentage property to render status bars on the frontend.
    """
    progress_percentage = serializers.SerializerMethodField(
        help_text="The completion progress represented as a percentage (0 - 100)"
    )

    class Meta:
        model = ExpectedGoal
        fields = [
            'id',
            'title',
            'goal_type',
            'experience_date',
            'location',
            'target_amount',
            'current_amount',
            'currency',
            'start_date',
            'end_date',
            'category',
            'status',
            'description',
            'progress_percentage',
            'created_at'
        ]

    @extend_schema_field(serializers.FloatField)
    def get_progress_percentage(self, obj):
        """
        Calculates and bounds the current savings progress percentage.
        """
        if not obj.target_amount or obj.target_amount <= 0:
            return 0.0
        percentage = float(obj.current_amount) / float(obj.target_amount) * 100.0
        return round(min(percentage, 100.0), 2)