"""Detect and backfill statement_type/bank_name on existing bank statements."""
import pdfplumber

from django.core.management.base import BaseCommand

from finance_api.models import BankStatement
from finance_api.services.statement_detection import detect_statement_info


class Command(BaseCommand):
    help = 'Detect statement type and bank name from stored PDFs (skips non-other types by default)'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Re-detect every statement, not only type="other"')
        parser.add_argument('--dry-run', action='store_true', help='Print what would change without saving')

    def handle(self, *args, **options):
        queryset = BankStatement.objects.all() if options['all'] else BankStatement.objects.filter(statement_type='other')
        updated = 0
        for statement in queryset:
            try:
                kwargs = {'password': statement.password} if statement.password else {}
                with pdfplumber.open(statement.file.path, **kwargs) as pdf:
                    text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
            except Exception as exc:
                self.stderr.write(f'{statement.original_filename}: skipped ({exc})')
                continue

            detected = detect_statement_info(text)
            changes = []
            if not options['all'] and statement.statement_type == 'other' and detected['statement_type'] != 'other':
                changes.append(('statement_type', statement.statement_type, detected['statement_type']))
            if options['all'] and detected['statement_type'] != statement.statement_type:
                changes.append(('statement_type', statement.statement_type, detected['statement_type']))
            if detected['bank_name'] and detected['bank_name'] != statement.bank_name:
                changes.append(('bank_name', statement.bank_name, detected['bank_name']))

            if not changes:
                continue

            if options['dry_run']:
                for field, old, new in changes:
                    self.stdout.write(f'{statement.original_filename}: {field} {old!r} -> {new!r} (dry-run)')
            else:
                for field, _old, new in changes:
                    setattr(statement, field, new)
                statement.save(update_fields=[field for field, *_ in changes])
                self.stdout.write(f'{statement.original_filename}: updated')
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'Done. {updated} statement(s) changed.'))