"""Model signals that keep derived data in sync automatically.

1. Custom types/categories -> Choice vocabulary (keeps every form dropdown
   in the frontend porcelain-clean whenever the user edits the vocabulary).
2. FinancialRecord save/delete -> recompute the monthly FinancialSnapshot,
   which the analytics endpoint serves first (cache-first dashboard).
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import CustomType, CustomCategory, Choice, FinancialRecord
from .services.snapshot_service import compute_monthly_snapshot


@receiver(post_save, sender=CustomType)
def sync_custom_type_to_choice(sender, instance, created, **kwargs):
    # Types are plain labels with no extra attributes; only the name can vary.
    # The mirrored Choice inherits the owner so it stays private to that user.
    if created:
        Choice.objects.get_or_create(
            owner=instance.owner,
            name=instance.name,
            choice_type=Choice.TYPE,
            defaults=dict(
                builtin=False,
                custom_type=instance,
            )
        )
    else:
        Choice.objects.update_or_create(
            custom_type=instance,
            defaults=dict(name=instance.name)
        )


@receiver(post_delete, sender=CustomType)
def cleanup_custom_type_choice(sender, instance, **kwargs):
    Choice.objects.filter(custom_type=instance).delete()


@receiver(post_save, sender=CustomCategory)
def sync_custom_category_to_choice(sender, instance, created, **kwargs):
    # Categories also carry a transaction_type (income/expense direction),
    # which the Choice must mirror for the review UI to prefill correctly.
    if created:
        Choice.objects.get_or_create(
            owner=instance.owner,
            name=instance.name,
            choice_type=Choice.CATEGORY,
            defaults=dict(
                transaction_type=instance.transaction_type,
                builtin=False,
                custom_category=instance,
            )
        )
    else:
        Choice.objects.update_or_create(
            custom_category=instance,
            defaults=dict(
                name=instance.name,
                transaction_type=instance.transaction_type,
            )
        )


@receiver(post_delete, sender=CustomCategory)
def cleanup_custom_category_choice(sender, instance, **kwargs):
    Choice.objects.filter(custom_category=instance).delete()


@receiver(post_save, sender=FinancialRecord)
def refresh_snapshot_on_record_save(sender, instance, **kwargs):
    """Keep the monthly snapshot cache in sync when a record is created or edited.

    The analytics endpoint serves snapshot data first, so every mutation of a
    financial record (including category/type edits confirmed during statement
    review) must recompute its month snapshot — for that record's owner only.
    """
    if instance.owner_id is None:
        return  # Legacy row with no owner: nothing to recompute for.
    compute_monthly_snapshot(instance.date, instance.owner)


@receiver(post_delete, sender=FinancialRecord)
def refresh_snapshot_on_record_delete(sender, instance, **kwargs):
    if instance.owner_id is None:
        return
    compute_monthly_snapshot(instance.date, instance.owner)
