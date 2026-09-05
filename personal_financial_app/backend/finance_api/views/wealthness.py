"""API view for the Wealthness dashboard: financial health at a glance."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes

from ..services import wealthness_service
from ..services.snapshot_service import base_currency_for

MAX_MONTHS = 60


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                'months', OpenApiTypes.INT,
                description=f'Length of the window, 2 to {MAX_MONTHS} months (default 12).',
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
        description=(
            'Financial health: monthly net flow, the direction net worth is '
            'moving, savings rate, emergency-fund cover and debt load. Each '
            'metric carries a status from documented rules of thumb, not a '
            'single opaque score.'
        ),
    ),
)
class WealthnessView(APIView):
    """GET /api/wealthness/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            months = int(request.query_params.get('months', 12))
        except (TypeError, ValueError):
            months = 12
        # Clamp rather than reject: a nonsense window should still render a
        # dashboard, just over a sane range.
        months = max(2, min(months, MAX_MONTHS))

        base = base_currency_for(request.user)
        return Response(wealthness_service.overview(request.user, base, months=months))
