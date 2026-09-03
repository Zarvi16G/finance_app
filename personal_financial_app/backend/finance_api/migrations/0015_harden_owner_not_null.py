"""Make `owner` mandatory at the database level.

0013/0014 added the column and backfilled it. This closes the loop: the
database itself now refuses a row that belongs to nobody, so a future code
path that forgets to set an owner fails loudly instead of creating a record
invisible to everyone.

Only the six person-owned models plus UserSetting are hardened. The
vocabulary models (Choice, CustomType, CustomCategory) keep a nullable owner
on purpose — there, NULL means "seeded catalog shared by every account".
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

OWNED_MODELS = [
    'FinancialRecord',
    'ExpectedGoal',
    'Debt',
    'BankStatement',
    'FinancialSnapshot',
    'CategorizationMemory',
    'UserSetting',
]


def assign_remaining_orphans(apps, schema_editor):
    """Catch anything 0014 could not reach, and fail clearly if it cannot.

    0014 runs when it runs; a database that had no accounts yet at that
    moment still holds ownerless rows. Rather than let the ALTER blow up with
    a bare IntegrityError, hand them to the oldest account — or explain
    exactly what to do when there is no account to hand them to.
    """
    User = apps.get_model('auth', 'User')
    first_user = User.objects.order_by('date_joined', 'id').first()

    stranded = []
    for model_name in OWNED_MODELS:
        model = apps.get_model('finance_api', model_name)
        orphans = model.objects.filter(owner__isnull=True)
        if not orphans.exists():
            continue
        if first_user is None:
            stranded.append(f'{model_name} ({orphans.count()} row(s))')
        else:
            orphans.update(owner=first_user)

    if stranded:
        raise RuntimeError(
            'Cannot make `owner` mandatory: these rows have no owner and the '
            'database has no user account to assign them to — '
            + ', '.join(stranded) + '. '
            'Create an account (python manage.py createsuperuser), then run '
            'migrate again; the rows will be assigned to it. Delete them '
            'instead if they are throwaway data.'
        )


def noop(apps, schema_editor):
    """Reversing only needs to relax the column, which the AlterFields do."""


class Migration(migrations.Migration):

    dependencies = [
        ("finance_api", "0014_backfill_owner"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(assign_remaining_orphans, noop),
        migrations.AlterField(
            model_name="bankstatement",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this statement belongs to",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bank_statements",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="categorizationmemory",
            name="owner",
            field=models.ForeignKey(
                help_text="The user whose confirmations produced this pattern",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="categorization_memories",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="debt",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this debt belongs to",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="debts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="expectedgoal",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this goal belongs to",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="goals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="financialrecord",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this record belongs to",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="financial_records",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="financialsnapshot",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this snapshot summarizes",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="snapshots",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="usersetting",
            name="owner",
            field=models.OneToOneField(
                help_text="The user these settings belong to",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="setting",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
