/**
 * Individual debt detail page: a single statement sheet for one debt —
 * summary figures, paid-to-date progress and the amortization curve
 * showing how the outstanding balance is scheduled to be paid down.
 *
 * Multi-currency support:
 * - Uses the debt's own `currency` field for native amounts.
 * - A toggle switches the amortization chart between native currency
 *   and COP-converted view (using rates from the profile).
 */
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Icon } from '@iconify/react';
import CardBox from '../shared/CardBox';
import PageHeader from '../shared/PageHeader';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { debtsApi } from '../../api/debts';
import { profileApi } from '../../api/profile';
import { getErrorMessage } from '../../api/client';
import { fmtMoney, fmtMoneyCompact, convertToBase, BASE_CURRENCY } from '../../lib/money';
import { buildAmortizationSchedule, monthLabel } from '../../lib/amortization';
import type { Debt } from '../../types';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';

const cssVar = (name: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#18251c';

const statusVariant = (status: string): 'primary' | 'success' | 'warning' | 'error' => {
  if (status === 'paid_off') return 'success';
  if (status === 'defaulted') return 'error';
  if (status === 'in_grace') return 'warning';
  return 'primary';
};

const tooltipStyle = {
  background: 'var(--card)',
  border: '1px solid var(--border)',
  borderRadius: 2,
  fontSize: 12,
  fontFamily: "'IBM Plex Mono', monospace",
} as const;

const axisTick = {
  fontFamily: "'IBM Plex Mono', monospace",
  fontSize: 10,
  fill: 'var(--muted-foreground)',
} as const;

function StatTile({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: string;
  tone?: 'default' | 'error' | 'success';
}) {
  const color =
    tone === 'error' ? 'text-error' : tone === 'success' ? 'text-success' : 'text-foreground';
  return (
    <CardBox>
      <div className="p-5">
        <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
          {label}
        </p>
        <p className={`mt-1 font-mono text-2xl font-medium tabular-nums ${color}`}>{value}</p>
      </div>
    </CardBox>
  );
}

export default function DebtDetail() {
  const { id } = useParams<{ id: string }>();
  const [debt, setDebt] = useState<Debt | null>(null);
  const [exchangeRates, setExchangeRates] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [chartView, setChartView] = useState<'native' | 'cop'>('native');

  useEffect(() => {
    if (!id) return;
    profileApi.get().then((s) => {
      setExchangeRates(s.exchange_rates || {});
    }).catch(() => {});
    debtsApi
      .get(id)
      .then(setDebt)
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [id]);

  const schedule = useMemo(() => {
    if (!debt) return null;
    return buildAmortizationSchedule({
      originalAmount: Number(debt.original_amount),
      currentBalance: Number(debt.current_balance),
      annualRatePct: Number(debt.interest_rate),
      minPayment: Number(debt.minimum_payment),
      startDate: debt.start_date,
      status: debt.status,
    });
  }, [debt]);

  const debtCurrency = debt?.currency || BASE_CURRENCY;
  const displayCurrency = chartView === 'cop' ? BASE_CURRENCY : debtCurrency;

  // Convert the entire amortization schedule to COP when in COP view
  const displaySchedule = useMemo(() => {
    if (!schedule || !debt) return schedule;
    if (chartView === 'native') return schedule;
    // COP view: convert each point's balance and paid amounts
    return {
      points: schedule.points.map((p) => ({
        ...p,
        balance: convertToBase(p.balance, debtCurrency, exchangeRates),
        paid: convertToBase(p.paid, debtCurrency, exchangeRates),
      })),
      payoffKey: schedule.payoffKey,
      neverPaysOff: schedule.neverPaysOff,
      projectedInterest: convertToBase(schedule.projectedInterest, debtCurrency, exchangeRates),
    };
  }, [schedule, debt, chartView, debtCurrency, exchangeRates]);

  const paid = useMemo(() => {
    if (!debt) return 0;
    return Math.max(0, Number(debt.original_amount) - Number(debt.current_balance));
  }, [debt]);

  const payoffLabel = useMemo(() => {
    if (!debt || !schedule) return '—';
    if (debt.status === 'paid_off') return 'Paid off';
    if (schedule.neverPaysOff) return 'Never at minimum payment';
    return schedule.payoffKey ? monthLabel(schedule.payoffKey) : '—';
  }, [debt, schedule]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-16 w-2/3 animate-pulse rounded-sm bg-muted" />
        <div className="grid gap-6 md:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-sm bg-muted" />
          ))}
        </div>
        <div className="h-96 animate-pulse rounded-sm bg-muted" />
      </div>
    );
  }

  if (error || !debt || !schedule) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Liabilities Ledger"
          title="Debt not found"
          description="This entry could not be loaded."
          actions={
            <Button asChild variant="outline">
              <Link to="/debts">
                <Icon icon="solar:alt-arrow-left-linear" height={16} width={16} />
                Back to registry
              </Link>
            </Button>
          }
        />
        {error && (
          <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>
        )}
      </div>
    );
  }

  const original = Number(debt.original_amount);
  const balance = Number(debt.current_balance);
  const rate = Number(debt.interest_rate);
  const minPayment = Number(debt.minimum_payment);
  const monthlyInterest = Number(debt.monthly_interest) || balance * (rate / 100 / 12);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Liabilities Ledger · Account Statement"
        title={debt.name}
        description={`${debt.creditor} · ${debt.debt_type_display}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={statusVariant(debt.status)}>{debt.status_display}</Badge>
            <Button asChild variant="outline">
              <Link to="/debts">
                <Icon icon="solar:alt-arrow-left-linear" height={16} width={16} />
                Back to registry
              </Link>
            </Button>
          </div>
        }
      />

      {/* Summary sheet */}
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label={`Balance Outstanding (${debtCurrency})`}
          value={fmtMoney(balance, debtCurrency)}
          tone={balance > 0 ? 'error' : 'success'}
        />
        <StatTile label="Annual Rate" value={`${rate.toFixed(2)}%`} />
        <StatTile
          label={`Monthly Payment (${debtCurrency})`}
          value={fmtMoney(minPayment, debtCurrency)}
        />
        <StatTile
          label={`Monthly Interest (${debtCurrency})`}
          value={fmtMoney(monthlyInterest, debtCurrency)}
          tone="error"
        />
      </div>

      {/* Paid to date */}
      <CardBox>
        <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
          <div>
            <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Paid to date
            </p>
             <p className="mt-1 font-mono text-2xl font-medium tabular-nums text-success">
               {fmtMoney(paid, debtCurrency)}
             </p>
           </div>
           <div className="h-2 w-full max-w-[14rem] overflow-hidden rounded-sm bg-muted">
             <div
               className="h-full rounded-sm bg-success transition-all"
               style={{ width: `${Math.min(debt.progress_percentage, 100)}%` }}
             />
           </div>
           <div className="font-mono text-xs tabular-nums text-muted-foreground">
             {debt.progress_percentage}% ·{' '}
             <span className="text-foreground">{fmtMoney(original, debtCurrency)}</span> original
           </div>
        </div>
        <div className="flex flex-wrap gap-x-8 gap-y-2 border-t border-border px-5 py-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            Estimated payoff — <span className="text-foreground">{payoffLabel}</span>
          </p>
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            Due day — <span className="text-foreground">{debt.due_date}</span>
          </p>
          {debtCurrency !== BASE_CURRENCY && schedule.payoffKey && (
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              Projected interest —{' '}
              <span className="text-foreground">
                {fmtMoney(schedule.projectedInterest, debtCurrency)}{' '}
                <span className="text-xs opacity-70">
                  ({fmtMoney(convertToBase(schedule.projectedInterest, debtCurrency, exchangeRates), BASE_CURRENCY)} in {BASE_CURRENCY})
                </span>
              </span>
            </p>
          )}
          {debtCurrency === BASE_CURRENCY && schedule.payoffKey && (
            <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              Projected interest —{' '}
              <span className="text-foreground">{fmtMoney(schedule.projectedInterest, debtCurrency)}</span>
            </p>
          )}
        </div>
        {schedule.neverPaysOff && (
          <p className="border-t border-border px-5 py-3 font-mono text-xs text-warning">
            At the minimum payment, interest consumes the whole payment — this debt never gets
            paid off. Raising the monthly payment is the only way down.
          </p>
        )}
      </CardBox>

      {/* Amortization curve */}
      <CardBox className="overflow-hidden">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border px-5 py-4">
          <div>
            <h3 className="font-display text-xl font-normal text-foreground">Balance over time</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Outstanding balance vs. principal paid, month by month — projected at the minimum
              payment.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-4 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 bg-success" aria-hidden="true" />
              Paid to date
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 bg-error" aria-hidden="true" />
              Outstanding
            </span>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-b border-border px-5 py-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            {chartView === 'cop' ? `View: ${BASE_CURRENCY}` : `View: ${debtCurrency} (native)`}
          </span>
          <Select value={chartView} onValueChange={(v) => setChartView(v as 'native' | 'cop')}>
            <SelectTrigger className="h-7 w-36 font-mono text-[10px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="native">{debtCurrency} (native)</SelectItem>
              <SelectItem value="cop">{BASE_CURRENCY} (converted)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="h-[340px] p-5">
          {displaySchedule && (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={displaySchedule.points} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="debtGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={cssVar('--error')} stopOpacity={0.24} />
                    <stop offset="95%" stopColor={cssVar('--error')} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" />
                <XAxis
                  dataKey="label"
                  tick={axisTick}
                  interval="preserveStartEnd"
                  minTickGap={24}
                />
                <YAxis
                  tick={axisTick}
                  tickFormatter={(v: number) => fmtMoneyCompact(v, displayCurrency)}
                  width={64}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  labelFormatter={(label) => `Month — ${label}`}
                  formatter={(value, name) => [fmtMoney(Number(value), displayCurrency), String(name)]}
                />
                <ReferenceLine
                  y={Number(displaySchedule.points[0]?.balance > 0
                    ? original
                    : convertToBase(original, debtCurrency, exchangeRates))}
                  stroke="var(--border)"
                  strokeDasharray="4 3"
                  label={{
                    value: `Original ${fmtMoneyCompact(original, displayCurrency)}`,
                    position: 'insideTopLeft',
                    fontSize: 10,
                    fontFamily: "'IBM Plex Mono', monospace",
                    fill: 'var(--muted-foreground)',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="balance"
                  name="Outstanding"
                  stroke={cssVar('--error')}
                  strokeWidth={2}
                  fill="url(#debtGrad)"
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="paid"
                  name="Paid to date"
                  stroke={cssVar('--success')}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardBox>

      {debt.notes && (
        <CardBox>
          <div className="p-5">
            <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Notes
            </p>
            <p className="mt-1 text-sm text-foreground/80">{debt.notes}</p>
          </div>
        </CardBox>
      )}
    </div>
  );
}
