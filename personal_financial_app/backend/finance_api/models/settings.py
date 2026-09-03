"""User preferences and customizable choice models (types, categories)."""
from django.conf import settings
from django.db import models


class UserSetting(models.Model):
    AI_PROVIDER_CHOICES = [
        ('gemini', 'Gemini (Google)'),
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
    ]

    # One settings row per user. This used to be a single global row (pk=1),
    # which meant every account shared the same currency and the same
    # encrypted AI API keys.
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='setting',
        help_text="The user these settings belong to",
    )

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


class OwnedVocabularyQuerySet(models.QuerySet):
    """Shared scoping for the user vocabulary (types, categories, choices).

    Rows with `builtin=True` (or no owner) are the seeded catalog shared by
    everyone; anything a user creates is private to that user.
    """

    def visible_to(self, user):
        return self.filter(models.Q(owner=user) | models.Q(owner__isnull=True))

    def owned_by(self, user):
        return self.filter(owner=user)


class CustomType(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='custom_types',
        null=True,
        help_text="Owner of this custom type; null means seeded/global",
    )
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OwnedVocabularyQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'name'],
                name='uniq_customtype_owner_name',
            ),
        ]

    def __str__(self):
        return self.name


class CustomCategory(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='custom_categories',
        null=True,
        help_text="Owner of this custom category; null means seeded/global",
    )
    name = models.CharField(max_length=50)
    transaction_type = models.CharField(max_length=10, default='expense')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OwnedVocabularyQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'name'],
                name='uniq_customcategory_owner_name',
            ),
        ]

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
        null=True,
        help_text="Owner of this choice; null means seeded/built-in and shared",
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

    objects = OwnedVocabularyQuerySet.as_manager()

    class Meta:
        ordering = ['sort_order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'name', 'choice_type'],
                name='uniq_choice_owner_name_type',
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.choice_type})"
