"""API views for smart financial analysis (Ollama/DeepSeek + rule fallback)."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import FinancialRecord, ExpectedGoal
from ..services.analysis_service import run_financial_analysis
from ..services.filters import apply_filters_to_queryset


class AIAnalysisView(APIView):
    """
    API endpoint that performs smart financial data analyses.
    Aggregates filtered incomes and expenses, identifies high spending areas,
    evaluates goal statuses, and sends a context-rich prompt to local Ollama
    or DeepSeek. Automatically falls back to an intelligent rule-based expert system
    if no active external local LLM is detected.
    """
    def post(self, request, *args, **kwargs):
        # 1. Fetch current financial dataset & apply active filtering
        records = FinancialRecord.objects.all()
        records = apply_filters_to_queryset(request, records)

        # 2. Retrieve financial goals
        goals = ExpectedGoal.objects.all()

        result = run_financial_analysis(records, goals)

        return Response(result, status=status.HTTP_200_OK)