"""Itemised budgets for life-experience goals.

A trip is not one number — it is flights, a hotel, food, tickets and the
things that go wrong. Breaking it down is what makes the target believable,
and it is what lets the app show where the money is actually planned to go.

Estimates and actuals are kept side by side rather than the estimate being
overwritten: the gap between what you planned and what you spent is the
useful part, and it is what makes the next trip's estimate better.
"""
from django.db import models


class ExperienceBudgetItem(models.Model):
    """One line of an experience goal's budget."""

    CATEGORIES = [
        ('transport', 'Transport'),
        ('lodging', 'Lodging'),
        ('food', 'Food'),
        ('activities', 'Activities'),
        ('insurance', 'Insurance & Visas'),
        ('shopping', 'Shopping'),
        ('buffer', 'Buffer'),
        ('other', 'Other'),
    ]

    goal = models.ForeignKey(
        'finance_api.ExpectedGoal',
        on_delete=models.CASCADE,
        related_name='budget_items',
        help_text="The experience this line belongs to; ownership follows it",
    )
    label = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='other')
    estimated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    actual_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Filled in once the money is actually spent",
    )
    # A single trip can legitimately mix currencies: flights in USD, the hotel
    # in EUR, food in the local one.
    currency = models.CharField(max_length=3, default='COP')
    is_booked = models.BooleanField(
        default=False,
        help_text="Already paid or reserved, so the price will not move",
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'label']

    def __str__(self):
        return f'{self.label} ({self.category}): {self.estimated_amount} {self.currency}'
