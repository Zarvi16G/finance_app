"""User preferences and customizable choice models (types, categories)."""
from django.db import models


class UserSetting(models.Model):
    AI_PROVIDER_CHOICES = [
        ('gemini', 'Gemini (Google)'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
    ]

    currency = models.CharField(max_length=10, default='USD')

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
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CustomCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    transaction_type = models.CharField(max_length=10, default='expense')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.transaction_type})"


class Choice(models.Model):
    CATEGORY = 'category'
    TYPE = 'type'
    CHOICE_TYPES = [
        (CATEGORY, 'Category'),
        (TYPE, 'Transaction Type'),
    ]
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
        unique_together = ['name', 'choice_type']

    def __str__(self):
        return f"{self.name} ({self.choice_type})"