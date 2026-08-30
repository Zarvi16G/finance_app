"""Data migration: assign an owner to every pre-existing ownerless row.

Phase 0 (multi-tenancy) step 2 of 3. Migration 0017 added a nullable ``owner``
FK to the financial-data models; this migration backfills it so that 0019 can
safely flip the column to ``NOT NULL``.

Every ownerless row is assigned to a single "legacy" user - the first
superuser, or failing that the first user by id. On a database with no users
there is nothing to own, so the migration is a no-op (a fresh install hits this
path and later rows are created already-owned by the API).
"""
from django.db import migrations

OWNED_MODELS = [
    "FinancialRecord",
    "Debt",
    "ExpectedGoal",
    "BankStatement",
    "FinancialSnapshot",
]


def _legacy_user(apps):
    User = apps.get_model("auth", "User")
    return (
        User.objects.filter(is_superuser=True).order_by("id").first()
        or User.objects.order_by("id").first()
    )


def backfill_owner(apps, schema_editor):
    user = _legacy_user(apps)
    if user is None:
        return
    for model_name in OWNED_MODELS:
        model = apps.get_model("finance_api", model_name)
        model.objects.filter(owner__isnull=True).update(owner_id=user.id)


def clear_owner(apps, schema_editor):
    for model_name in OWNED_MODELS:
        model = apps.get_model("finance_api", model_name)
        model.objects.update(owner=None)


class Migration(migrations.Migration):

    dependencies = [
        ("finance_api", "0017_add_owner_fields"),
    ]

    operations = [
        migrations.RunPython(backfill_owner, clear_owner),
    ]
