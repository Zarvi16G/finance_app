"""Debt model: user debts (loans, credit cards, mortgages, etc.)."""
import math
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Debt(models.Model):
    """
    Model for tracking user debts (loans, credit cards, mortgages, etc.)
    """
    DEBT_TYPES = [
        ('credit_card', 'Credit Card'),
        ('personal_loan', 'Personal Loan'),
        ('mortgage', 'Mortgage'),
        ('auto_loan', 'Auto Loan'),
        ('student_loan', 'Student Loan'),
        ('medical_debt', 'Medical Debt'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paid_off', 'Paid Off'),
        ('defaulted', 'Defaulted'),
        ('in_grace', 'In Grace Period'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='debts',
        help_text="The user this debt belongs to",
    )
    name = models.CharField(max_length=100)
    debt_type = models.CharField(max_length=20, choices=DEBT_TYPES)
    creditor = models.CharField(max_length=100)
    original_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        default='COP',
        help_text="ISO 4217 code for every amount on this debt",
    )
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Annual percentage rate
    minimum_payment = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Day of month the payment is due (1-31)"
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # Expected payoff date
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.debt_type}) - ${self.current_balance}"

    @property
    def monthly_interest(self):
        return (self.current_balance * self.interest_rate / 100) / 12

    @property
    def payoff_months_remaining(self):
        if self.minimum_payment <= self.monthly_interest:
            return None  # Never pays off at minimum payment
        return math.ceil(
            math.log(1 + (self.current_balance * (self.interest_rate / 100 / 12)) / self.minimum_payment)
            / math.log(1 + self.interest_rate / 100 / 12)
        )