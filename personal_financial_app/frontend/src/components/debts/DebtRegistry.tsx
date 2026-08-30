/**
 * Debt registry page: CRUD table with debt summary tiles,
 * per-currency amortization charts, and payoff progress tracking.
 *
 * Multi-currency support:
 * - Each debt carries its own currency code.
 * - The currency selector in the form is populated from the settings
 *   exchange-rate table (base currency COP is always available).
 * - A "Debt by Currency" chart section appears only when 2+ distinct
 *   currencies exist among active debts. Up to 3 currency charts are
 *   shown; the rest can be managed via a modal.
 * - Totals are never naively mixed — they are converted to COP when
 *   currencies differ.
 */
import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useProfileCurrency } from '../../hooks/useProfileCurrency';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import CardBox from '../shared/CardBox';
import PageHeader from '../shared/PageHeader';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { debtsApi, type DebtInput } from '../../api/debts';
import { getErrorMessage } from '../../api/client';
import { fmtMoney } from '../../lib/money';
import type { Debt } from '../../types';
import { Icon } from '@iconify/react';

const DEBT_TYPES = [
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'personal_loan', label: 'Personal Loan' },
  { value: 'mortgage', label: 'Mortgage' },
  { value: 'auto_loan', label: 'Auto Loan' },
  { value: 'student_loan', label: 'Student Loan' },
  { value: 'medical_debt', label: 'Medical Debt' },
  { value: 'other', label: 'Other' },
];

const EMPTY_FORM: DebtInput = {
  name: '',
  debt_type: 'credit_card',
  currency: 'COP',
  creditor: '',
  original_amount: '',
  current_balance: '',
  interest_rate: '',
  minimum_payment: '',
  due_date: 1,
  start_date: '',
  notes: '',
};

const MAX_VISIBLE_CHARTS = 3;

