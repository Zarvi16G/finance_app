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
import { ASSET_TYPES, LIQUID_BY_DEFAULT, assetsApi } from '../../api/patrimony';
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
    if (!draft.name.trim()) return setError('Ponle un nombre al activo.');
    const value = Number(draft.current_value);
    if (!Number.isFinite(value) || value < 0) {
      return setError('El valor debe ser un número igual o mayor que cero.');
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
            {asset ? 'Editar activo' : 'Añadir activo'}
          </DialogTitle>
          <DialogDescription>
            Guarda el valor en la moneda en que realmente está. La conversión a {baseCurrency} se
            calcula al leerlo, nunca se escribe encima del monto original.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div>
            <Label htmlFor="a-name">Nombre</Label>
            <Input
              id="a-name"
              className="mt-2"
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              placeholder="Apartamento, Ahorros Bancolombia…"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="a-type">Tipo</Label>
              <Select value={draft.asset_type} onValueChange={setType}>
                <SelectTrigger id="a-type" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ASSET_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="a-currency">Moneda</Label>
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
              <Label htmlFor="a-value">Valor actual</Label>
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
              <Label htmlFor="a-valued">Valorado el</Label>
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
                <span className="text-sm font-semibold">Es líquido</span>
                <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
                  Puedes convertirlo en efectivo en días. Solo los activos líquidos cuentan para el
                  fondo de emergencia. Un CDT a cinco años es ahorro, pero no es líquido.
                </span>
              </span>
            </label>
          </div>

          <div>
            <Label htmlFor="a-notes">Notas</Label>
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
            Cancelar
          </Button>
          <Button onClick={submit} disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
