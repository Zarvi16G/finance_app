/**
 * Patrimonio — the asset register and the net-worth equation.
 *
 * Two decisions carried over from the design, both of them substantive:
 *
 *  - Net worth is written as an equation (assets − liabilities = net worth)
 *    rather than as a lone total, because the total alone hides which side
 *    moved.
 *  - Liquid and illiquid assets are separated as a first-class split. A house
 *    is wealth but will not pay next month's rent, and the emergency-fund
 *    metric on the Wealthness screen depends on exactly this distinction.
 *
 * Liabilities are read-only here: they are debts, and they are edited on the
 * Deudas screen where their payment schedule lives.
 */
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Icon } from '@iconify/react';
import PageHeader from '../shared/PageHeader';
import BaseCurrencyBadge from '../shared/BaseCurrencyBadge';
import ConversionNotice from '../shared/ConversionNotice';
import { Button } from '../ui/button';
import AssetForm from './AssetForm';
import { assetsApi, assetTypeLabel, patrimonyApi } from '../../api/patrimony';
import { debtStatusLabel, debtTypeLabel, debtsApi } from '../../api/debts';
import { getErrorMessage } from '../../api/client';
import { fmtFigure, fmtPercent, fmtDate } from '../../lib/money';
import type { Asset, Debt, PatrimonySummary } from '../../types';

/** Column template shared by the header row and every register row. */
const COLS = 'grid grid-cols-[1.6fr_1fr_0.9fr_1fr_90px] items-center gap-5';

