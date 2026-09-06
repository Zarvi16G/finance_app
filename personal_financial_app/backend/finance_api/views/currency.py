"""API views for the currency catalog and conversion."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes

from ..models import Currency
from ..services import currency_service
from ..services.snapshot_service import base_currency_for


@extend_schema_view(
    get=extend_schema(
        responses={200: OpenApiTypes.OBJECT},
        description='Lists the currencies the app can hold amounts in, plus the caller\'s base currency.',
    ),
)
class CurrencyListView(APIView):
    """GET /api/currencies/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        currencies = Currency.objects.filter(is_active=True)
        return Response({
            'base_currency': base_currency_for(request.user),
            'currencies': [
                {
                    'code': c.code,
                    'name': c.name,
                    'symbol': c.symbol,
                    'decimals': c.decimals,
                }
                for c in currencies
            ],
        })


@extend_schema_view(
    post=extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT},
        description=(
            'Converts {amount, from, to}. `to` defaults to the caller\'s base '
            'currency. Rates come from the daily cache, not a live call.'
        ),
    ),
)
class CurrencyConvertView(APIView):
    """POST /api/currencies/convert/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount')
        source = request.data.get('from')
        target = request.data.get('to') or base_currency_for(request.user)

        if amount is None or not source:
            return Response(
                {'error': 'amount and from are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            converted = currency_service.convert(amount, source, target)
            rate = currency_service.get_rate(source, target)
        except (TypeError, ValueError, ArithmeticError):
            return Response(
                {'error': 'amount must be a number.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except currency_service.ExchangeRateUnavailable as exc:
            return Response(
                {'error': str(exc), 'error_code': 'rate_unavailable'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            'amount': str(amount),
            'from': currency_service.normalize(source),
            'to': currency_service.normalize(target),
            'rate': str(rate),
            'converted': str(converted),
        })
