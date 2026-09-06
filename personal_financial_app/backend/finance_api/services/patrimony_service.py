"""Net worth: what you own minus what you owe.

Assets and debts are each stored in their own currency, so every figure here
is converted to the reader's base currency before anything is added. The
split between liquid and illiquid assets is kept because it answers a
different question than the total does: a house is wealth, but it will not
cover next month's rent.

Nothing is added across currencies: sums are `Total` objects, which refuse
it. When a rate is missing the affected amount is excluded and reported in
`conversion`, so the reader knows the figure is partial instead of being
handed a peso total with dollars folded into it.
"""
from ..models import Asset, Debt
from . import currency_service
from .currency_service import Total


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

    assets_by_type = _assets_by_type(assets, base)
    liabilities_by_type = _liabilities_by_type(debts, base)

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
            round(float(total_liabilities / total_assets) * 100, 2)
            if total_assets > 0 else None
        ),
        'assets_by_type': [row for row, _ in assets_by_type],
        'liabilities_by_type': [row for row, _ in liabilities_by_type],
        'asset_count': assets.count(),
        'liability_count': debts.count(),
        'conversion': currency_service.conversion_report(
            total_assets, liquid_assets, total_liabilities,
            *(total for _, total in assets_by_type),
            *(total for _, total in liabilities_by_type),
        ),
    }


def net_worth_for(user, base: str) -> tuple[Total, Total, Total]:
    """(total_assets, total_liabilities, net_worth) in `base`.

    The narrow version used by the monthly snapshot, which does not need the
    breakdowns. Returns Totals rather than Decimals so a caller cannot lose
    track of which currency the numbers are in, or of what was excluded.
    """
    assets = Asset.objects.filter(owner=user)
    debts = Debt.objects.filter(owner=user).exclude(status='paid_off')
    total_assets = currency_service.sum_in(assets, base, field='current_value')
    total_liabilities = currency_service.sum_in(debts, base, field='current_balance')
    return total_assets, total_liabilities, total_assets - total_liabilities


def _assets_by_type(assets, base: str) -> list[tuple[dict, Total]]:
    rows = []
    for value in dict.fromkeys(assets.values_list('asset_type', flat=True)):
        group = assets.filter(asset_type=value)
        total = currency_service.sum_in(group, base, field='current_value')
        rows.append((
            {'type': value, 'total': float(total), 'count': group.count()},
            total,
        ))
    return sorted(rows, key=lambda pair: -pair[0]['total'])


def _liabilities_by_type(debts, base: str) -> list[tuple[dict, Total]]:
    rows = []
    for value in dict.fromkeys(debts.values_list('debt_type', flat=True)):
        group = debts.filter(debt_type=value)
        total = currency_service.sum_in(group, base, field='current_balance')
        rows.append((
            {'type': value, 'total': float(total), 'count': group.count()},
            total,
        ))
    return sorted(rows, key=lambda pair: -pair[0]['total'])
