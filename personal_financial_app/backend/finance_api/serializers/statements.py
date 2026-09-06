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

    class Meta:
        model = BankStatement
        fields = [
            'id', 'file', 'original_filename', 'file_size_mb',
            'content_hash', 'statement_type', 'statement_type_display',
            'bank_name', 'password', 'account_number', 'statement_period_start', 'statement_period_end',
            'uploaded_at', 'processed_at', 'status', 'status_display',
            'total_transactions_extracted', 'total_transactions_imported', 'error_message'
        ]
        read_only_fields = ['uploaded_at', 'processed_at', 'status', 'total_transactions_extracted', 'total_transactions_imported', 'error_message', 'content_hash']
        extra_kwargs = {'password': {'write_only': True, 'style': {'input_type': 'password'}}}

    @extend_schema_field(serializers.FloatField)
    def get_file_size_mb(self, obj):
        if obj.file:
            return round(obj.file.size / (1024 * 1024), 2)
        return 0


class ExtractedTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for extracted transactions from bank statements.
    """
    suggested_category_display = serializers.CharField(source='get_suggested_category_display', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = ExtractedTransaction
        fields = [
            'id', 'statement', 'date', 'raw_description', 'cleaned_description', 'amount', 'transaction_type',
            'transaction_type_display', 'suggested_category', 'suggested_category_display',
            'confidence_score', 'needs_review', 'is_reviewed', 'user_confirmed_category',
            'user_confirmed_type', 'created_at', 'reviewed_at'
        ]
        read_only_fields = ['statement', 'suggested_category', 'confidence_score', 'created_at', 'raw_description', 'cleaned_description']


class CategorizationReviewSerializer(serializers.Serializer):
    """
    Serializer for batch categorization review.
    """
    transactions = ExtractedTransactionSerializer(many=True)
    categories = serializers.ListField(child=serializers.CharField())