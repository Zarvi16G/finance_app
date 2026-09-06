"""API views for the financial analytics dashboard."""
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiTypes

from ..models import Debt
from ..services.analytics_service import (
    build_dashboard_data,
    build_dashboard_from_snapshots,
    get_debt_summary,
)


@extend_schema(
    responses={200: OpenApiTypes.OBJECT},
    description=(
        'Comprehensive dashboard data (stat tiles, charts, health ratios, debt summary) '
        'for the date range given by start_date / end_date (YYYY-MM-DD). Serves from '
        'pre-computed FinancialSnapshot when available, otherwise computes live.'
    ),
)
class FinancialAnalyticsView(APIView):
    """
    Comprehensive financial analytics dashboard data.
    Serves from pre-computed FinancialSnapshot when available,
    falls back to live computation for current/incomplete months.
    """
    def get(self, request):
        # Get date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date:
            start_date = (timezone.now() - timedelta(days=365)).date()
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        if not end_date:
            end_date = timezone.now().date()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Try to serve from pre-computed snapshots
        snapshot_data = build_dashboard_from_snapshots(start_date, end_date, request.user)
        if snapshot_data is not None:
            debts = Debt.objects.filter(owner=request.user, status='active')
            snapshot_data['debt_summary'] = get_debt_summary(
                debts, snapshot_data['base_currency']
            )
            return Response(snapshot_data)

        # Fall back to live computation
        return Response(build_dashboard_data(start_date, end_date, request.user))