"""API views for financial records (incomes & expenses)."""
from django.db import models
from rest_framework import viewsets

from ..models import FinancialRecord
from ..serializers import FinancialRecordSerializer
from .mixins import OwnerScopedMixin


class FinancialRecordViewSet(OwnerScopedMixin, viewsets.ModelViewSet):
    """
    ViewSet for FinancialRecord model (Incomes & Expenses).
    Provides CRUD functionality with support for multiple filters
    (category, bank account, dates, types, etc.)
    """
    queryset = FinancialRecord.objects.all()
    serializer_class = FinancialRecordSerializer
    currency_field = 'currency'

    def get_queryset(self):
        """
        Applies filter logic dynamically based on HTTP request query parameters.
        This enables exact client-side syncing for dashboard graphics and custom filtering.
        """
        queryset = super().get_queryset()

        # 1. Filter by transaction type (income / expense)
        record_type = self.request.query_params.get('type')
        if record_type:
            queryset = queryset.filter(type=record_type)

        # 2. Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # 3. Filter by bank account or payment method
        account_bank = self.request.query_params.get('account_bank')
        if account_bank:
            queryset = queryset.filter(account_bank=account_bank)

        # 4. Filter by date ranges (start_date / end_date)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        # 5. Filter by amount ranges (min_amount / max_amount)
        min_amount = self.request.query_params.get('min_amount')
        max_amount = self.request.query_params.get('max_amount')
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)

        # 6. Text search filter
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(description__icontains=search) |
                models.Q(category__icontains=search) |
                models.Q(account_bank__icontains=search)
            )

        return queryset