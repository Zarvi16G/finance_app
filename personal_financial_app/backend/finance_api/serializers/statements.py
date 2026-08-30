"""Serializers for bank statements and their extracted transactions."""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from ..models.statements import BankStatement, ExtractedTransaction


class BankStatementSerializer(serializers.ModelSerializer):
    """
    Serializer for uploaded bank statements.
    """
    file_size_mb = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    statement_type_display = serializers.CharField(source='get_statement_type_display', read_only=True)
    total_income_usd = serializers.SerializerMethodField()
    total_expense_usd = serializers.SerializerMethodField()
    net_usd = serializers.SerializerMethodField()
    totals_stale = serializers.SerializerMethodField()

    class Meta:
        model = BankStatement
        fields = [
            'id', 'file', 'original_filename', 'file_size_mb',
            'content_hash', 'statement_type', 'statement_type_display',
            'bank_name', 'password', 'account_number', 'currency',
            'statement_period_start', 'statement_period_end',
            'uploaded_at', 'processed_at', 'status', 'status_display',
            'total_transactions_extracted', 'total_transactions_imported', 'error_message',
            'total_income_usd', 'total_expense_usd', 'net_usd', 'totals_stale',
            'totals_updated_at',
        ]
        read_only_fields = ['uploaded_at', 'processed_at', 'status', 'total_transactions_extracted', 'total_transactions_imported', 'error_message', 'content_hash', 'totals_updated_at']
        extra_kwargs = {'password': {'write_only': True, 'style': {'input_type': 'password'}}}

    @extend_schema_field(serializers.FloatField)
    def get_file_size_mb(self, obj):
        if obj.file:
            return round(obj.file.size / (1024 * 1024), 2)
        return 0

    def get_total_income_usd(self, obj):
        return self._get_totals(obj).get('total_income_usd', 0)

    def get_total_expense_usd(self, obj):
        return self._get_totals(obj).get('total_expense_usd', 0)

    def get_net_usd(self, obj):
        return self._get_totals(obj).get('net_usd', 0)

    def get_totals_stale(self, obj):
        return self._get_totals(obj).get('totals_stale', True)

    def _get_totals(self, obj):
        if not hasattr(self, '_totals_cache'):
            self._totals_cache = {}
        key = str(obj.id)
        if key not in self._totals_cache:
            from ..services.statement_totals import get_statement_totals
            self._totals_cache[key] = get_statement_totals(obj)
        return self._totals_cache[key]


class ExtractedTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for extracted transactions from bank statements.
    """
    suggested_category_display = serializers.CharField(source='get_suggested_category_display', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    usd_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ExtractedTransaction
        fields = [
            'id', 'statement', 'date', 'raw_description', 'cleaned_description', 'amount',
            'currency', 'transaction_type',
            'transaction_type_display', 'suggested_category', 'suggested_category_display',
            'confidence_score', 'needs_review', 'is_reviewed', 'user_confirmed_category',
            'user_confirmed_type', 'created_at', 'reviewed_at', 'usd_amount'
        ]
        read_only_fields = ['statement', 'suggested_category', 'confidence_score', 'created_at', 'raw_description', 'cleaned_description', 'currency', 'usd_amount']


class CategorizationReviewSerializer(serializers.Serializer):
    """
    Serializer for batch categorization review.
    """
    transactions = ExtractedTransactionSerializer(many=True)
    categories = serializers.ListField(child=serializers.CharField())