export default function DebtRegistry() {
  const { profileCurrency } = useProfileCurrency();
  const [debts, setDebts] = useState<Debt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Debt | null>(null);
  const [form, setForm] = useState<DebtInput>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [currency, setCurrency] = useState(BASE_CURRENCY);
  const [manageChartsOpen, setManageChartsOpen] = useState(false);
  const [visibleCurrencies, setVisibleCurrencies] = useState<string[]>([]);

  useEffect(() => {
    setCurrency(profileCurrency);
  }, [profileCurrency]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        setDebts(await debtsApi.list());
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    fetchDebts();
  }, []);

  // Available currency options: COP (base) + all currencies from the exchange rate table
  const availableCurrencies = useMemo(() => {
    const codes = new Set([BASE_CURRENCY, ...Object.keys(exchangeRates || {})]);
    return Array.from(codes).sort();
  }, []);

  useEffect(() => {
    if (availableCurrencies.length > 0) {
      setVisibleCurrencies((prev) => {
        const existing = prev.filter((c) => availableCurrencies.includes(c));
        if (existing.length === 0) {
          return availableCurrencies.slice(0, MAX_VISIBLE_CHARTS);
        }
        // Add any new currencies not yet in the list
        const newCurrencies = availableCurrencies.filter((c) => !existing.includes(c));
        return [...existing, ...newCurrencies.slice(0, MAX_VISIBLE_CHARTS - existing.length)];
      });
    }
  }, [availableCurrencies]);

  // Determine which currencies have active debts
  const activeDebtCurrencies = useMemo(() => {
    const currencies = new Set(
      debts.filter((d) => d.status === 'active').map((d) => d.currency || BASE_CURRENCY)
    );
    return currencies;
  }, [debts]);

  // True when there are 2+ distinct currencies among active debts
  const hasMultipleCurrencies = activeDebtCurrencies.size >= 2;

  // Groups debts by currency for the chart
  const debtsByCurrency = useMemo(() => {
    const groups: Record<string, Debt[]> = {};
    for (const debt of debts.filter((d) => d.status === 'active')) {
      const curr = debt.currency || BASE_CURRENCY;
      if (!groups[curr]) groups[curr] = [];
      groups[curr].push(debt);
    }
    return groups;
  }, [debts]);

  // COP-converted totals for summary tiles
  const totalsForCurrency = useCallback(
    (currencyCode: string, field: 'current_balance' | 'minimum_payment' | 'monthly_interest') => {
      const group = debtsByCurrency[currencyCode] || [];
      const nativeTotal = group.reduce((sum, d) => sum + Number(d[field] || 0), 0);
      return convertToBase(nativeTotal, currencyCode, exchangeRates);
    },
    [debtsByCurrency],
  );

  const totalBalanceCop = useMemo(
    () => activeDebtCurrencies.size > 0
      ? Array.from(activeDebtCurrencies).reduce((sum, curr) => sum + totalsForCurrency(curr, 'current_balance'), 0)
      : 0,
    [activeDebtCurrencies, totalsForCurrency],
  );

  const totalMinPaymentCop = useMemo(
    () => activeDebtCurrencies.size > 0
      ? Array.from(activeDebtCurrencies).reduce((sum, curr) => sum + totalsForCurrency(curr, 'minimum_payment'), 0)
      : 0,
    [activeDebtCurrencies, totalsForCurrency],
  );

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, currency: currency });
    setDialogOpen(true);
  };

  const openEdit = (debt: Debt) => {
    setEditing(debt);
    setForm({
      name: debt.name,
      debt_type: debt.debt_type,
      currency: debt.currency || BASE_CURRENCY,
      creditor: debt.creditor,
      original_amount: String(debt.original_amount),
      current_balance: String(debt.current_balance),
      interest_rate: String(debt.interest_rate),
      minimum_payment: String(debt.minimum_payment),
      due_date: debt.due_date,
      start_date: debt.start_date,
      notes: debt.notes ?? '',
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    const payload: DebtInput = {
      ...form,
      original_amount: Number(form.original_amount),
      current_balance: Number(form.current_balance),
      interest_rate: Number(form.interest_rate),
      minimum_payment: Number(form.minimum_payment),
      due_date: Number(form.due_date),
    };
    try {
      if (editing) {
        await debtsApi.update(editing.id, payload);
      } else {
        await debtsApi.create(payload);
      }
      setDialogOpen(false);
      await fetchDebts();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this debt?')) return;
    await debtsApi.remove(id);
    await fetchDebts();
  };

  const handleManageCharts = (selected: string[]) => {
    setVisibleCurrencies(selected);
    setManageChartsOpen(false);
  };

  const cssVar = (name: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#18251c';

  const chartColors = ['--chart-1', '--chart-2', '--chart-3', '--chart-4', '--info'];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Liabilities Ledger"
        title="Debt registry"
        description="Track balances, interest and payments — everything you owe, in one column."
        actions={
          <Button onClick={openCreate}>
            <Icon icon="solar:add-circle-linear" height={18} width={18} />
            Add Debt
          </Button>
        }
      />

      {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

      {/* Summary Cards - USD primary, Profile Currency secondary */}
      <CardBox className="mb-4">
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-foreground">Total Balance</p>
              <p className="font-display text-2xl font-normal">
                {fmtMoney(totalBalanceCop, BASE_CURRENCY)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">
                Total in {profileCurrency}
              </p>
              <p className="font-display text-xl font-bold">
                {fmtMoney(
                  totalBalanceCop,
                  profileCurrency
                )}
              </p>
            </div>
          </div>
        </div>
        <div className="p-4">
          <p className="text-sm text-muted-foreground">
            Primary view: USD {profileCurrency === 'USD' ? '(active)' : ''}
            {profileCurrency !== 'USD' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setProfileCurrency('USD')}
              >
                Switch to USD
              </Button>
            )}
          </p>
        </div>
      </CardBox>

      {!loading && debts.length > 0 && (
        <div className="grid gap-6 md:grid-cols-3">
          <CardBox>
            <div className="p-5">
              <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Total Balance {hasMultipleCurrencies && `(in ${BASE_CURRENCY})`}
              </p>
              <p className="mt-1 font-mono text-2xl font-medium tabular-nums text-foreground">
                {fmtMoney(totalBalanceCop, BASE_CURRENCY)}
              </p>
              {hasMultipleCurrencies && (
                <div className="mt-1 space-y-0.5">
                  {Array.from(activeDebtCurrencies).map((curr) => (
                    <p key={curr} className="font-mono text-[10px] text-muted-foreground">
                      {fmtMoney(
                        (debtsByCurrency[curr] || []).reduce((sum, d) => sum + Number(d.current_balance || 0), 0),
                        curr
                      )}{' '}
                      <span className="opacity-60">({curr})</span>
                    </p>
                  ))}
                </div>
              )}
            </div>
          </CardBox>
          <CardBox>
            <div className="p-5">
              <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Min. Payments / Month {hasMultipleCurrencies && `(in ${BASE_CURRENCY})`}
              </p>
              <p className="mt-1 font-mono text-2xl font-medium tabular-nums text-foreground">
                {fmtMoney(totalMinPaymentCop, BASE_CURRENCY)}
              </p>
            </div>
          </CardBox>
          <CardBox>
            <div className="p-5">
              <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                Active Debts
              </p>
              <p className="mt-1 font-mono text-2xl font-medium tabular-nums text-foreground">
                {debts.filter((d) => d.status === 'active').length}
              </p>
              {hasMultipleCurrencies && (
                <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                  {activeDebtCurrencies.size} currencies
                </p>
              )}
            </div>
          </CardBox>
        </div>
      )}

      {/** Multi-currency debt charts — only when 2+ currencies exist */}
      {hasMultipleCurrencies && (
        <CardBox>
          <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border px-5 py-4">
            <div>
              <h3 className="font-display text-xl font-normal text-foreground">Debt by Currency</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Separate charts per currency — amounts are shown in their native currency, never mixed or converted within a chart.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setManageChartsOpen(true)}
            >
              <Icon icon="solar:settings-2-linear" height={16} width={16} className="mr-1" />
              Manage Charts
            </Button>
          </div>
          <div className="grid gap-6 p-5 md:grid-cols-2 xl:grid-cols-3">
            {visibleCurrencies
              .filter((curr) => curr in debtsByCurrency)
              .map((curr, i) => {
                const group = debtsByCurrency[curr];
                const total = group.reduce((sum, d) => sum + Number(d.current_balance || 0), 0);
                const chartData = group.map((d) => ({
                  name: d.name.length > 16 ? d.name.slice(0, 16) + '…' : d.name,
                  balance: Number(d.current_balance),
                  currency: curr,
                }));
                const color = cssVar(chartColors[i % chartColors.length]);
                return (
                  <div key={curr} className="rounded-sm border border-border p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <Badge variant="outline">{curr}</Badge>
                      <span className="font-mono text-sm font-medium tabular-nums text-foreground">
                        {fmtMoney(total, curr)}
                      </span>
                    </div>
                    <div className="h-56">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 24 }}>
                          <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" />
                          <XAxis
                            dataKey="name"
                            tick={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, fill: 'var(--muted-foreground)' }}
                            interval="preserveEnd"
                            angle={-35}
                            textAnchor="end"
                          />
                          <YAxis
                            tick={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, fill: 'var(--muted-foreground)' }}
                            tickFormatter={(v) => fmtMoneyCompact(v, curr)}
                            width={56}
                          />
                          <Tooltip
                            contentStyle={{
                              background: 'var(--card)',
                              border: '1px solid var(--border)',
                              borderRadius: 2,
                              fontSize: 12,
                              fontFamily: "'IBM Plex Mono', monospace",
                            }}
                            formatter={(value: number, name: string) => [fmtMoney(value, curr), name]}
                          />
                          <Bar dataKey="balance" name="Balance" fill={color} radius={[2, 2, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                );
              })}
            {visibleCurrencies.filter((curr) => curr in debtsByCurrency).length === 0 && (
              <p className="text-sm text-muted-foreground">No active debts in the selected currencies.</p>
            )}
          </div>
        </CardBox>
      )}

      <CardBox className="overflow-hidden">
        {loading ? (
          <div className="h-60 animate-pulse rounded-lg m-5 bg-muted" />
        ) : debts.length === 0 ? (
          <div className="p-10 text-center">
            <Icon
              icon="solar:wallet-money-outline"
              height={48}
              width={48}
              className="mx-auto text-muted-foreground"
            />
            <p className="mt-3 text-muted-foreground">
              No debts tracked. Add your first debt to start a payoff plan.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Currency</TableHead>
                <TableHead className="text-right">Balance</TableHead>
                <TableHead className="text-right">Rate</TableHead>
                <TableHead className="text-right">Min Payment</TableHead>
                <TableHead>Progress</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {debts.map((debt) => (
                <TableRow key={debt.id}>
                  <TableCell>
                    <Link
                      to={`/debts/${debt.id}`}
                      className="font-medium text-foreground hover:underline"
                    >
                      {debt.name}
                    </Link>
                    <p className="text-xs text-muted-foreground">{debt.creditor}</p>
                  </TableCell>
                  <TableCell>{debt.debt_type_display}</TableCell>
                  <TableCell>
                    <Badge variant="gray">{debt.currency || BASE_CURRENCY}</Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono font-semibold tabular-nums text-foreground">
                    {fmtMoney(Number(debt.current_balance), debt.currency || BASE_CURRENCY)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
                    {debt.interest_rate}%
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
                    {fmtMoney(Number(debt.minimum_payment), debt.currency || BASE_CURRENCY)}
                  </TableCell>
                  <TableCell className="min-w-[140px]">
                    <div className="h-2 overflow-hidden rounded-sm bg-muted">
                      <div
                        className="h-full rounded-sm bg-success"
                        style={{ width: `${Math.min(debt.progress_percentage, 100)}%` }}
                      />
                    </div>
                    <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
                      {debt.progress_percentage}% paid
                    </p>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={debt.status === 'active' ? 'primary' : debt.status === 'paid_off' ? 'success' : 'gray'}
                    >
                      {debt.status_display}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(debt)}>
                        <Icon icon="solar:pen-linear" height={16} width={16} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-error hover:text-error"
                        onClick={() => handleDelete(debt.id)}
                      >
                        <Icon icon="solar:trash-bin-trash-linear" height={16} width={16} />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardBox>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Debt' : 'Add Debt'}</DialogTitle>
            <DialogDescription>Track the debt details to compute payoff progress.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="d-name">Name</Label>
                <Input
                  id="d-name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="d-type">Type</Label>
                <Select
                  value={form.debt_type}
                  onValueChange={(v) => setForm({ ...form, debt_type: v })}
                >
                  <SelectTrigger id="d-type" className="mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DEBT_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="d-currency">Currency</Label>
                <Select
                  value={form.currency}
                  onValueChange={(v) => setForm({ ...form, currency: v })}
                >
                  <SelectTrigger id="d-currency" className="mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {availableCurrencies.length === 0 && (
                      <SelectItem value={BASE_CURRENCY} disabled>
                        {BASE_CURRENCY} (no rates configured)
                      </SelectItem>
                    )}
                    {availableCurrencies.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}{' '}
                        {c !== BASE_CURRENCY && exchangeRates[c] !== undefined && (
                          <span className="text-xs text-muted-foreground">
                            (1 {c} = {Number(exchangeRates[c]).toLocaleString()} {BASE_CURRENCY})
                          </span>
                        )}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {form.currency !== BASE_CURRENCY && exchangeRates[form.currency] !== undefined && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    1 {form.currency} = {Number(exchangeRates[form.currency]).toLocaleString()} {BASE_CURRENCY}
                  </p>
                )}
                {form.currency !== BASE_CURRENCY && (
                  <p className="mt-1 text-xs text-warning">
                    You need to add an exchange rate for {form.currency} in{' '}
                    <Link to="/profile" className="underline">Settings</Link>
                  </p>
                )}
              </div>
              <div>
                <Label htmlFor="d-creditor">Creditor</Label>
                <Input
                  id="d-creditor"
                  value={form.creditor}
                  onChange={(e) => setForm({ ...form, creditor: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="d-original">Original Amount ({form.currency})</Label>
                <Input
                  id="d-original"
                  type="number"
                  min="0"
                  step="0.01"
                  value={String(form.original_amount)}
                  onChange={(e) => setForm({ ...form, original_amount: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="d-balance">Current Balance ({form.currency})</Label>
                <Input
                  id="d-balance"
                  type="number"
                  min="0"
                  step="0.01"
                  value={String(form.current_balance)}
                  onChange={(e) => setForm({ ...form, current_balance: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="d-rate">Interest Rate (% annual)</Label>
                <Input
                  id="d-rate"
                  type="number"
                  min="0"
                  step="0.01"
                  value={String(form.interest_rate)}
                  onChange={(e) => setForm({ ...form, interest_rate: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="d-min">Minimum Payment ({form.currency})</Label>
                <Input
                  id="d-min"
                  type="number"
                  min="0"
                  step="0.01"
                  value={String(form.minimum_payment)}
                  onChange={(e) => setForm({ ...form, minimum_payment: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="d-due">Due Day (1-31)</Label>
                <Input
                  id="d-due"
                  type="number"
                  min="1"
                  max="31"
                  value={form.due_date}
                  onChange={(e) => setForm({ ...form, due_date: Number(e.target.value) })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="d-start">Start Date</Label>
                <Input
                  id="d-start"
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                  required
                />
              </div>
            </div>
            <div>
              <Label htmlFor="d-notes">Notes</Label>
              <Textarea
                id="d-notes"
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : editing ? 'Save Changes' : 'Add Debt'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Manage Charts modal — select which currency charts to display (max 3) */}
      <Dialog open={manageChartsOpen} onOpenChange={setManageChartsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Manage Currency Charts</DialogTitle>
            <DialogDescription>
              Select which currency charts to display on the debt registry (max {MAX_VISIBLE_CHARTS}).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            {Array.from(activeDebtCurrencies).sort().map((curr) => (
              <label key={curr} className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-primary"
                  checked={visibleCurrencies.includes(curr)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setVisibleCurrencies((prev) => [...prev, curr]);
                    } else {
                      setVisibleCurrencies((prev) => prev.filter((c) => c !== curr));
                    }
                  }}
                />
                <span className="font-mono">{curr}</span>
                <span className="text-xs text-muted-foreground">
                  {fmtMoney(
                    (debtsByCurrency[curr] || []).reduce((sum, d) => sum + Number(d.current_balance || 0), 0),
                    curr
                  )}
                </span>
              </label>
            ))}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setManageChartsOpen(false)}
            >
              Close
            </Button>
            <Button
              onClick={() => handleManageCharts(visibleCurrencies)}
              disabled={visibleCurrencies.length === 0}
            >
              Apply Selection
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
