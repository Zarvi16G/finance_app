/**
 * Dashboard (home page) — rendered as a monthly cash-flow statement.
 *
 *  - Letterhead: period strip behaves like a "statement period" field.
 *  - Stat tiles are ledger lines: mono figures on ruled sheets.
 *  - The Running Balance register (the signature element) lists live
 *    records as statement rows with an accumulating balance column.
 *  - Charts use theme tokens so they follow light/dark ink.
 *
 * Data sources (unchanged):
 *  - /analytics/ (analyticsApi) — snapshot cache: category pie, ratios, debt summary
 *  - /records/ (recordsApi) — live records: income/expense series, net trend, register
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import CardBox from '../shared/CardBox';
import PageHeader from '../shared/PageHeader';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { analyticsApi } from '../../api/ai';
import { recordsApi, profileApi } from '../../api/profile';
import { getErrorMessage } from '../../api/client';
import { fmtMoney } from '../../lib/money';
import type { DashboardData, FinancialRecord } from '../../types';
import { Icon } from '@iconify/react';

const CHART_TOKENS = ['--chart-1', '--chart-2', '--chart-3', '--chart-4', '--chart-5', '--info'];

const cssVar = (name: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#18251c';

const chartColor = (i: number) => cssVar(CHART_TOKENS[i % CHART_TOKENS.length]);

const toISODate = (d: Date) => d.toISOString().slice(0, 10);

const today = () => {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
};

const monthRange = (base: Date) => {
  const start = new Date(base.getFullYear(), base.getMonth(), 1);
  const end = new Date(base.getFullYear(), base.getMonth() + 1, 0);
  return { start: toISODate(start), end: toISODate(end) };
};

type PresetKey = 'last_month' | 'this_month' | 'quarter' | 'year' | 'all';

const PRESETS: Array<{ key: PresetKey; label: string }> = [
  { key: 'last_month', label: 'Last Month' },
  { key: 'this_month', label: 'This Month' },
  { key: 'quarter', label: 'Quarter' },
  { key: 'year', label: 'Year' },
  { key: 'all', label: 'All' },
];

function resolvePreset(key: PresetKey): { start?: string; end?: string; all: boolean } {
  const now = today();
  switch (key) {
    case 'last_month': {
      const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      return { ...monthRange(prev), all: false };
    }
    case 'this_month': {
      return { ...monthRange(now), all: false };
    }
    case 'quarter': {
      const quarterStartMonth = Math.floor(now.getMonth() / 3) - 3;
      const start = new Date(now.getFullYear(), quarterStartMonth, 1);
      const end = new Date(now.getFullYear(), quarterStartMonth + 3, 0);
      return { start: toISODate(start), end: toISODate(end), all: false };
    }
    case 'year': {
      const start = new Date(now.getFullYear(), 0, 1);
      return { start: toISODate(start), end: toISODate(now), all: false };
    }
    case 'all':
      return { start: undefined, end: undefined, all: true };
  }
}

interface SeriesPoint {
  label: string;
  income: number;
  expenses: number;
  net: number;
}

function buildSeries(records: FinancialRecord[], startDate: string, endDate: string): SeriesPoint[] {
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);
  const days = Math.round((end.getTime() - start.getTime()) / 86400000) + 1;

  const byDay = new Map<string, SeriesPoint>();
  const byMonth = new Map<string, SeriesPoint>();

  const add = (map: Map<string, SeriesPoint>, key: string, income: number, expenses: number) => {
    const point = map.get(key) ?? { label: key, income: 0, expenses: 0, net: 0 };
    point.income += income;
    point.expenses += expenses;
    map.set(key, point);
  };

  for (const record of records) {
    const amount = Number(record.amount) || 0;
    if (record.type === 'income') {
      add(byDay, record.date, amount, 0);
      add(byMonth, record.date.slice(0, 7), amount, 0);
    } else if (record.type === 'expense') {
      add(byDay, record.date, 0, amount);
      add(byMonth, record.date.slice(0, 7), 0, amount);
    }
  }

  if (days <= 45) {
    const points: SeriesPoint[] = [];
    for (let i = 0; i < days; i++) {
      const date = new Date(start.getTime() + i * 86400000);
      const key = toISODate(date);
      const point = byDay.get(key) ?? { label: key, income: 0, expenses: 0, net: 0 };
      point.label = `${date.getMonth() + 1}/${date.getDate()}`;
      point.net = point.income - point.expenses;
      points.push(point);
    }
    return points;
  }

  const points: SeriesPoint[] = [];
  const cursor = new Date(start.getFullYear(), start.getMonth(), 1);
  const last = new Date(end.getFullYear(), end.getMonth(), 1);
  while (cursor <= last) {
    const key = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}`;
    const point = byMonth.get(key) ?? { label: key, income: 0, expenses: 0, net: 0 };
    point.net = point.income - point.expenses;
    points.push(point);
    cursor.setMonth(cursor.getMonth() + 1);
  }
  return points;
}

/* ---- motion helpers ------------------------------------------------------ */

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;

