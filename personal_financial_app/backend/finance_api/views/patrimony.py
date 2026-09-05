"""API views for the asset registry and the net-worth summary."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes

from ..models import Asset
from ..serializers import AssetSerializer
from ..services import patrimony_service
from ..services.snapshot_service import base_currency_for
from .mixins import OwnerScopedMixin


class AssetViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    """
    CRUD for the things a user owns: cash, investments, property, vehicles.
    Debts are the other side of the ledger and live at /api/debts/.
    """
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    currency_field = 'currency'

    def get_queryset(self):
        queryset = super().get_queryset()

        asset_type = self.request.query_params.get('asset_type')
        if asset_type:
            queryset = queryset.filter(asset_type=asset_type)

        liquid = self.request.query_params.get('is_liquid')
        if liquid is not None:
            queryset = queryset.filter(is_liquid=liquid.lower() == 'true')

        return queryset


@extend_schema_view(
    get=extend_schema(
        responses={200: OpenApiTypes.OBJECT},
        description=(
            'Net worth and its parts: assets (split liquid vs illiquid), '
            'liabilities, and both broken down by type. Every figure is in the '
            "caller's base currency."
        ),
    ),
)
class PatrimonyView(APIView):
    """GET /api/patrimony/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base = base_currency_for(request.user)
        return Response(patrimony_service.summary_for(request.user, base))
