"""AI provider clients (Gemini, OpenAI, Anthropic).

All providers are called over plain HTTP (requests) with a strict timeout.
Errors are logged with the provider's raw output and reported as empty
strings so callers can fall back to the rule-based engines.
"""
import json
import logging

import requests

from . import settings as ai_settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class AIProviderError(Exception):
    pass


def _gemini_generate(api_key, model, system_prompt, user_message, history=None, json_mode=False):
    contents = []
    if history:
        for h in history[-6:]:
            role = 'user' if h.get('role') == 'user' else 'model'
            contents.append({'role': role, 'parts': [{'text': h.get('content', '')}]})
    contents.append({'role': 'user', 'parts': [{'text': user_message}]})

    payload = {
        "systemInstruction": {'parts': [{'text': system_prompt}]},
        "contents": contents,
    }
    if json_mode:
        payload["generationConfig"] = {"responseMimeType": "application/json"}

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        logger.warning(
            'Gemini API error status=%s model=%s body=%s',
            resp.status_code, model, resp.text[:500],
        )
        raise AIProviderError(f'Gemini API error {resp.status_code}')
    candidates = resp.json().get('candidates', [])
    if not candidates:
        logger.warning('Gemini returned no candidates model=%s body=%s', model, resp.text[:500])
        raise AIProviderError('Gemini returned no candidates')
    return candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')


def _openai_generate(api_key, model, system_prompt, user_message, history=None, json_mode=False):
    messages = [{'role': 'system', 'content': system_prompt}]
    if history:
        for h in history[-6:]:
            role = 'user' if h.get('role') == 'user' else 'assistant'
            messages.append({'role': role, 'content': h.get('content', '')})
    messages.append({'role': 'user', 'content': user_message})

    payload = {
        'model': model,
        'messages': messages,
        'temperature': 0.3,
    }
    if json_mode:
        payload['response_format'] = {'type': 'json_object'}

    resp = requests.post(
        'https://api.openai.com/v1/chat/completions',
        json=payload,
        headers={'Authorization': f'Bearer {api_key}'},
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        logger.warning(
            'OpenAI API error status=%s model=%s body=%s',
            resp.status_code, model, resp.text[:500],
        )
        raise AIProviderError(f'OpenAI API error {resp.status_code}')
    choices = resp.json().get('choices', [])
    if not choices:
        logger.warning('OpenAI returned no choices model=%s body=%s', model, resp.text[:500])
        raise AIProviderError('OpenAI returned no choices')
    return choices[0].get('message', {}).get('content', '')


def _anthropic_generate(api_key, model, system_prompt, user_message, history=None, json_mode=False):
    messages = []
    if history:
        for h in history[-6:]:
            role = 'user' if h.get('role') == 'user' else 'assistant'
            messages.append({'role': role, 'content': h.get('content', '')})
    messages.append({'role': 'user', 'content': user_message})

    payload = {
        'model': model,
        'max_tokens': 2000,
        'system': system_prompt,
        'messages': messages,
    }
    if json_mode:
        payload['temperature'] = 0.2

    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        json=payload,
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        logger.warning(
            'Anthropic API error status=%s model=%s body=%s',
            resp.status_code, model, resp.text[:500],
        )
        raise AIProviderError(f'Anthropic API error {resp.status_code}')
    content = resp.json().get('content', [])
    if not content:
        logger.warning('Anthropic returned no content model=%s body=%s', model, resp.text[:500])
        raise AIProviderError('Anthropic returned no content')
    return ''.join(block.get('text', '') for block in content if block.get('type') == 'text')


_PROVIDER_CLIENTS = {
    'gemini': _gemini_generate,
    'openai': _openai_generate,
    'anthropic': _anthropic_generate,
}


def call_ai(system_prompt, user_message, history=None, provider=None, model=None, api_key=None, user=None):
    """Call the configured AI provider and return the text response.

    Resolves provider/model/api key from `user`'s stored settings when not
    given explicitly. Returns '' on any failure so callers can use rule
    fallbacks.
    """
    provider = provider or ai_settings.get_provider(user)
    api_key = api_key or ai_settings.get_api_key(user, provider)
    model = model or ai_settings.get_model(user, provider)

    if not api_key:
        return ''

    client = _PROVIDER_CLIENTS.get(provider)
    if not client:
        return ''

    try:
        return client(api_key, model, system_prompt, user_message, history)
    except Exception:
        logger.exception('AI provider call failed provider=%s model=%s', provider, model)
        return ''


def suggest_categories(transactions, categories, types, memories=None, user=None):
    """Ask the AI to categorize a batch of transactions; returns [] on failure."""
    prompt = _build_suggestion_prompt(transactions, categories, types, memories)
    provider = ai_settings.get_provider(user)
    api_key = ai_settings.get_api_key(user, provider)
    model = ai_settings.get_model(user, provider)

    if not api_key:
        logger.warning('AI categorization skipped: no API key for provider=%s', provider)
        return []

    client = _PROVIDER_CLIENTS.get(provider)
    if not client:
        logger.warning('AI categorization skipped: unsupported provider=%s', provider)
        return []

    try:
        result = client(api_key, model, prompt, 'Return only the JSON array, no extra text.', json_mode=True)
    except Exception:
        logger.exception('AI categorization failed provider=%s model=%s', provider, model)
        return []

    if not result:
        logger.warning('AI categorization returned empty response provider=%s model=%s', provider, model)
        return []
    try:
        cleaned = result.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[-1]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
        # JSON mode may wrap the array in an object on some providers: unwrap it
        if not cleaned.startswith('['):
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed.get('results', [])
        suggestions = json.loads(cleaned)
        return suggestions if isinstance(suggestions, list) else [suggestions]
    except (json.JSONDecodeError, TypeError):
        logger.exception('AI categorization returned unparsable JSON provider=%s result=%s', provider, result[:500])
        return []


def _build_suggestion_prompt(transactions, categories, types, memories=None):
    txn_json = json.dumps(transactions, indent=2)
    memory_context = ''
    if memories:
        memory_context = '\nLearned patterns from past confirmations:\n' + json.dumps(memories, indent=2)

    prompt = f"""You are a financial transaction categorization expert. Categorize the following transactions based on their description.

Available categories: {', '.join(categories)}
Available types: {', '.join(types)}{memory_context}

Transactions to categorize:
{txn_json}

Return a JSON array with each transaction categorized:
[
  {{
    "id": "transaction_id_or_null",
    "description": "original description",
    "suggested_category": "category_name",
    "suggested_type": "income_or_expense",
    "confidence": 0.95,
    "reasoning": "brief explanation"
  }}
]

Only return the JSON array, no additional text."""

    return prompt