function useCountUp(target: number, duration = 800) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (prefersReducedMotion()) {
      setValue(target);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return value;
}

/* ---- ledger primitives --------------------------------------------------- */

function LedgerStat({
  label,
  value,
  sign,
  tone = 'ink',
  sub,
}: {
  label: string;
  value: string;
  sign?: string;
  tone?: 'ink' | 'credit' | 'debit';
  sub?: string;
}) {
  const color =
    tone === 'credit' ? 'text-success' : tone === 'debit' ? 'text-error' : 'text-foreground';
  return (
    <CardBox className="overflow-hidden">
      <div className="flex items-center justify-between px-5 pt-4 pb-2">
        <span className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
          {label}
        </span>
        <span className="h-1.5 w-1.5 rounded-full bg-border" aria-hidden="true" />
      </div>
      <div className="border-t border-border px-5 py-3">
        <p className={`font-mono text-2xl font-medium tabular-nums ${color}`}>
          {sign && <span className="mr-0.5">{sign}</span>}
          {value}
        </p>
        {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
      </div>
    </CardBox>
  );
}

const shortDate = (iso: string) => {
  const d = new Date(`${iso}T00:00:00`);
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

interface RegisterRow {
  id: number;
  date: string;
  description: string;
  amount: number;
  type: string;
  balance: number;
}

export default function AnalyticsDashboard() {
  const [preset, setPreset] = useState<PresetKey>('last_month');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [allTime, setAllTime] = useState(false);
  const [analytics, setAnalytics] = useState<DashboardData | null>(null);
  const [series, setSeries] = useState<SeriesPoint[]>([]);
  const [records, setRecords] = useState<FinancialRecord[]>([]);
  const [currency, setCurrency] = useState('USD');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const applyPreset = (key: PresetKey) => {
    const range = resolvePreset(key);
    setPreset(key);
    setAllTime(range.all);
    setStartDate(range.start ?? '');
    setEndDate(range.end ?? '');
  };

  useEffect(() => {
    applyPreset('last_month');
    profileApi
      .get()
      .then((s) => setCurrency(s.currency || 'USD'))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    const params = allTime
      ? undefined
      : { start_date: startDate, end_date: endDate };
    try {
      const [analyticsData, recordsData] = await Promise.all([
        analyticsApi.dashboard(params),
        recordsApi.list(params),
      ]);
      setAnalytics(analyticsData);
      setRecords(recordsData);
      const span =
        allTime && recordsData.length > 0
          ? {
              start: recordsData.map((r) => r.date).sort()[0],
              end: recordsData.map((r) => r.date).sort().at(-1) ?? '',
            }
          : { start: startDate, end: endDate };
      if (allTime && recordsData.length === 0) {
        setSeries([]);
      } else {
        setSeries(buildSeries(recordsData, span.start, span.end));
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, allTime]);

  useEffect(() => {
    if (startDate || allTime) {
      fetchData();
    }
  }, [fetchData, startDate, endDate, allTime]);

  const totals = useMemo(() => {
    const income = series.reduce((sum, p) => sum + p.income, 0);
    const expenses = series.reduce((sum, p) => sum + p.expenses, 0);
    const net = income - expenses;
    return {
      income,
      expenses,
      net,
      savingsRate: income > 0 ? (net / income) * 100 : 0,
    };
  }, [series]);

  /* The running balance register — oldest to newest, closing at the end. */
  const register = useMemo<RegisterRow[]>(() => {
    const sorted = [...records].sort(
      (a, b) => a.date.localeCompare(b.date) || a.id - b.id,
    );
    let balance = 0;
    const rows: RegisterRow[] = [];
    for (const r of sorted) {
      const amount = r.type === 'expense' ? -Math.abs(Number(r.amount) || 0) : Math.abs(Number(r.amount) || 0);
      balance += amount;
      rows.push({
        id: r.id,
        date: r.date,
        description: r.description || r.category,
        amount,
        type: r.type,
        balance,
      });
    }
    return rows;
  }, [records]);
  const registerPage = register.length > 12 ? register.slice(-12) : register;
  const registerCount = register.length;
  const registerTotal = register.length > 0 ? register[register.length - 1].balance : 0;

  const categories = useMemo(() => {
    const map = new Map<string, { total: number; count: number }>();
    for (const record of analytics?.expense_by_category ?? []) {
      map.set(record.category, { total: Number(record.total), count: record.count });
    }
    return [...map.entries()]
      .sort((a, b) => b[1].total - a[1].total)
      .map(([category, v]) => ({ category, total: v.total, count: v.count }));
  }, [analytics]);

  const ratios = analytics?.financial_ratios;
  const debtSummary = analytics?.debt_summary;
  const dayMode = series.length > 0 && series.length <= 45;
  const periodLabel = allTime ? 'All time' : `${startDate} → ${endDate}`;
  const hasAny = records.length > 0 || (categories.length > 0 && !loading);

  const shiftMonth = (delta: number) => {
    const base = new Date(`${startDate || toISODate(today())}T00:00:00`);
    const next = monthRange(new Date(base.getFullYear(), base.getMonth() + delta, 1));
    setPreset('last_month');
    setAllTime(false);
    setStartDate(next.start);
    setEndDate(next.end);
  };

  const chartTitle = allTime
    ? 'Income vs Expenses — All Time (monthly)'
    : dayMode
      ? `Daily Income vs Expenses — ${startDate.slice(0, 7)}`
      : `Income vs Expenses — ${startDate} to ${endDate}`;

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

  const animatedIncome = useCountUp(totals.income);
  const animatedExpenses = useCountUp(totals.expenses);
  const animatedNet = useCountUp(totals.net);
  const animatedRate = useCountUp(Math.abs(totals.savingsRate));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Cash Flow Statement"
        title="Your money, in and out"
        description="What came in, what went out, and what is left — over the selected period."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to="/statements/upload">
              <Icon icon="solar:upload-linear" height={16} width={16} />
              Import statement
            </Link>
          </Button>
        }
      />

      {/* Statement period strip */}
      <CardBox className="px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground mr-1">
              Period
            </span>
            <Button
              variant="outline"
              size="icon"
              onClick={() => shiftMonth(-1)}
              aria-label="Previous month"
              className="h-8 w-8"
            >
              <Icon icon="solar:alt-arrow-left-linear" height={15} width={15} />
            </Button>
            {PRESETS.map((p) => (
              <Button
                key={p.key}
                variant={preset === p.key && !allTime ? 'default' : 'outline'}
                size="sm"
                className="h-8 font-mono text-[11px] uppercase tracking-[0.08em]"
                onClick={() => applyPreset(p.key)}
              >
                {p.label}
              </Button>
            ))}
            <Button
              variant="outline"
              size="icon"
              onClick={() => shiftMonth(1)}
              aria-label="Next month"
              className="h-8 w-8"
            >
              <Icon icon="solar:alt-arrow-right-linear" height={15} width={15} />
            </Button>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              From
              <Input
                type="date"
                className="h-8 w-36 sm:w-40"
                value={startDate}
                disabled={allTime}
                onChange={(e) => {
                  if (!e.target.value) return;
                  setStartDate(e.target.value);
                  setAllTime(false);
                  setPreset('last_month');
                }}
              />
            </label>
            <label className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              To
              <Input
                type="date"
                className="h-8 w-36 sm:w-40"
                value={endDate}
                min={startDate}
                disabled={allTime}
                onChange={(e) => {
                  if (!e.target.value) return;
                  setEndDate(e.target.value);
                  setAllTime(false);
                  setPreset('last_month');
                }}
              />
            </label>
          </div>
        </div>
      </CardBox>

      {error && (
        <p className="rounded-sm bg-error/10 px-3 py-2 font-mono text-xs text-error">{error}</p>
      )}

      {loading ? (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-sm bg-muted" />
          ))}
        </div>
      ) : (
        <>
          {/* Ledger summary lines */}
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            <LedgerStat
              label="Total Income"
              value={fmtMoney(animatedIncome, currency)}
              sign="+"
              tone="credit"
              sub={periodLabel}
            />
            <LedgerStat
              label="Total Expenses"
              value={fmtMoney(animatedExpenses, currency)}
              sign="−"
              tone="debit"
              sub={periodLabel}
            />
            <LedgerStat
              label="Net Cash Flow"
              value={fmtMoney(animatedNet, currency)}
              sign={totals.net >= 0 ? '+' : '−'}
              tone={totals.net >= 0 ? 'ink' : 'debit'}
              sub={totals.net >= 0 ? 'Positive balance' : 'Negative balance'}
            />
            <LedgerStat
              label="Savings Rate"
              value={`${animatedRate.toFixed(1)}%`}
              tone={totals.savingsRate >= 0 ? 'ink' : 'debit'}
              sub="of income saved"
            />
          </div>

          {/* The running balance register — the signature of the ledger */}
          <CardBox className="overflow-hidden">
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border px-5 py-4">
              <div>
                <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  Running Balance — Ledger
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {registerCount === 0
                    ? 'No entries this period'
                    : `${registerCount} entr${registerCount === 1 ? 'y' : 'ies'} · closing ${fmtMoney(registerTotal, currency)}`}
                </p>
              </div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                {periodLabel}
              </p>
            </div>

            {registerCount === 0 ? (
              <div className="px-5 py-14 text-center">
                <Icon
                  icon="solar:inbox-outline"
                  height={40}
                  width={40}
                  className="mx-auto text-muted-foreground/60"
                />
                <p className="mx-auto mt-4 max-w-sm text-sm text-muted-foreground">
                  This statement is blank. Import a bank statement PDF to start the ledger — the
                  balance column keeps itself.
                </p>
                <Button asChild variant="outline" size="sm" className="mt-4">
                  <Link to="/statements/upload">Import a statement</Link>
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-5 py-2.5 text-left font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Date
                      </th>
                      <th className="px-5 py-2.5 text-left font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Description
                      </th>
                      <th className="px-5 py-2.5 text-right font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Credit
                      </th>
                      <th className="px-5 py-2.5 text-right font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Debit
                      </th>
                      <th className="px-5 py-2.5 text-right font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Balance
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {registerPage.map((row, i) => (
                      <tr
                        key={row.id}
                        className="ledger-print-row border-b border-border/70"
                        style={{ animationDelay: `${Math.min(i, 8) * 55}ms` }}
                      >
                        <td className="px-5 py-2.5 font-mono text-xs tabular-nums text-muted-foreground">
                          {shortDate(row.date)}
                        </td>
                        <td className="max-w-[16rem] truncate px-5 py-2.5 text-foreground">
                          {row.description}
                        </td>
                        <td className="px-5 py-2.5 text-right font-mono text-xs tabular-nums text-success">
                          {row.amount > 0 ? fmtMoney(row.amount, currency) : ''}
                        </td>
                        <td className="px-5 py-2.5 text-right font-mono text-xs tabular-nums text-error">
                          {row.amount < 0 ? fmtMoney(Math.abs(row.amount), currency) : ''}
                        </td>
                        <td className="px-5 py-2.5 text-right font-mono text-xs font-semibold tabular-nums text-foreground">
                          {fmtMoney(row.balance, currency)}
                        </td>
                      </tr>
                    ))}
                    {registerCount > registerPage.length && (
                      <tr className="border-b border-border/70">
                        <td
                          colSpan={5}
                          className="px-5 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground"
                        >
                          … {registerCount - registerPage.length} earlier entr
                          {registerCount - registerPage.length === 1 ? 'y' : 'ies'} this period
                        </td>
                      </tr>
                    )}
                    <tr className="border-t-2 border-foreground/70">
                      <td colSpan={4} className="px-5 py-3 text-right font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                        Closing Balance
                      </td>
                      <td className={`px-5 py-3 text-right font-mono text-sm font-semibold tabular-nums ${registerTotal < 0 ? 'text-error' : 'text-foreground'}`}>
                        {fmtMoney(registerTotal, currency)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </CardBox>

          <div className="grid gap-6 xl:grid-cols-3">
            <CardBox className="xl:col-span-2">
              <div className="p-5">
                <h3 className="font-display text-xl font-normal text-foreground">{chartTitle}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {dayMode
                    ? 'Per day of the selected month'
                    : allTime
                      ? 'Per month across all your records'
                      : 'Per month across the selected range'}
                </p>
                <div className="mt-4 h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={cssVar('--chart-1')} stopOpacity={0.28} />
                          <stop offset="95%" stopColor={cssVar('--chart-1')} stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={cssVar('--chart-2')} stopOpacity={0.28} />
                          <stop offset="95%" stopColor={cssVar('--chart-2')} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" />
                      <XAxis dataKey="label" tick={axisTick} interval="preserveStartEnd" />
                      <YAxis tick={axisTick} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Area
                        type="monotone"
                        dataKey="income"
                        name="Income"
                        stroke={cssVar('--chart-1')}
                        strokeWidth={2}
                        fill="url(#incomeGrad)"
                      />
                      <Area
                        type="monotone"
                        dataKey="expenses"
                        name="Expenses"
                        stroke={cssVar('--chart-2')}
                        strokeWidth={2}
                        fill="url(#expenseGrad)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </CardBox>

            <CardBox>
              <div className="p-5">
                <h3 className="font-display text-xl font-normal text-foreground">
                  Expenses by Category
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">Selected period breakdown</p>
                {categories.length === 0 ? (
                  <p className="mt-6 text-sm text-muted-foreground">
                    No expense data in this period.
                  </p>
                ) : (
                  <>
                    <div className="mt-4 h-[180px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={categories}
                            dataKey="total"
                            nameKey="category"
                            innerRadius={50}
                            outerRadius={80}
                            paddingAngle={2}
                          >
                            {categories.map((_, i) => (
                              <Cell key={i} fill={chartColor(i)} stroke="none" />
                            ))}
                          </Pie>
                          <Tooltip contentStyle={tooltipStyle} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="mt-4 divide-y divide-border/70">
                      {categories.map((cat, i) => (
                        <div key={cat.category} className="flex items-center justify-between py-2 text-sm">
                          <span className="flex items-center gap-2.5 text-muted-foreground">
                            <span className="h-2 w-2" style={{ background: chartColor(i) }} />
                            {cat.category}
                          </span>
                          <span className="font-mono text-xs tabular-nums font-medium text-foreground">
                            {fmtMoney(cat.total, currency)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </CardBox>
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <CardBox>
              <div className="p-5">
                <h3 className="font-display text-xl font-normal text-foreground">
                  {dayMode ? 'Daily Net Trend' : 'Monthly Net Trend'}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Net savings per {dayMode ? 'day' : 'month'} — green above zero, red below
                </p>
                <div className="mt-4 h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" />
                      <XAxis dataKey="label" tick={axisTick} interval="preserveStartEnd" />
                      <YAxis tick={axisTick} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Bar dataKey="net" name="Net" radius={[2, 2, 0, 0]}>
                        {series.map((p, i) => (
                          <Cell
                            key={i}
                            fill={p.net >= 0 ? cssVar('--chart-1') : cssVar('--chart-2')}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </CardBox>

            <CardBox>
              <div className="p-5">
                <h3 className="font-display text-xl font-normal text-foreground">
                  Financial Health Ratios
                </h3>
                {allTime ? (
                  <p className="mt-4 text-sm text-muted-foreground">
                    Ratios are shown per period — select a month, quarter or year to view them.
                  </p>
                ) : ratios ? (
                  <div className="mt-2 divide-y divide-border/70">
                    <RatioTile label="Current Ratio" value={ratios.liquidity.current_ratio} />
                    <RatioTile label="Cash Ratio" value={ratios.liquidity.cash_ratio} />
                    <RatioTile label="Net Profit Margin" value={ratios.profitability.net_profit_margin} />
                    <RatioTile label="Expense Ratio" value={ratios.profitability.expense_ratio} />
                    <RatioTile label="Debt to Income" value={ratios.solvency.debt_to_income} unit="%" />
                    <RatioTile label="Income Growth YoY" value={ratios.growth.income_growth_yoy} unit="%" />
                  </div>
                ) : null}
                {debtSummary && (
                  <div className="mt-5 border border-border bg-lightprimary px-4 py-3">
                    <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-primary">
                      Debt Summary
                    </p>
                    <p className="mt-1 font-mono text-2xl font-medium tabular-nums text-foreground">
                      {fmtMoney(debtSummary.total_balance, currency)}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {debtSummary.total_debts} active debt{debtSummary.total_debts === 1 ? '' : 's'} ·
                      min payment {fmtMoney(debtSummary.total_monthly_payment, currency)}
                    </p>
                  </div>
                )}
              </div>
            </CardBox>
          </div>

          {!hasAny && !loading && (
            <p className="text-center text-xs text-muted-foreground">
              Everything on this page is computed from your records — the ledger has no other
              source.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function RatioTile({ label, value, unit }: { label: string; value: number | null; unit?: string }) {
  return (
    <div className="flex items-baseline justify-between py-2.5">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="font-mono text-sm tabular-nums font-semibold text-foreground">
        {value === null || value === undefined ? '—' : `${value}${unit ?? ''}`}
      </span>
    </div>
  );
}
