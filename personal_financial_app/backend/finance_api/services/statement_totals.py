"""Statement totals: aggregate income/expense/net in USD from extracted transactions.

Uses per-statement totals_updated_at timestamp for staleness tracking.
If stored usd_amount values are older than MAX_AGE_HOURS, they are
refreshed using live CurrencyRate data and persisted.
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from ..models.statements import BankStatement, ExtractedTransaction
from .currency import get_rate_map

MAX_AGE_HOURS = 20


def is_totals_stale(statement: BankStatement) -> bool:
    """Return True if totals need refreshing."""
    if statement.totals_updated_at is None:
        return True
    return (timezone.now() - statement.totals_updated_at) > timedelta(hours=MAX_AGE_HOURS)


def refresh_usd_amounts(statement: BankStatement) -> None:
    """Recompute usd_amount on every extracted transaction using live rates."""
    rate_map = get_rate_map()
    usd_rate = float(rate_map.get('USD', Decimal('1.0')))
    now = timezone.now()

    txns = list(statement.extracted_transactions.all())
    to_update = []
    for txn in txns:
        cur = (txn.currency or 'USD').upper()
        if cur == 'USD':
            new_usd = txn.amount
        else:
            rate_to_cop = float(rate_map.get(cur, Decimal('0')))
            if rate_to_cop > 0 and usd_rate > 0:
                new_usd = txn.amount * Decimal(str(rate_to_cop / usd_rate))
            else:
                new_usd = Decimal('0')
        if txn.usd_amount != new_usd:
            txn.usd_amount = new_usd
            to_update.append(txn)

    if to_update:
        ExtractedTransaction.objects.bulk_update(to_update, ['usd_amount'])

    statement.totals_updated_at = now
    statement.save(update_fields=['totals_updated_at'])


def get_statement_totals(statement: BankStatement, force_refresh: bool = False) -> dict:
    """Return aggregated totals for a statement.

    Returns dict with keys:
        total_income_usd, total_expense_usd, net_usd, totals_stale
    """
    if force_refresh or is_totals_stale(statement):
        refresh_usd_amounts(statement)

    txns = statement.extracted_transactions.all()
    income = Decimal('0')
    expense = Decimal('0')
    for txn in txns:
        amt = Decimal(str(txn.usd_amount or 0))
        if txn.transaction_type == 'income':
            income += amt
        elif txn.transaction_type == 'expense':
            expense += amt

    return {
        'total_income_usd': float(income),
        'total_expense_usd': float(expense),
        'net_usd': float(income - expense),
        'totals_stale': is_totals_stale(statement),
    }


def get_all_statements_totals(statements, force_refresh: bool = False) -> dict:
    """Batch compute totals for a list of statements.

    Returns dict mapping statement.id -> totals dict.
    """
    result = {}
    for stmt in statements:
        result[str(stmt.id)] = get_statement_totals(stmt, force_refresh=force_refresh)
    return result
