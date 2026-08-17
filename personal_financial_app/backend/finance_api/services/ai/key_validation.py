"""AI API key validation engine.

When a user stores an API key, it is checked live against the provider's API
and the provider error output is classified so the UI can explain exactly
what happened (invalid key, rate limit, billing/quota, etc.).
"""
import requests

REQUEST_TIMEOUT = 10

# Classification codes returned to clients
CODE_INVALID_KEY = 'invalid_key'
CODE_RATE_LIMIT = 'rate_limit'
CODE_BILLING = 'billing_error'
CODE_PERMISSION = 'permission_denied'
CODE_NETWORK = 'network_error'
CODE_UNKNOWN = 'unknown_error'

# Human-readable messages mapped 1:1 to codes
CODE_MESSAGES = {
    CODE_INVALID_KEY: 'This API key was not recognized by the provider. Check it was copied correctly.',
    CODE_RATE_LIMIT: 'The provider rate limit was reached. Wait a moment and try again.',
    CODE_BILLING: 'The provider blocked this key for billing reasons. Enable billing or add a payment method in the provider console.',
    CODE_PERMISSION: 'The provider rejected this key: it exists but is not allowed to access this API.',
    CODE_NETWORK: 'Could not reach the provider to verify the key. Check your connection and try again.',
    CODE_UNKNOWN: 'The provider rejected this key for an unknown reason.',
}

# Body keywords that hint at billing/quota or permission issues
BILLING_HINTS = ('billing', 'quota', 'payment', 'insufficient')
PERMISSION_HINTS = ('permission', 'access', 'forbidden')


def classify_error(status_code: int, body: str) -> str:
    """Map a provider HTTP response to one of the classification codes.

    Priority: status code first, then provider hints found in the body.
    """
    if status_code == 401:
        return CODE_INVALID_KEY
    if status_code == 429:
        return CODE_RATE_LIMIT
    if status_code == 402:
        return CODE_BILLING
    if status_code == 403:
        lowered = body.lower()
        if any(hint in lowered for hint in BILLING_HINTS):
            return CODE_BILLING
        return CODE_PERMISSION
    if status_code == 400 and 'api key not valid' in body.lower():
        return CODE_INVALID_KEY
    if status_code >= 500:
        return CODE_UNKNOWN
    return CODE_UNKNOWN


def _check_gemini(api_key: str) -> tuple[int, str]:
    resp = requests.get(
        f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}',
        timeout=REQUEST_TIMEOUT,
    )
    return resp.status_code, resp.text


def _check_openai(api_key: str) -> tuple[int, str]:
    resp = requests.get(
        'https://api.openai.com/v1/models',
        headers={'Authorization': f'Bearer {api_key}'},
        timeout=REQUEST_TIMEOUT,
    )
    return resp.status_code, resp.text


def _check_anthropic(api_key: str) -> tuple[int, str]:
    resp = requests.get(
        'https://api.anthropic.com/v1/models',
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
        },
        timeout=REQUEST_TIMEOUT,
    )
    return resp.status_code, resp.text


_CHECKERS = {
    'gemini': _check_gemini,
    'openai': _check_openai,
    'anthropic': _check_anthropic,
}


def validate_api_key(provider: str, api_key: str) -> dict:
    """Check an API key against the provider and return a verdict.

    Returns one of:
      {'valid': True}
      {'valid': False, 'code': CODE_*, 'message': str}
    """
    if not api_key or not api_key.strip():
        return {'valid': False, 'code': CODE_INVALID_KEY, 'message': 'API key cannot be empty.'}

    checker = _CHECKERS.get(provider)
    if not checker:
        return {'valid': False, 'code': CODE_UNKNOWN, 'message': 'Unsupported provider.'}

    try:
        status_code, body = checker(api_key.strip())
    except requests.RequestException as exc:
        return {'valid': False, 'code': CODE_NETWORK, 'message': CODE_MESSAGES[CODE_NETWORK]}

    if status_code == 200:
        return {'valid': True}

    code = classify_error(status_code, body)
    return {'valid': False, 'code': code, 'message': CODE_MESSAGES[code]}