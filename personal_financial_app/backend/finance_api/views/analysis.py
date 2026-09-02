"""API views for smart financial analysis (Ollama/DeepSeek + rule fallback)."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiTypes

from ..models import FinancialRecord, ExpectedGoal
from ..services.analysis_service import run_financial_analysis
from ..services.filters import apply_filters_to_queryset


@extend_schema(
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT},
    description=(
        'Runs a smart financial analysis over the filtered records and goals, returning '
        'an executive health audit, budget leak analysis and actionable steps.'
    ),
)
class AIAnalysisView(APIView):
    """
    API endpoint that performs smart financial data analyses.
    Aggregates filtered incomes and expenses, identifies high spending areas,
    evaluates goal statuses, and sends a context-rich prompt to local Ollama
    or DeepSeek. Automatically falls back to an intelligent rule-based expert system
    if no active external local LLM is detected.
    """
    def post(self, request, *args, **kwargs):
        # 1. Fetch this user's financial dataset & apply active filtering
        records = FinancialRecord.objects.filter(owner=request.user)
        records = apply_filters_to_queryset(request, records)

        # 2. Retrieve this user's financial goals
        goals = ExpectedGoal.objects.filter(owner=request.user)

        result = run_financial_analysis(records, goals)

        return Response(result, status=status.HTTP_200_OK)