"""Schema half of the multi-tenancy fix.

Adds the `owner` foreign key to every user-owned model and re-scopes the
uniqueness rules that were previously global (statement content hash,
snapshot month, vocabulary names, learned categorization patterns).

The column is nullable here on purpose: existing rows have no owner yet.
The follow-up data migration (0014) backfills them.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance_api", "0012_usersetting_ai_keys_usersetting_ai_model_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="categorizationmemory",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="choice",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="bankstatement",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this statement belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bank_statements",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="categorizationmemory",
            name="owner",
            field=models.ForeignKey(
                help_text="The user whose confirmations produced this pattern",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="categorization_memories",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="choice",
            name="owner",
            field=models.ForeignKey(
                help_text="Owner of this choice; null means seeded/built-in and shared",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="choices",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="customcategory",
            name="owner",
            field=models.ForeignKey(
                help_text="Owner of this custom category; null means seeded/global",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="custom_categories",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="customtype",
            name="owner",
            field=models.ForeignKey(
                help_text="Owner of this custom type; null means seeded/global",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="custom_types",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="debt",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this debt belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="debts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="expectedgoal",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this goal belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="goals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="financialrecord",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this record belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="financial_records",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="financialsnapshot",
            name="owner",
            field=models.ForeignKey(
                help_text="The user this snapshot summarizes",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="snapshots",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="usersetting",
            name="owner",
            field=models.OneToOneField(
                help_text="The user these settings belong to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="setting",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="bankstatement",
            name="content_hash",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="SHA256 hash of file content for duplicate detection",
                max_length=64,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="customcategory",
            name="name",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="customtype",
            name="name",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="financialsnapshot",
            name="date",
            field=models.DateField(),
        ),
        migrations.AlterUniqueTogether(
            name="categorizationmemory",
            unique_together={("owner", "pattern", "category", "transaction_type")},
        ),
        migrations.AddConstraint(
            model_name="bankstatement",
            constraint=models.UniqueConstraint(
                fields=("owner", "content_hash"),
                name="uniq_statement_owner_content_hash",
            ),
        ),
        migrations.AddConstraint(
            model_name="choice",
            constraint=models.UniqueConstraint(
                fields=("owner", "name", "choice_type"),
                name="uniq_choice_owner_name_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="customcategory",
            constraint=models.UniqueConstraint(
                fields=("owner", "name"), name="uniq_customcategory_owner_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="customtype",
            constraint=models.UniqueConstraint(
                fields=("owner", "name"), name="uniq_customtype_owner_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="financialsnapshot",
            constraint=models.UniqueConstraint(
                fields=("owner", "date"), name="uniq_snapshot_owner_date"
            ),
        ),
    ]
