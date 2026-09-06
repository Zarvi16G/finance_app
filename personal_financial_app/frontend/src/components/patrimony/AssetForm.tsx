/**
 * Create or edit one asset.
 *
 * The liquidity field is the interesting one. The backend defaults it from
 * the asset type, but only when the client says nothing — so an explicit
 * "savings account that is not liquid" (a five-year CD) sticks. This form
 * therefore always sends `is_liquid`, and pre-fills it from the type only
 * while the user has not touched it themselves.
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ASSET_TYPES, LIQUID_BY_DEFAULT, assetTypeLabel, assetsApi } from '../../api/patrimony';
import { currencyApi } from '../../api/currency';
import { getErrorMessage } from '../../api/client';
import type { Asset, Currency } from '../../types';

interface Draft {
  name: string;
  asset_type: string;
  current_value: string;
  currency: string;
  is_liquid: boolean;
  valued_at: string;
  acquired_date: string;
  notes: string;
}

const today = () => new Date().toISOString().slice(0, 10);

const emptyDraft = (baseCurrency: string): Draft => ({
  name: '',
  asset_type: 'savings',
  current_value: '',
  currency: baseCurrency,
  is_liquid: true,
  valued_at: today(),
  acquired_date: '',
  notes: '',
});

export default function AssetForm({
  asset,
  baseCurrency,
  onClose,
  onSaved,
}: {
  asset: Asset | null;
  baseCurrency: string;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<Draft>(() =>
    asset
      ? {
          name: asset.name,
          asset_type: asset.asset_type,
          current_value: String(asset.current_value),
          currency: asset.currency,
          is_liquid: asset.is_liquid,
          valued_at: asset.valued_at?.slice(0, 10) ?? today(),
          acquired_date: asset.acquired_date?.slice(0, 10) ?? '',
          notes: asset.notes ?? '',
        }
      : emptyDraft(baseCurrency),
  );
  // Once the user sets liquidity by hand, changing the type must not undo it.
  const [liquidityTouched, setLiquidityTouched] = useState(Boolean(asset));
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    currencyApi
      .catalog()
      .then((c) => setCurrencies(c.currencies))
      .catch(() => setCurrencies([]));
  }, []);

  const setType = (asset_type: string) =>
    setDraft((d) => ({
      ...d,
      asset_type,
      is_liquid: liquidityTouched ? d.is_liquid : LIQUID_BY_DEFAULT.has(asset_type),
    }));

  const submit = async () => {
    setError(null);
    if (!draft.name.trim()) return setError(t('assetForm.errorName'));
    const value = Number(draft.current_value);
    if (!Number.isFinite(value) || value < 0) {
      return setError(t('assetForm.errorValue'));
    }

    setSaving(true);
    try {
      const payload = {
        name: draft.name.trim(),
        asset_type: draft.asset_type,
        current_value: draft.current_value,
        currency: draft.currency,
        is_liquid: draft.is_liquid,
        valued_at: draft.valued_at || null,
        acquired_date: draft.acquired_date || null,
        notes: draft.notes.trim(),
      };
      if (asset) await assetsApi.update(asset.id, payload);
      else await assetsApi.create(payload);
      await onSaved();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="fig text-xl font-medium">
            {t(asset ? 'assetForm.editTitle' : 'assetForm.addTitle')}
          </DialogTitle>
          <DialogDescription>
{t('assetForm.description', { base: baseCurrency })}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div>
            <Label htmlFor="a-name">{t('assetForm.name')}</Label>
            <Input
              id="a-name"
              className="mt-2"
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              placeholder={t('assetForm.namePlaceholder')}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="a-type">{t('assetForm.type')}</Label>
              <Select value={draft.asset_type} onValueChange={setType}>
                <SelectTrigger id="a-type" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ASSET_TYPES.map((value) => (
                    <SelectItem key={value} value={value}>
                      {assetTypeLabel(value)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="a-currency">{t('assetForm.currency')}</Label>
              <Select
                value={draft.currency}
                onValueChange={(currency) => setDraft({ ...draft, currency })}
              >
                <SelectTrigger id="a-currency" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(currencies.length
                    ? currencies
                    : [{ code: baseCurrency, name: baseCurrency, symbol: '', decimals: 2 }]
                  ).map((c) => (
                    <SelectItem key={c.code} value={c.code}>
                      {c.code} · {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="a-value">{t('assetForm.currentValue')}</Label>
              <Input
                id="a-value"
                className="mt-2"
                type="number"
                min="0"
                step="0.01"
                value={draft.current_value}
                onChange={(e) => setDraft({ ...draft, current_value: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="a-valued">{t('assetForm.valuedOn')}</Label>
              <Input
                id="a-valued"
                className="mt-2"
                type="date"
                value={draft.valued_at}
                onChange={(e) => setDraft({ ...draft, valued_at: e.target.value })}
              />
            </div>
          </div>

          <div className="border border-input p-4">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                className="mt-1"
                checked={draft.is_liquid}
                onChange={(e) => {
                  setLiquidityTouched(true);
                  setDraft({ ...draft, is_liquid: e.target.checked });
                }}
              />
              <span>
                <span className="text-sm font-semibold">{t('assetForm.isLiquid')}</span>
                <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
{t('assetForm.isLiquidNote')}
                </span>
              </span>
            </label>
          </div>

          <div>
            <Label htmlFor="a-notes">{t('assetForm.notes')}</Label>
            <Input
              id="a-notes"
              className="mt-2"
              value={draft.notes}
              onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
            />
          </div>

          {error && <p className="text-sm text-error">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            {t('common.cancel')}
          </Button>
          <Button onClick={submit} disabled={saving}>
            {saving ? t('common.saving') : t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
