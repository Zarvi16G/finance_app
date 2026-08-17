"""AI integration services: provider clients and stored-settings management."""
from .providers import call_ai, suggest_categories
from . import settings as ai_settings

__all__ = ['call_ai', 'suggest_categories', 'ai_settings']