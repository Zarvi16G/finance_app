"""AI configuration: stored API keys (encrypted), provider and model selection."""
from ...crypto import encrypt_text, decrypt_text, mask_secret
from ...models import UserSetting

PROVIDERS = ('gemini', 'openai', 'anthropic')

PROVIDER_DEFAULT_MODELS = {
    'gemini': 'gemini-2.5-flash',
    'openai': 'gpt-4o-mini',
    'anthropic': 'claude-3-5-haiku-latest',
}

PROVIDER_LABELS = {
    'gemini': 'Gemini (Google)',
    'openai': 'OpenAI',
    'anthropic': 'Anthropic',
}


def get_setting() -> UserSetting:
    setting, _ = UserSetting.objects.get_or_create(pk=1)
    return setting


def get_provider() -> str:
    return get_setting().ai_provider or 'gemini'


def get_model(provider: str) -> str:
    setting = get_setting()
    if setting.ai_model and provider == (setting.ai_provider or 'gemini'):
        return setting.ai_model
    return PROVIDER_DEFAULT_MODELS.get(provider, PROVIDER_DEFAULT_MODELS['gemini'])


def get_api_key(provider: str = None) -> str:
    """Return the decrypted API key for a provider.

    Falls back to the GEMINI_API_KEY environment variable for gemini when
    no key has been stored (backwards compatibility with the previous setup).
    """
    setting = get_setting()
    provider = provider or setting.ai_provider or 'gemini'
    encrypted = (setting.ai_keys or {}).get(provider, '')
    if encrypted:
        return decrypt_text(encrypted)
    if provider == 'gemini' and encrypted == '':
        from django.conf import settings as django_settings
        return getattr(django_settings, 'GEMINI_API_KEY', '')
    return ''


def save_api_key(provider: str, api_key: str) -> None:
    """Encrypt and store an API key for the given provider."""
    if not provider or provider not in PROVIDERS:
        raise ValueError(f'Unsupported provider: {provider!r}')
    if not api_key or not api_key.strip():
        raise ValueError('API key cannot be empty')
    setting = get_setting()
    keys = dict(setting.ai_keys or {})
    keys[provider] = encrypt_text(api_key.strip())
    setting.ai_keys = keys
    setting.save()


def set_provider_and_model(provider: str = None, model: str = None) -> UserSetting:
    setting = get_setting()
    if provider:
        if provider not in PROVIDERS:
            raise ValueError(f'Unsupported provider: {provider!r}')
        setting.ai_provider = provider
    if model is not None:
        setting.ai_model = model.strip()[:100]
    setting.save()
    return setting


def get_public_config() -> dict:
    """Masked view of AI settings, safe to expose through the API."""
    setting = get_setting()
    keys = setting.ai_keys or {}
    return {
        'provider': setting.ai_provider or 'gemini',
        'model': setting.ai_model or '',
        'keys': {
            provider: mask_secret(decrypt_text(keys[provider])) if keys.get(provider) else None
            for provider in PROVIDERS
        },
        'default_models': PROVIDER_DEFAULT_MODELS,
    }