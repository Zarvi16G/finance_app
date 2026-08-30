"""ExpectedGoal model: user-defined financial goals."""
from django.conf import settings
from django.db import models


class ExpectedGoal(models.Model):
    """
    Model representing user-defined financial goals.
    Tracks recent status (current progress) vs future status (expected targets).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ongoing', 'Ongoing'),
        ('achieved', 'Achieved'),
        ('failed', 'Failed'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goals',
        help_text="The user this goal belongs to",
    )

    title = models.CharField(
        max_length=100,
        help_text="Name of the financial goal"
    )

    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="The future target amount to achieve"
    )

    current_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="The current progress or recent status towards the target"
    )

    start_date = models.DateField(
        help_text="The start date for tracking this goal"
    )
    end_date = models.DateField(
        help_text="The target completion date for this goal"
    )

    category = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional category this goal is linked to (e.g. Shopping, Housing)"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ongoing',
        help_text="Current tracking status of the goal"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed context or strategy for this goal"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['end_date']

    def __str__(self):
        return f"{self.title} ({self.status}) - {self.current_amount}/{self.target_amount}"