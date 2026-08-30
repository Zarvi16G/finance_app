"""Bank statement domain: BankStatement, ExtractedTransaction and CategorizationMemory."""
import uuid

from django.conf import settings
from django.db import models

from .records import FinancialRecord


class BankStatement(models.Model):
    """
    Model for uploaded bank statement PDFs.
    Tracks processing status and extracted transaction count.
    """
    STATEMENT_TYPES = [
        ('savings', 'Savings Account'),
        ('checking', 'Checking Account'),
        ('credit_card', 'Credit Card'),
        ('loan', 'Loan Statement'),
        ('investment', 'Investment Account'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('extracted', 'Extracted'),
        ('review_pending', 'Review Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bank_statements',
        help_text="The user who uploaded this statement",
    )
    file = models.FileField(upload_to='bank_statements/')
    original_filename = models.CharField(max_length=255)
    content_hash = models.CharField(max_length=64, db_index=True, blank=True, null=True, help_text="SHA256 hash of file content for duplicate detection (unique per owner, see Meta)")
    bank_name = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100, null=True, blank=True, help_text="Password if the file has one")
    account_number = models.CharField(max_length=50, blank=True)
    statement_type = models.CharField(max_length=20, choices=STATEMENT_TYPES, default='other', help_text="Type of statement: savings, checking, credit_card, etc.")
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="ISO 4217 currency code of the statement (e.g. COP, USD, EUR). Editable after extraction.",
    )
    statement_period_start = models.DateField(null=True, blank=True)
    statement_period_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    total_transactions_extracted = models.IntegerField(default=0)
    total_transactions_imported = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    totals_updated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Last time usd_amount values on extracted transactions were refreshed via live rates.",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']
        unique_together = ['owner', 'content_hash']
        indexes = [
            models.Index(fields=['content_hash']),
            models.Index(fields=['statement_type', 'statement_period_start', 'statement_period_end']),
        ]

    def delete(self, *args, **kwargs):
        if self.file and self.file.storage.exists(self.file.name):
            self.file.storage.delete(self.file.name)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.original_filename} ({self.status})"


class ExtractedTransaction(models.Model):
    """
    Temporary model for transactions extracted from PDF before user review.
    """
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('unknown', 'Unknown'),
    ]

    CATEGORY_CHOICES = FinancialRecord.CATEGORY_CHOICES

    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='extracted_transactions')
    raw_description = models.TextField()
    cleaned_description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="ISO 4217 currency code of this transaction (inherits from statement, editable in review)",
    )
    usd_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Amount converted to USD using the user's active DailyUserSnapshot rate",
    )
    date = models.DateField()
    transaction_type = models.CharField(max_length=10, default='unknown')
    suggested_category = models.CharField(max_length=50, default='Other')
    confidence_score = models.FloatField(default=0.0)
    needs_review = models.BooleanField(default=True)
    is_reviewed = models.BooleanField(default=False)
    user_confirmed_category = models.CharField(max_length=50, blank=True, null=True)
    user_confirmed_type = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date', '-created_at']

    @property
    def owner(self):
        """Ownership is inherited from the parent statement (no own column).

        Lets :class:`finance_api.permissions.IsOwner` treat extracted
        transactions uniformly; querysets still scope via ``statement__owner``.
        """
        return self.statement.owner

    def __str__(self):
        return f"{self.cleaned_description}: {self.amount} ({self.suggested_category})"


class CategorizationMemory(models.Model):
    """
    Learned pattern -> category mapping used to improve AI suggestions over time.

    Scoped per user (Phase 0b): one person's confirmation habits must not shape
    another person's AI suggestions, and the stored patterns are derived from
    their own transaction descriptions.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categorization_memories',
        null=True,  # Phase 0b: nullable now -> backfilled (migration 0021-0022)
        help_text="The user whose confirmations produced this pattern",
    )
    pattern = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=50)
    transaction_type = models.CharField(max_length=10)
    hit_count = models.IntegerField(default=1)
    last_used = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['owner', 'pattern', 'category', 'transaction_type']
        ordering = ['-hit_count', '-last_used']

    def __str__(self):
        return f"{self.pattern} -> {self.category} ({self.transaction_type})"

"""Statement calculation is no correct, it should be based on the transactions, not the statement itself. 
The statement is just a container for the transactions."""