export default function Patrimony() {
  const { t } = useTranslation();
  const [summary, setSummary] = useState<PatrimonySummary | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [debts, setDebts] = useState<Debt[]>([]);
  const [editing, setEditing] = useState<Asset | 'new' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [summaryData, assetList, debtList] = await Promise.all([
        patrimonyApi.summary(),
        assetsApi.list(),
        debtsApi.list(),
      ]);
      setSummary(summaryData);
      setAssets(assetList);
      setDebts(debtList.filter((d) => d.status !== 'paid_off'));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (asset: Asset) => {
    if (!window.confirm(t('patrimony.confirmDelete', { name: asset.name }))) return;
    try {
      await assetsApi.remove(asset.id);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  if (loading) return <p className="text-sm text-muted-foreground">{t('patrimony.loading')}</p>;
  if (!summary) {
    return <p className="border border-error/40 bg-lighterror p-4 text-sm text-error">{error}</p>;
  }

  const base = summary.base_currency;
  const liquidShare =
    summary.total_assets > 0 ? (summary.liquid_assets / summary.total_assets) * 100 : 0;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow={t('patrimony.eyebrow')}
        title={t('patrimony.title')}
        actions={
          <>
            <BaseCurrencyBadge currency={base} />
            <Button onClick={() => setEditing('new')}>{t('patrimony.addAsset')}</Button>
          </>
        }
      />

      {error && (
        <p className="border border-error/40 bg-lighterror p-3 text-sm text-error">{error}</p>
      )}

      <ConversionNotice report={summary.conversion} baseCurrency={base} />

      {/* The balance, stated as an equation */}
      <div className="flex flex-wrap items-center gap-10 border-y rule-strong border-b-border py-6">
        <div>
          <div className="eyebrow-sm mb-2.5">{t('patrimony.assets')}</div>
          <div className="fig text-[32px] font-medium text-success">
            {fmtFigure(summary.total_assets, base)}
          </div>
        </div>
        <div className="fig text-[28px] text-secondary">−</div>
        <div>
          <div className="eyebrow-sm mb-2.5">{t('patrimony.liabilities')}</div>
          <div className="fig text-[32px] font-medium text-error">
            {fmtFigure(summary.total_liabilities, base)}
          </div>
        </div>
        <div className="fig text-[28px] text-secondary">=</div>
        <div>
          <div className="eyebrow-sm mb-2.5">{t('patrimony.netWorth')}</div>
          <div className="fig text-[40px] font-medium leading-none">
            {fmtFigure(summary.net_worth, base)}
          </div>
        </div>
        <div className="ml-auto text-right">
          <div className="eyebrow-sm mb-2.5">{t('patrimony.debtToAsset')}</div>
          <div className="fig text-2xl font-medium">
            {summary.debt_to_asset === null ? (
              <span className="text-secondary">{t('common.notDetermined')}</span>
            ) : (
              fmtPercent(summary.debt_to_asset, 2)
            )}
          </div>
          {summary.debt_to_asset === null && (
            <div className="mt-1.5 text-xs text-muted-foreground">
              {t('patrimony.noAssetsRatio')}
            </div>
          )}
        </div>
      </div>

      {/* Liquid vs illiquid */}
      {summary.total_assets > 0 && (
        <div>
          <div className="mb-3.5 flex flex-wrap items-baseline justify-between gap-3">
            <div className="fig text-[19px] font-medium">{t('patrimony.liquidVsIlliquid')}</div>
            <span className="text-[13px] text-muted-foreground">
              {t('patrimony.liquidNote')}
            </span>
          </div>
          <div className="flex h-11 border rule-strong">
            <div className="bg-primary" style={{ width: `${liquidShare}%` }} />
            <div className="flex-grow bg-muted" />
          </div>
          <div className="mt-2.5 flex flex-wrap justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="h-3 w-3 bg-primary" />
              <span className="text-[13px]">{t('patrimony.liquid')}</span>
              <span className="fig text-sm font-medium">
                {fmtFigure(summary.liquid_assets, base)}
              </span>
              <span className="text-xs text-muted-foreground">{fmtPercent(liquidShare)}</span>
            </div>
            <div className="flex items-center gap-2.5">
              <span className="h-3 w-3 border border-input bg-muted" />
              <span className="text-[13px]">{t('patrimony.illiquid')}</span>
              <span className="fig text-sm font-medium">
                {fmtFigure(summary.illiquid_assets, base)}
              </span>
              <span className="text-xs text-muted-foreground">{fmtPercent(100 - liquidShare)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Asset register */}
      <div>
        <div className="fig mb-1 text-[19px] font-medium">{t('patrimony.assets')}</div>
        {assets.length === 0 ? (
          <p className="border border-input bg-card p-6 text-sm text-inksoft">
{t('patrimony.noAssets')}
          </p>
        ) : (
          <>
            <div className={`${COLS} border-b rule-strong py-3`}>
              <span className="eyebrow-sm">{t('patrimony.name')}</span>
              <span className="eyebrow-sm">{t('patrimony.type')}</span>
              <span className="eyebrow-sm">{t('patrimony.liquidity')}</span>
              <span className="eyebrow-sm text-right">{t('patrimony.value')}</span>
              <span />
            </div>
            {assets.map((asset) => (
              <div key={asset.id} className={`${COLS} border-b border-border py-4`}>
                <div className="min-w-0">
                  <div className="truncate text-[15px]">{asset.name}</div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {asset.valued_at
                      ? t('patrimony.valuedOn', { date: fmtDate(asset.valued_at) })
                      : t('patrimony.noValuationDate')}
                  </div>
                </div>
                <span className="text-sm text-inksoft">{assetTypeLabel(asset.asset_type)}</span>
                <span
                  className={
                    asset.is_liquid
                      ? 'text-xs font-semibold text-primary'
                      : 'text-xs text-muted-foreground'
                  }
                >
                  {t(asset.is_liquid ? 'patrimony.liquid' : 'patrimony.illiquid')}
                </span>
                {/* Each asset is listed in the currency it is actually held
                    in, so a column of values can legitimately mix currencies.
                    The code is printed on any row that is not in the base
                    currency — without it, a figure in dollars sitting under a
                    column of pesos reads as pesos. The totals above are the
                    converted ones. */}
                <span className="fig text-right text-[17px]">
                  {fmtFigure(asset.current_value, asset.currency)}
                  {asset.currency !== base && (
                    <span className="ml-1.5 text-xs text-muted-foreground">{asset.currency}</span>
                  )}
                </span>
                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setEditing(asset)}
                    aria-label={`${t('common.edit')} ${asset.name}`}
                    className="text-muted-foreground transition-colors hover:text-foreground"
                  >
                    <Icon icon="solar:pen-linear" height={16} width={16} />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(asset)}
                    aria-label={`${t('common.delete')} ${asset.name}`}
                    className="text-muted-foreground transition-colors hover:text-error"
                  >
                    <Icon icon="solar:trash-bin-minimalistic-linear" height={16} width={16} />
                  </button>
                </div>
              </div>
            ))}
          </>
        )}

        {/* Liabilities: the other side, read-only */}
        <div className="fig mb-1 mt-7 text-[19px] font-medium">{t('patrimony.liabilities')}</div>
        {debts.length === 0 ? (
          <p className="border-t rule-strong pt-4 text-sm text-inksoft">
            {t('patrimony.noDebts')}
          </p>
        ) : (
          debts.map((debt, index) => (
            <div
              key={debt.id}
              className={`${COLS} border-b border-border py-4 ${
                index === 0 ? 'border-t rule-strong' : ''
              }`}
            >
              <div className="min-w-0">
                <div className="truncate text-[15px]">{debt.name}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {t('patrimony.debtDetail', {
                    creditor: debt.creditor || t('patrimony.noCreditor'),
                    rate: fmtPercent(Number(debt.interest_rate), 2),
                    payment: fmtFigure(debt.minimum_payment, base),
                  })}
                </div>
              </div>
              <span className="text-sm text-inksoft">
                {debtTypeLabel(debt.debt_type, debt.debt_type_display)}
              </span>
              <span className="text-xs text-muted-foreground">
                {debtStatusLabel(debt.status, debt.status_display)}
              </span>
              <span className="fig text-right text-[17px] text-error">
                {fmtFigure(debt.current_balance, debt.currency ?? base)}
                {debt.currency && debt.currency !== base && (
                  <span className="ml-1.5 text-xs text-muted-foreground">{debt.currency}</span>
                )}
              </span>
              <div className="flex justify-end">
                <Link
                  to={`/deudas/${debt.id}`}
                  aria-label={debt.name}
                  className="text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Icon icon="solar:arrow-right-linear" height={16} width={16} />
                </Link>
              </div>
            </div>
          ))
        )}
      </div>

      {editing && (
        <AssetForm
          asset={editing === 'new' ? null : editing}
          baseCurrency={base}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await load();
          }}
        />
      )}
    </div>
  );
}
