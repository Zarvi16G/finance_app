"""API views for extracted transactions (review/confirm/import)."""
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import FinancialRecord, ExtractedTransaction
from ..serializers import FinancialRecordSerializer, ExtractedTransactionSerializer
from ..services.categorization import record_memory
from .mixins import OwnerScopedMixin


class ExtractedTransactionViewSet(
    OwnerScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for managing extracted transactions awaiting review.

    There is deliberately no create route: these rows only ever come from
    parsing a statement, so a client-created one would have no statement and
    therefore no owner. POSTing here used to raise an IntegrityError (500);
    it now answers 405.
    """
    queryset = ExtractedTransaction.objects.all()
    serializer_class = ExtractedTransactionSerializer
    # Extracted rows have no owner column of their own: they inherit it from
    # the statement they were parsed out of.
    owner_field = None
    owner_lookup = 'statement__owner'

    def get_queryset(self):
        queryset = super().get_queryset()
        statement_id = self.request.query_params.get('statement_id')
        if statement_id:
            queryset = queryset.filter(statement_id=statement_id)

        needs_review = self.request.query_params.get('needs_review')
        if needs_review is not None:
            queryset = queryset.filter(needs_review=needs_review.lower() == 'true')

        return queryset

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a transaction's categorization and create/update FinancialRecord."""
        transaction = self.get_object()
        category = request.data.get('category')
        txn_type = request.data.get('type')
        description = request.data.get('description')
        account_bank = request.data.get('account_bank', 'Imported from Statement')

        if not category or not txn_type:
            return Response({'error': 'Category and type are required'}, status=status.HTTP_400_BAD_REQUEST)

        if transaction.is_reviewed:
            record = FinancialRecord.objects.filter(
                owner=request.user,
                amount=transaction.amount,
                date=transaction.date,
                description=transaction.cleaned_description,
            ).last()
            if record:
                record.type = txn_type
                record.category = category
                record.description = description or transaction.cleaned_description
                record.save()
                created = False
            else:
                record = FinancialRecord.objects.create(
                    owner=request.user,
                    type=txn_type, category=category, amount=transaction.amount,
                    date=transaction.date, description=description or transaction.cleaned_description,
                    account_bank=account_bank
                )
                created = True
        else:
            record = FinancialRecord.objects.create(
                owner=request.user,
                type=txn_type, category=category, amount=transaction.amount,
                date=transaction.date, description=description or transaction.cleaned_description,
                account_bank=account_bank
            )
            created = True

        transaction.is_reviewed = True
        transaction.user_confirmed_category = category
        transaction.user_confirmed_type = txn_type
        transaction.reviewed_at = timezone.now()
        transaction.needs_review = False
        transaction.save()

        record_memory(transaction.cleaned_description, category, txn_type, request.user)

        statement = transaction.statement
        if created:
            statement.total_transactions_imported += 1
        if statement.total_transactions_imported >= statement.total_transactions_extracted:
            statement.status = 'completed'
        statement.save()

        # Auto-generate monthly snapshot after confirmation (via post_save signal)

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(FinancialRecordSerializer(record).data, status=status_code)

    @action(detail=False, methods=['post'])
    def bulk_confirm(self, request):
        """Bulk confirm multiple transactions (handles both create and update)."""
        transactions_data = request.data.get('transactions', [])
        processed = []

        for txn_data in transactions_data:
            txn_id = txn_data.get('id')
            category = txn_data.get('category')
            txn_type = txn_data.get('type')

            if not txn_id or not category or not txn_type:
                continue

            try:
                # Scoped lookup: ids belonging to another user simply are not
                # found, so a crafted payload cannot touch their transactions.
                transaction = self.get_queryset().get(id=txn_id)

                if transaction.is_reviewed:
                    record = FinancialRecord.objects.filter(
                        owner=request.user,
                        amount=transaction.amount,
                        date=transaction.date,
                        description=transaction.cleaned_description,
                    ).last()
                    if record:
                        record.type = txn_type
                        record.category = category
                        record.description = txn_data.get('description') or transaction.cleaned_description
                        record.save()
                    else:
                        record = FinancialRecord.objects.create(
                            owner=request.user,
                            type=txn_type, category=category, amount=transaction.amount,
                            date=transaction.date, description=txn_data.get('description') or transaction.cleaned_description,
                            account_bank=txn_data.get('account_bank', 'Imported from Statement')
                        )
                else:
                    record = FinancialRecord.objects.create(
                        owner=request.user,
                        type=txn_type, category=category, amount=transaction.amount,
                        date=transaction.date, description=txn_data.get('description') or transaction.cleaned_description,
                        account_bank=txn_data.get('account_bank', 'Imported from Statement')
                    )
                    statement = transaction.statement
                    statement.total_transactions_imported += 1
                    if statement.total_transactions_imported >= statement.total_transactions_extracted:
                        statement.status = 'completed'
                    statement.save()

                transaction.is_reviewed = True
                transaction.user_confirmed_category = category
                transaction.user_confirmed_type = txn_type
                transaction.reviewed_at = timezone.now()
                transaction.needs_review = False
                transaction.save()

                record_memory(transaction.cleaned_description, category, txn_type, request.user)

                processed.append(record)
            except ExtractedTransaction.DoesNotExist:
                continue

        # Auto-generate snapshots for all affected months (via post_save signal per record)

        return Response({
            'created': len(processed),
            'records': FinancialRecordSerializer(processed, many=True).data
        }, status=status.HTTP_200_OK)