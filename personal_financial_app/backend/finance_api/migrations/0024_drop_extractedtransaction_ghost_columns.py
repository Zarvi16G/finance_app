"""Drop the two ghost columns left behind on extractedtransaction.

`usd_amount` and `currency` were created by 0015_extractedtransaction_usd_amount_and_more,
part of the migration history that was replaced when the owner-scoping branch
was merged. That file no longer exists, but its row stays in django_migrations
and the columns stayed in the table: NOT NULL, no default, and unknown to any
model in the codebase.

Every INSERT Django builds lists only the model's columns, so SQLite fills
these with NULL and rejects the row:

    NOT NULL constraint failed: finance_api_extractedtransaction.usd_amount

which crashed every statement upload at services/statement_parser.py:37, right
after the PDF had parsed successfully.

This is a database-only correction. The migration state never knew these
fields, so there is nothing to remove from it — a plain RemoveField would raise
FieldDoesNotExist while building state. RunSQL brings the table back in line
with the state, which is the direction the drift actually runs.

Reversing is a no-op on purpose: the columns carry no data any part of the
application reads, and re-adding them NOT NULL without a default would fail on
a populated table anyway.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("finance_api", "0023_merge_20260906_2207"),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE "finance_api_extractedtransaction" DROP COLUMN "usd_amount";',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql='ALTER TABLE "finance_api_extractedtransaction" DROP COLUMN "currency";',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
