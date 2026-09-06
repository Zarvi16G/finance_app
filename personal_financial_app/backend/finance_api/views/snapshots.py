"""API views for financial snapshots."""
from datetime import datetime

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import FinancialSnapshot
from ..serializers import FinancialSnapshotSerializer
from ..services.snapshot_service import compute_monthly_snapshot
from .mixins import OwnerScopedMixin


class FinancialSnapshotViewSet(OwnerScopedMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for historical financial snapshots.
    """
    queryset = FinancialSnapshot.objects.all()
    serializer_class = FinancialSnapshotSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new financial snapshot for a given month with all ratios."""
        date_str = request.data.get('date')
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date().replace(day=1)

        snapshot = compute_monthly_snapshot(date, request.user)
        return Response(FinancialSnapshotSerializer(snapshot).data)