"""Life experiences: what a trip will cost, and how close you are to it.

Two numbers that are easy to confuse and are kept apart on purpose:

  target_amount   what the user decided to save for (they own this number)
  budget total    what the itemised lines add up to

They are not forced to match. The gap between them is the useful signal — a
trip budgeted at 8M against a 7M target is a plan with a hole in it — and
silently overwriting the user's target with the sum of their line items would
hide exactly that.
"""
from decimal import Decimal

from ..models import ExpectedGoal
from ..models.experiences import ExperienceBudgetItem
from . import currency_service


def budget_summary(goal, base: str) -> dict:
    """Cost breakdown for one experience, totalled in the base currency."""
    items = goal.budget_items.all()

    estimated = currency_service.sum_in(items, base, field='estimated_amount')
    booked = currency_service.sum_in(
        items.filter(is_booked=True), base, field='estimated_amount'
    )
    # Only lines that have actually been spent count toward the actual total.
    spent_items = items.exclude(actual_amount__isnull=True)
    actual = currency_service.sum_in(spent_items, base, field='actual_amount')

    by_category = []
    for category in dict.fromkeys(items.values_list('category', flat=True)):
        group = items.filter(category=category)
        total = currency_service.sum_in(group, base, field='estimated_amount')
        by_category.append({
            'category': category,
            'estimated': float(total),
            'count': group.count(),
            'percentage': None,  # filled in below, once the total is known
        })
    for row in by_category:
        row['percentage'] = (
            round(row['estimated'] / float(estimated) * 100, 2)
            if estimated > 0 else 0
        )
    by_category.sort(key=lambda row: -row['estimated'])

    target = currency_service.convert_safe(
        goal.target_amount, goal.currency or base, base
    )
    saved = currency_service.convert_safe(
        goal.current_amount, goal.currency or base, base
    )

    return {
        'estimated_total': float(estimated),
        'booked_total': float(booked),
        'actual_total': float(actual),
        'items_priced': items.count(),
        'items_booked': items.filter(is_booked=True).count(),
        'by_category': by_category,
        # Where the plan stands against what the user set out to save.
        'target_amount': float(target),
        'saved_amount': float(saved),
        'still_to_save': float(max(target - saved, Decimal('0'))),
        # Positive means the itemised plan costs more than the target.
        'budget_vs_target': float(estimated - target),
        'progress_percentage': (
            round(float(saved / target * 100), 2) if target > 0 else 0
        ),
    }


def experiences_for(user, base: str) -> dict:
    """Every experience goal with its budget, plus a portfolio-level total."""
    goals = ExpectedGoal.objects.filter(
        owner=user, goal_type='experience'
    ).prefetch_related('budget_items').order_by('end_date')

    entries = []
    for goal in goals:
        entries.append({
            'id': goal.id,
            'title': goal.title,
            'status': goal.status,
            'location': goal.location,
            'currency': goal.currency,
            'start_date': goal.start_date.isoformat() if goal.start_date else None,
            'end_date': goal.end_date.isoformat() if goal.end_date else None,
            'experience_date': (
                goal.experience_date.isoformat() if goal.experience_date else None
            ),
            'description': goal.description,
            'budget': budget_summary(goal, base),
        })

    return {
        'base_currency': base,
        'count': len(entries),
        'total_estimated': sum(e['budget']['estimated_total'] for e in entries),
        'total_saved': sum(e['budget']['saved_amount'] for e in entries),
        'total_still_to_save': sum(e['budget']['still_to_save'] for e in entries),
        'experiences': entries,
    }
