"""Data migration: assign an owner to pre-existing config/vocabulary rows.

Phase 0b step 2. Migration 0021 added a nullable ``owner`` to ``UserSetting``,
``CustomType``, ``CustomCategory``, ``Choice`` and ``CategorizationMemory``;
this migration backfills them.

* ``UserSetting`` was a single global row (``pk=1``) - it becomes the legacy
  user's row; any accidental extra rows are dropped so 0023 can add the
  OneToOne ``NOT NULL`` constraint.
* ``CustomType`` / ``CustomCategory`` / ``CategorizationMemory`` rows are all
  user-created -> legacy user.
* ``Choice`` rows: ``builtin=True`` stay ``owner=NULL`` (shared catalog);
  custom ones inherit the owner of their linked type/category, else legacy user.

"Legacy user" = first superuser, or first user by id. No users -> no-op.
"""
from django.db import migrations


def _legacy_user(apps):
    User = apps.get_model("auth", "User")
    return (
        User.objects.filter(is_superuser=True).order_by("id").first()
        or User.objects.order_by("id").first()
    )


def backfill(apps, schema_editor):
    user = _legacy_user(apps)
    if user is None:
        return

    UserSetting = apps.get_model("finance_api", "UserSetting")
    CustomType = apps.get_model("finance_api", "CustomType")
    CustomCategory = apps.get_model("finance_api", "CustomCategory")
    Choice = apps.get_model("finance_api", "Choice")
    CategorizationMemory = apps.get_model("finance_api", "CategorizationMemory")

    # UserSetting: keep the first row for the legacy user, drop any extras.
    settings_qs = list(UserSetting.objects.order_by("id"))
    for extra in settings_qs[1:]:
        extra.delete()
    if settings_qs:
        UserSetting.objects.filter(pk=settings_qs[0].pk).update(owner_id=user.id)

    CustomType.objects.filter(owner__isnull=True).update(owner_id=user.id)
    CustomCategory.objects.filter(owner__isnull=True).update(owner_id=user.id)
    CategorizationMemory.objects.filter(owner__isnull=True).update(owner_id=user.id)

    # Choice: built-ins stay global; custom rows follow their linked object.
    for choice in Choice.objects.filter(builtin=False, owner__isnull=True).select_related(
        "custom_type", "custom_category"
    ):
        linked = choice.custom_type or choice.custom_category
        choice.owner_id = getattr(linked, "owner_id", None) or user.id
        choice.save(update_fields=["owner"])


def clear(apps, schema_editor):
    for model_name in ("UserSetting", "CustomType", "CustomCategory", "Choice", "CategorizationMemory"):
        apps.get_model("finance_api", model_name).objects.update(owner=None)


class Migration(migrations.Migration):

    dependencies = [
        ("finance_api", "0021_phase0b_owner_fields"),
    ]

    operations = [
        migrations.RunPython(backfill, clear),
    ]
