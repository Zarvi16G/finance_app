"""Life experiences: what a trip will cost, and how close you are to it.

Two numbers that are easy to confuse and are kept apart on purpose:

  target_amount   what the user decided to save for (they own this number)
  budget total    what the itemised lines add up to

They are not forced to match. The gap between them is the useful signal — a
trip budgeted at 8M against a 7M target is a plan with a hole in it — and
silently overwriting the user's target with the sum of their line items would
hide exactly that.
"""
from ..models import ExpectedGoal
from ..models.experiences import ExperienceBudgetItem
from . import currency_service
from .currency_service import Total


def budget_summary(goal, base: str) -> tuple[dict, list[Total]]:
    """Cost breakdown for one experience, totalled in the base currency.

    Returns the payload plus every Total that went into it, so the caller can
    report in one place what could not be converted. A trip that mixes
    currencies is the normal case here — flights in dollars, the hotel in
    pesos — which is exactly why none of these figures may be added without
    converting first.
    """
    items = goal.budget_items.all()
    goal_currency = goal.currency or base

    estimated = currency_service.sum_in(items, base, field='estimated_amount')
    booked = currency_service.sum_in(
        items.filter(is_booked=True), base, field='estimated_amount'
    )
    # Only lines that have actually been spent count toward the actual total.
    spent_items = items.exclude(actual_amount__isnull=True)
    actual = currency_service.sum_in(spent_items, base, field='actual_amount')

    by_category = []
    category_totals = []
    for category in dict.fromkeys(items.values_list('category', flat=True)):
        group = items.filter(category=category)
        total = currency_service.sum_in(group, base, field='estimated_amount')
        category_totals.append(total)
        by_category.append({
            'category': category,
            'estimated': float(total),
            'count': group.count(),
            # A share of a total that excluded something would be a share of
            # the wrong denominator, so it stays null rather than misleading.
            'percentage': (
                round(float(total / estimated) * 100, 2)
                if estimated > 0 and estimated.complete else None
            ),
        })
    by_category.sort(key=lambda row: -row['estimated'])

    target = Total.converted(goal.target_amount, goal_currency, base)
    saved = Total.converted(goal.current_amount, goal_currency, base)
    still_to_save = target - saved

    totals = [estimated, booked, actual, target, saved, *category_totals]

    payload = {
        'estimated_total': float(estimated),
        'booked_total': float(booked),
        'actual_total': float(actual),
        'items_priced': items.count(),
        'items_booked': items.filter(is_booked=True).count(),
        'by_category': by_category,
        # Where the plan stands against what the user set out to save.
        'target_amount': float(target),
        'saved_amount': float(saved),
        'still_to_save': float(still_to_save) if still_to_save > 0 else 0.0,
        # Positive means the itemised plan costs more than the target.
        'budget_vs_target': float(estimated - target),
        'progress_percentage': (
            round(float(saved / target) * 100, 2) if target > 0 else 0
        ),
        'conversion': currency_service.conversion_report(*totals),
    }
    return payload, totals


def experiences_for(user, base: str) -> dict:
    """Every experience goal with its budget, plus a portfolio-level total."""
    goals = ExpectedGoal.objects.filter(
        owner=user, goal_type='experience'
    ).prefetch_related('budget_items').order_by('end_date')

    entries = []
    # The portfolio row is built by adding Totals, not the floats already
    # rendered for each trip: floats have lost the currency that makes the
    # addition legal, and lost the record of anything left out.
    grand_estimated = Total.zero(base)
    grand_saved = Total.zero(base)
    grand_still = Total.zero(base)
    every_total: list[Total] = []

    for goal in goals:
        budget, totals = budget_summary(goal, base)
        every_total.extend(totals)
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
            'budget': budget,
        })
        grand_estimated = grand_estimated + Total.of(budget['estimated_total'], base)
        grand_saved = grand_saved + Total.of(budget['saved_amount'], base)
        grand_still = grand_still + Total.of(budget['still_to_save'], base)

    return {
        'base_currency': base,
        'count': len(entries),
        'total_estimated': float(grand_estimated),
        'total_saved': float(grand_saved),
        'total_still_to_save': float(grand_still),
        'experiences': entries,
        'conversion': currency_service.conversion_report(*every_total),
    }
