"""API views for AI integrations: categorization, chat assistant and AI settings."""
import json
import re

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Choice, CustomCategory, CategorizationMemory, ExtractedTransaction
from ..services.ai import providers as ai_providers
from ..services.ai import settings as ai_settings
from ..services.ai import key_validation
from ..services.chat_service import build_chat_prompt, parse_ai_reply, fallback_chat


class AICategorizationView(APIView):
    """
    Use the configured AI provider to suggest categories for transactions
    based on their descriptions.
    """
    def post(self, request):
        transaction_ids = request.data.get('transaction_ids', [])
        descriptions = request.data.get('descriptions', [])

        if not transaction_ids and not descriptions:
            return Response({'error': 'No transactions provided'}, status=status.HTTP_400_BAD_REQUEST)

        if transaction_ids:
            transactions = ExtractedTransaction.objects.filter(id__in=transaction_ids)
        else:
            transactions = [{'id': None, 'description': d, 'amount': 0, 'date': ''} for d in descriptions]

        txn_list = []
        for txn in transactions:
            if hasattr(txn, 'cleaned_description'):
                txn_list.append({
                    'id': txn.id,
                    'description': txn.cleaned_description,
                    'amount': float(txn.amount),
                    'date': str(txn.date) if hasattr(txn, 'date') else ''
                })
            else:
                txn_list.append(txn)

        categories = list(Choice.objects.filter(
            choice_type=Choice.CATEGORY
        ).values_list('name', flat=True))
        types = list(Choice.objects.filter(
            choice_type=Choice.TYPE
        ).values_list('name', flat=True))

        memories = list(CategorizationMemory.objects.filter(
            hit_count__gte=2
        ).values('pattern', 'category', 'transaction_type', 'hit_count')[:20])

        try:
            suggestions = ai_providers.suggest_categories(txn_list, categories, types, memories)
            if suggestions:
                return Response({'results': suggestions})
            return Response({'error': 'AI categorization failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'AI service unavailable: {str(e)}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class AIChatView(APIView):
    """
    Conversational AI assistant for transaction management.
    Uses the stored AI provider; falls back to the rule engine when offline.
    """
    def post(self, request):
        message = request.data.get('message', '')
        transaction_ids = request.data.get('transaction_ids', [])
        history = request.data.get('history', [])

        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        transactions = ExtractedTransaction.objects.filter(id__in=transaction_ids)
        all_categories = list(Choice.objects.filter(choice_type=Choice.CATEGORY).values_list('name', flat=True))
        all_types = list(Choice.objects.filter(choice_type=Choice.TYPE).values_list('name', flat=True))

        memories = CategorizationMemory.objects.filter(hit_count__gte=2)[:20]
        system_prompt = build_chat_prompt(message, transactions, all_categories, all_types, memories, history)

        ai_reply = ai_providers.call_ai(system_prompt, message, history)

        if ai_reply:
            reply, actions = parse_ai_reply(ai_reply)
            return Response({'reply': reply, 'actions': actions})

        # --- Rule-based fallback ---
        reply, actions = fallback_chat(message, transactions, all_categories, all_types)
        return Response({'reply': reply, 'actions': actions})


class AISettingsView(APIView):
    """
    Manage AI provider settings and API keys.

    GET returns only masked keys (safe for display).
    PUT accepts {provider?, model?, api_key?} — an api_key is validated live
    against the provider before being stored (encrypted).
    """

    def get(self, request):
        return Response(ai_settings.get_public_config())

    def put(self, request):
        provider = request.data.get('provider')
        model = request.data.get('model')
        api_key = request.data.get('api_key')

        try:
            if provider or model is not None:
                ai_settings.set_provider_and_model(provider=provider, model=model)
            if api_key:
                target = provider or ai_settings.get_provider()
                verdict = key_validation.validate_api_key(target, api_key)
                if not verdict['valid']:
                    return Response(
                        {
                            'error': verdict['message'],
                            'error_code': verdict['code'],
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                ai_settings.save_api_key(target, api_key)
        except ValueError as e:
            message = str(e)
            code = key_validation.CODE_INVALID_KEY if 'API key' in message else key_validation.CODE_UNKNOWN
            return Response({'error': message, 'error_code': code}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ai_settings.get_public_config())