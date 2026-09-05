"""Net worth: what you own minus what you owe.

Assets and debts are each stored in their own currency, so every figure here
is converted to the reader's base currency before anything is added. The
split between liquid and illiquid assets is kept because it answers a
different question than the total does: a house is wealth, but it will not
cover next month's rent.
"""
from decimal import Decimal

from ..models import Asset, Debt
from . import currency_service


def summary_for(user, base: str) -> dict:
    """Full patrimony picture for one user, expressed in `base`."""
    assets = Asset.objects.filter(owner=user)
    debts = Debt.objects.filter(owner=user).exclude(status='paid_off')

    total_assets = currency_service.sum_in(assets, base, field='current_value')
    liquid_assets = currency_service.sum_in(
        assets.filter(is_liquid=True), base, field='current_value'
    )
    total_liabilities = currency_service.sum_in(
        debts, base, field='current_balance'
    )
    net_worth = total_assets - total_liabilities

    return {
        'base_currency': base,
        'total_assets': float(total_assets),
        'liquid_assets': float(liquid_assets),
        'illiquid_assets': float(total_assets - liquid_assets),
        'total_liabilities': float(total_liabilities),
        'net_worth': float(net_worth),
        # Share of what you own that is financed. Above 100% means the debts
        # outweigh the assets — negative net worth.
        'debt_to_asset': (
            round(float(total_liabilities / total_assets * 100), 2)
            if total_assets > 0 else None
        ),
        'assets_by_type': _assets_by_type(assets, base),
        'liabilities_by_type': _liabilities_by_type(debts, base),
        'asset_count': assets.count(),
        'liability_count': debts.count(),
    }


def net_worth_for(user, base: str) -> tuple[Decimal, Decimal, Decimal]:
    """(total_assets, total_liabilities, net_worth) in `base`.

    The narrow version used by the monthly snapshot, which does not need the
    breakdowns.
    """
    assets = Asset.objects.filter(owner=user)
    debts = Debt.objects.filter(owner=user).exclude(status='paid_off')
    total_assets = currency_service.sum_in(assets, base, field='current_value')
    total_liabilities = currency_service.sum_in(debts, base, field='current_balance')
    return total_assets, total_liabilities, total_assets - total_liabilities


def _assets_by_type(assets, base: str) -> list[dict]:
    rows = []
    for value in dict.fromkeys(assets.values_list('asset_type', flat=True)):
        group = assets.filter(asset_type=value)
        rows.append({
            'type': value,
            'total': float(currency_service.sum_in(group, base, field='current_value')),
            'count': group.count(),
        })
    return sorted(rows, key=lambda row: -row['total'])


def _liabilities_by_type(debts, base: str) -> list[dict]:
    rows = []
    for value in dict.fromkeys(debts.values_list('debt_type', flat=True)):
        group = debts.filter(debt_type=value)
        rows.append({
            'type': value,
            'total': float(currency_service.sum_in(group, base, field='current_balance')),
            'count': group.count(),
        })
    return sorted(rows, key=lambda row: -row['total'])
