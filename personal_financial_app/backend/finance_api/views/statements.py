"""API views for bank statement upload and processing."""
import hashlib

from django.http import FileResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from ..models import BankStatement
from ..serializers import BankStatementSerializer, ExtractedTransactionSerializer
from ..services.statement_parser import process_statement


class BankStatementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bank statement uploads and processing.
    """
    queryset = BankStatement.objects.all()
    serializer_class = BankStatementSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def create(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.lower().endswith('.pdf'):
            return Response({'error': 'Only PDF files are supported'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate content hash for duplicate detection
        file_obj.seek(0)
        content_hash = hashlib.sha256(file_obj.read()).hexdigest()
        file_obj.seek(0)

        # Check for duplicate
        existing = BankStatement.objects.filter(content_hash=content_hash).first()
        if existing:
            return Response({
                'error': 'Duplicate file detected',
                'message': 'This file has already been uploaded',
                'existing_statement': BankStatementSerializer(existing).data
            }, status=status.HTTP_409_CONFLICT)

        # Get optional password from request
        password = request.data.get('password', None) or None
        statement_type = request.data.get('statement_type', 'other')

        # Create statement record
        statement = BankStatement.objects.create(
            file=file_obj,
            original_filename=file_obj.name,
            content_hash=content_hash,
            statement_type=statement_type,
            password=password,
            status='processing'
        )

        # Process synchronously with optional password
        process_statement(statement, password)

        # Refresh to get updated status
        statement.refresh_from_db()
        serializer = self.get_serializer(statement)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def extracted_transactions(self, request, *args, **kwargs):
        """Get all extracted transactions for a statement."""
        statement_id = request.query_params.get('statement_id')
        if not statement_id:
            return Response({'error': 'statement_id query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            statement = BankStatement.objects.get(id=statement_id)
        except (BankStatement.DoesNotExist, ValueError):
            return Response({'error': 'Statement not found'}, status=status.HTTP_404_NOT_FOUND)

        transactions = statement.extracted_transactions.all()
        serializer = ExtractedTransactionSerializer(transactions, many=True)

        if serializer.data:
            return Response(serializer.data)
        return Response({'message': 'There is no info extracted'})

    @action(detail=True, methods=['get'])
    def file(self, request, pk=None):
        """Download the original statement PDF (only for authenticated users)."""
        statement = self.get_object()
        if not statement.file or not statement.file.storage.exists(statement.file.name):
            return Response({'error': 'Statement file not found on disk.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            statement.file.open('rb'),
            as_attachment=True,
            filename=statement.original_filename,
            content_type='application/pdf',
        )

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess a statement."""
        statement = self.get_object()
        statement.extracted_transactions.all().delete()
        statement.status = 'processing'
        statement.total_transactions_extracted = 0
        statement.save()

        try:
            process_statement(statement, statement.password)
        except Exception as e:
            statement.status = 'failed'
            statement.error_message = str(e)
            statement.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = self.get_serializer(statement)
        return Response(serializer.data)