"""FinancialRecord model: incomes & expenses."""
from django.conf import settings
from django.db import models


class FinancialRecord(models.Model):
    RECORD_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='financial_records',
        help_text="The user this record belongs to",
    )

    CATEGORY_CHOICES = [
        ('Salary', 'Salary'),
        ('Investment', 'Investment'),
        ('Food & Dining', 'Food & Dining'),
        ('Rent & Housing', 'Rent & Housing'),
        ('Utilities', 'Utilities'),
        ('Entertainment & Leisure', 'Entertainment & Leisure'),
        ('Transportation', 'Transportation'),
        ('Healthcare', 'Healthcare'),
        ('Education', 'Education'),
        ('Shopping', 'Shopping'),
        ('Other', 'Other'),
    ]

    ACCOUNT_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('cash_loan', 'Cash Loan'),
        ('bank_loan', 'Bank Loan'),
        ('cash', 'Cash'),
        ('business_card', 'Business Card'),
        ('bre_b', 'Bre-B (Employee Special Card)'),
        ('other', 'Other'),
    ]

    type = models.CharField(
        max_length=10,
        help_text="Type of transaction: income, expense, or custom"
    )

    category = models.CharField(
        max_length=50,
        default='Other',
        help_text="Financial category of the transaction"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Monetary value of the transaction"
    )

    # The currency the money actually moved in. Never rewritten: totals in the
    # user's base currency are derived at read time (see currency_service).
    currency = models.CharField(
        max_length=3,
        default='COP',
        help_text="ISO 4217 code of the amount above",
    )

    date = models.DateField(
        help_text="Date when the transaction occurred"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Notes/details about this transaction"
    )

    account_bank = models.CharField(
        max_length=50,
        choices=ACCOUNT_CHOICES,
        default='cash',
        help_text="The bank account, card, or method used for this record"
    )

    account_bank_other = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Specify custom account/method when 'Other' is selected"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="System timestamp when this record was created"
    )

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.type.capitalize()} - {self.category}: {self.amount} ({self.date})"