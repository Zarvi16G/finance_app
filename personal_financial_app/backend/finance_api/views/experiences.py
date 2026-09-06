"""API views for life-experience goals and their budgets."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes

from ..models.experiences import ExperienceBudgetItem
from ..serializers.experiences import ExperienceBudgetItemSerializer
from ..services import experience_service
from ..services.snapshot_service import base_currency_for
from .mixins import OwnerScopedMixin


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter('goal', OpenApiTypes.INT, description='Filter to one experience goal.'),
        ],
    ),
)
class ExperienceBudgetItemViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    """
    CRUD for the lines of an experience budget.

    A line has no owner column of its own — it inherits one from the goal it
    hangs off. The serializer restricts which goals may be referenced, so a
    line can never be attached to another user's trip.
    """
    queryset = ExperienceBudgetItem.objects.all()
    serializer_class = ExperienceBudgetItemSerializer
    owner_field = None
    owner_lookup = 'goal__owner'
    currency_field = 'currency'

    def get_queryset(self):
        queryset = super().get_queryset()
        goal = self.request.query_params.get('goal')
        if goal:
            queryset = queryset.filter(goal_id=goal)
        return queryset


@extend_schema_view(
    get=extend_schema(
        responses={200: OpenApiTypes.OBJECT},
        description=(
            'Every life-experience goal with its itemised budget, category '
            'breakdown, saving progress, and how the plan compares with the '
            'target. All amounts in the caller\'s base currency.'
        ),
    ),
)
class LifeExperiencesView(APIView):
    """GET /api/life-experiences/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base = base_currency_for(request.user)
        return Response(experience_service.experiences_for(request.user, base))
