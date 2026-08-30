"""API views for currency exchange rates."""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import CurrencyRate
from ..serializers import CurrencyRateSerializer
from ..services.currency import get_rate_map


class CurrencyRateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing currency exchange rates (foreign → COP).
    """
    queryset = CurrencyRate.objects.all()
    serializer_class = CurrencyRateSerializer

    @action(detail=False, methods=['get'])
    def rates(self, request):
        """Return a flat {currency_code: rate_to_cop} dict including COP: 1.0."""
        return Response(get_rate_map())
