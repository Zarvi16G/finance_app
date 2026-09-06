/**
 * Create or edit one line of an experience budget.
 *
 * `goal` is sent on every write and is the field that carries ownership: the
 * backend narrows its queryset to the caller's own goals, so a line can never
 * be attached to somebody else's trip. It is not editable here — a line
 * belongs to the trip it was created under.
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
import { BUDGET_CATEGORIES, budgetCategoryLabel, budgetItemsApi } from '../../api/experiences';
import { currencyApi } from '../../api/currency';
import { getErrorMessage } from '../../api/client';
import type { Currency, ExperienceBudgetItem } from '../../types';

export default function BudgetItemForm({
  item,
  goalId,
  goalTitle,
  baseCurrency,
  onClose,
  onSaved,
}: {
  item: ExperienceBudgetItem | null;
  goalId: number;
  goalTitle: string;
  baseCurrency: string;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  const { t } = useTranslation();
  const [label, setLabel] = useState(item?.label ?? '');
  const [category, setCategory] = useState(item?.category ?? 'other');
  const [estimated, setEstimated] = useState(String(item?.estimated_amount ?? ''));
  const [actual, setActual] = useState(
    item?.actual_amount === null || item?.actual_amount === undefined
      ? ''
      : String(item.actual_amount),
  );
  const [currency, setCurrency] = useState(item?.currency ?? baseCurrency);
  const [isBooked, setIsBooked] = useState(item?.is_booked ?? false);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    currencyApi
      .catalog()
      .then((c) => setCurrencies(c.currencies))
      .catch(() => setCurrencies([]));
  }, []);

  const submit = async () => {
    setError(null);
    if (!label.trim()) return setError(t('budgetForm.errorLabel'));
    const value = Number(estimated);
    if (!Number.isFinite(value) || value < 0) {
      return setError(t('budgetForm.errorEstimated'));
    }

    setSaving(true);
    try {
      const payload = {
        goal: goalId,
        label: label.trim(),
        category,
        estimated_amount: estimated,
        // An empty field means "not spent yet", which is null — not zero.
        actual_amount: actual.trim() === '' ? null : actual,
        currency,
        is_booked: isBooked,
      };
      if (item) await budgetItemsApi.update(item.id, payload);
      else await budgetItemsApi.create(payload);
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
            {t(item ? 'budgetForm.editTitle' : 'budgetForm.addTitle')}
          </DialogTitle>
          <DialogDescription>
{t('budgetForm.description', { goal: goalTitle, base: baseCurrency })}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div>
            <Label htmlFor="b-label">{t('budgetForm.label')}</Label>
            <Input
              id="b-label"
              className="mt-2"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder={t('budgetForm.labelPlaceholder')}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="b-category">{t('budgetForm.category')}</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger id="b-category" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BUDGET_CATEGORIES.map((value) => (
                    <SelectItem key={value} value={value}>
                      {budgetCategoryLabel(value)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="b-currency">{t('budgetForm.currency')}</Label>
              <Select value={currency} onValueChange={setCurrency}>
                <SelectTrigger id="b-currency" className="mt-2">
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
              <Label htmlFor="b-estimated">{t('budgetForm.estimated')}</Label>
              <Input
                id="b-estimated"
                className="mt-2"
                type="number"
                min="0"
                step="0.01"
                value={estimated}
                onChange={(e) => setEstimated(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="b-actual">{t('budgetForm.actual')}</Label>
              <Input
                id="b-actual"
                className="mt-2"
                type="number"
                min="0"
                step="0.01"
                value={actual}
                onChange={(e) => setActual(e.target.value)}
                placeholder={t('budgetForm.actualPlaceholder')}
              />
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
{t('budgetForm.actualNote')}
              </p>
            </div>
          </div>

          <label className="flex cursor-pointer items-start gap-3 border border-input p-4">
            <input
              type="checkbox"
              className="mt-1"
              checked={isBooked}
              onChange={(e) => setIsBooked(e.target.checked)}
            />
            <span>
              <span className="text-sm font-semibold">{t('budgetForm.booked')}</span>
              <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
{t('budgetForm.bookedNote')}
              </span>
            </span>
          </label>

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
