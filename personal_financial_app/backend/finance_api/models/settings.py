"""User preferences and customizable choice models (types, categories).

Phase 0b (multi-tenancy for config/vocabulary):

* ``UserSetting`` is now one row per user (``owner`` OneToOne). It holds that
  user's currency and their Fernet-encrypted AI provider keys, so keys never
  leak between accounts.
* ``CustomType`` / ``CustomCategory`` / ``Choice`` carry an optional ``owner``.
  Rows with ``builtin=True`` (the seed vocabulary) keep ``owner=NULL`` and stay
  a shared global catalog; user-created rows are owned and private.
"""
from django.conf import settings
from django.db import models


class UserSetting(models.Model):
    AI_PROVIDER_CHOICES = [
        ('gemini', 'Gemini (Google)'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='setting',
        help_text="The user these settings belong to",
    )

    currency = models.CharField(max_length=10, default='COP')

    # AI model integration settings. API keys are stored Fernet-encrypted
    # (see crypto.py) inside ai_keys, keyed by provider name.
    ai_provider = models.CharField(
        max_length=20,
        choices=AI_PROVIDER_CHOICES,
        default='gemini',
    )
    ai_model = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Model name override; defaults to the provider's default model when empty",
    )
    ai_keys = models.JSONField(default=dict, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Setting'
        verbose_name_plural = 'User Settings'

    def __str__(self):
        return f"Currency: {self.currency} | AI: {self.ai_provider}"


class CustomType(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='custom_types',
        null=True, blank=True,
        help_text="Owning user; NULL for the shared built-in vocabulary",
    )
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['owner', 'name']

    def __str__(self):
        return self.name


class CustomCategory(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='custom_categories',
        null=True, blank=True,
        help_text="Owning user; NULL for the shared built-in vocabulary",
    )
    name = models.CharField(max_length=50)
    transaction_type = models.CharField(max_length=10, default='expense')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['owner', 'name']

    def __str__(self):
        return f"{self.name} ({self.transaction_type})"


class Choice(models.Model):
    CATEGORY = 'category'
    TYPE = 'type'
    CHOICE_TYPES = [
        (CATEGORY, 'Category'),
        (TYPE, 'Transaction Type'),
    ]
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='choices',
        null=True, blank=True,
        help_text="Owning user; NULL for built-in choices (builtin=True), which are shared",
    )
    name = models.CharField(max_length=50)
    choice_type = models.CharField(max_length=20, choices=CHOICE_TYPES)
    transaction_type = models.CharField(max_length=10, default='expense', blank=True)
    builtin = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    custom_type = models.OneToOneField(
        CustomType, on_delete=models.CASCADE,
        null=True, blank=True, related_name='choice'
    )
    custom_category = models.OneToOneField(
        CustomCategory, on_delete=models.CASCADE,
        null=True, blank=True, related_name='choice'
    )

    class Meta:
        ordering = ['sort_order', 'name']
        unique_together = ['owner', 'name', 'choice_type']

    def __str__(self):
        return f"{self.name} ({self.choice_type})"
