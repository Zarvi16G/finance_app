"""Data half of the multi-tenancy fix: give existing rows an owner.

Everything created before 0013 was written by a single-tenant app, so the
rows carry no owner. We hand them to the oldest existing account (the person
who was actually using the install) and leave the built-in seeded vocabulary
global.

If the database has no users at all — a fresh clone, or CI — there is nothing
to backfill and every row stays orphaned. Orphans are safe: every queryset
filters on `owner=request.user`, and NULL never matches, so those rows are
simply invisible through the API.
"""

from django.db import migrations

# Rows owned by a person. The seeded Choice/CustomType/CustomCategory catalog
# is deliberately excluded: builtin vocabulary stays shared by everyone.
OWNED_MODELS = [
    'FinancialRecord',
    'ExpectedGoal',
    'Debt',
    'BankStatement',
    'FinancialSnapshot',
    'CategorizationMemory',
]


def backfill_owner(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    first_user = User.objects.order_by('date_joined', 'id').first()
    if first_user is None:
        return

    for model_name in OWNED_MODELS:
        model = apps.get_model('finance_api', model_name)
        model.objects.filter(owner__isnull=True).update(owner=first_user)

    # Custom (non-builtin) vocabulary belonged to that same person.
    Choice = apps.get_model('finance_api', 'Choice')
    Choice.objects.filter(owner__isnull=True, builtin=False).update(owner=first_user)

    for model_name in ('CustomType', 'CustomCategory'):
        model = apps.get_model('finance_api', model_name)
        model.objects.filter(owner__isnull=True).update(owner=first_user)

    # The old global settings row (pk=1) becomes that user's settings row.
    UserSetting = apps.get_model('finance_api', 'UserSetting')
    legacy = UserSetting.objects.filter(owner__isnull=True).order_by('id').first()
    if legacy is not None:
        legacy.owner = first_user
        legacy.save(update_fields=['owner'])
    # Any further ownerless settings rows are duplicates of a singleton that
    # no longer exists; drop them so the OneToOne stays clean.
    UserSetting.objects.filter(owner__isnull=True).delete()


def unbackfill_owner(apps, schema_editor):
    """Reverse: detach owners again so 0013 can be unapplied cleanly."""
    for model_name in OWNED_MODELS + ['Choice', 'CustomType', 'CustomCategory', 'UserSetting']:
        model = apps.get_model('finance_api', model_name)
        model.objects.update(owner=None)


class Migration(migrations.Migration):

    dependencies = [
        ('finance_api', '0013_owner_scoping'),
    ]

    operations = [
        migrations.RunPython(backfill_owner, unbackfill_owner),
    ]
