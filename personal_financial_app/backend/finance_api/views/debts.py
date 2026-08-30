"""API views for debt management."""
from decimal import Decimal

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Debt, FinancialRecord
from ..permissions import IsOwner
from ..serializers import DebtSerializer


class DebtViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user debts.
    """
    queryset = Debt.objects.all()
    serializer_class = DebtSerializer
    permission_classes = [IsOwner]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset().filter(owner=self.request.user)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    @action(detail=True, methods=['post'])
    def make_payment(self, request, pk=None):
        """Record a payment on a debt."""
        debt = self.get_object()
        amount = Decimal(str(request.data.get('amount', 0)))
        payment_date = request.data.get('date', timezone.now().date())

        if amount <= 0:
            return Response({'error': 'Payment amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)

        # Apply payment
        interest = debt.monthly_interest
        principal = amount - interest

        if principal > 0:
            debt.current_balance = max(Decimal('0'), debt.current_balance - Decimal(str(principal)))

        if debt.current_balance == 0:
            debt.status = 'paid_off'
            debt.end_date = payment_date

        debt.save()

        # Create expense record for interest
        if interest > 0:
            FinancialRecord.objects.create(
                owner=request.user,
                type='expense',
                category='Other',
                amount=Decimal(str(interest)),
                currency=debt.currency,
                date=payment_date,
                description=f'Interest payment on {debt.name}',
                account_bank=debt.creditor
            )

        return Response(DebtSerializer(debt).data)

    @action(detail=False, methods=['get'])
    def payoff_strategy(self, request):
        """Get recommended payoff strategy (avalanche vs snowball)."""
        debts = self.get_queryset().filter(status='active')

        if not debts:
            return Response({'message': 'No active debts'})

        # Avalanche (highest interest first)
        avalanche = sorted(debts, key=lambda d: float(d.interest_rate), reverse=True)
        # Snowball (smallest balance first)
        snowball = sorted(debts, key=lambda d: float(d.current_balance))

        return Response({
            'avalanche': DebtSerializer(avalanche, many=True).data,
            'snowball': DebtSerializer(snowball, many=True).data,
            'recommendation': 'avalanche' if len(debts) > 1 else 'single',
        })