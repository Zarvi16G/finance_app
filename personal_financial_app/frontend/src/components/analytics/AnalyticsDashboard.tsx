/**
 * Dashboard (home page).
 *
 * Fetches from two complementary sources in parallel:
 *  - /analytics/ (analyticsApi) — served from the monthly snapshot cache,
 *    powers the category pie, financial ratios and the debt summary tile;
 *  - /records/ (recordsApi) — live records, powers the income/expense series
 *    and the net trend chart, which the snapshot cache cannot render.
 *
 * Series granularity is chosen automatically: spans of 45 days or less are
 * rendered per-day, longer spans are bucketed per month (see buildSeries).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import CardBox from '../shared/CardBox';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { analyticsApi } from '../../api/ai';
import { recordsApi } from '../../api/profile';
import { getErrorMessage } from '../../api/client';
import type { DashboardData, FinancialRecord } from '../../types';
import { Icon } from '@iconify/react';

const PIE_COLORS = ['#5d87ff', '#49bdbe', '#66d19e', '#ffae1f', '#fa896b', '#5a6a85', '#ff6692'];

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
      const quarterStartMonth = Math.floor(now.getMonth() / 3) - 3; // last complete quarter
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
  // Bucket records two ways (by day and by month) up front, then choose which
  // to render based on the requested span: <=45 days -> one point per day
  // (with a full contiguous calendar so zero days still show), otherwise one
  // point per month, filled to cover every month in the range.
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

function StatCard({
  label,
  value,
  sub,
  icon,
  tone = 'primary',
}: {
  label: string;
  value: string;
  sub?: string;
  icon: string;
  tone?: 'primary' | 'success' | 'warning' | 'error';
}) {
  const toneBg =
    tone === 'success'
      ? 'bg-lightsuccess text-success'
      : tone === 'warning'
        ? 'bg-lightwarning text-warning'
        : tone === 'error'
          ? 'bg-lighterror text-error'
          : 'bg-lightprimary text-primary';

  return (
    <CardBox>
      <div className="p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="mt-1 text-2xl font-semibold text-foreground">{value}</p>
            {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
          </div>
          <span className={`grid h-12 w-12 place-items-center rounded-lg ${toneBg}`}>
            <Icon icon={icon} height={22} width={22} />
          </span>
        </div>
      </div>
    </CardBox>
  );
}

const fmtMoney = (v: number | undefined | null) =>
  `$${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

export default function AnalyticsDashboard() {
  const [preset, setPreset] = useState<PresetKey>('last_month');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [allTime, setAllTime] = useState(false);
  const [analytics, setAnalytics] = useState<DashboardData | null>(null);
  const [series, setSeries] = useState<SeriesPoint[]>([]);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    // "All time" sends no date params: analytics falls back to the full
    // monthly trend and records returns everything.
    const params = allTime
      ? undefined
      : { start_date: startDate, end_date: endDate };
    try {
      const [analyticsData, records] = await Promise.all([
        analyticsApi.dashboard(params),
        recordsApi.list(params),
      ]);
      setAnalytics(analyticsData);
      // For "All time" the series span comes from the min/max record dates,
      // otherwise it is exactly the chosen From/To range.
      const span =
        allTime && records.length > 0
          ? {
              start: records.map((r) => r.date).sort()[0],
              end: records.map((r) => r.date).sort().at(-1) ?? '',
            }
          : { start: startDate, end: endDate };
      if (allTime && records.length === 0) {
        setSeries([]);
      } else {
        setSeries(buildSeries(records, span.start, span.end));
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

  // Money tiles are derived from the live record series (definitive source);
  // the snapshot cache only feeds breakdowns and ratios.
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
  const periodLabel = allTime
    ? 'All time'
    : `${startDate} → ${endDate}`;

  // Chevron navigation walks one month at a time and keeps the From/To dates
  // aligned to that month's start/end, regardless of the active preset.
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

  return (
    <div className="space-y-6">
      <CardBox>
        <div className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={() => shiftMonth(-1)}
              aria-label="Previous month"
            >
              <Icon icon="solar:alt-arrow-left-linear" height={18} width={18} />
            </Button>
            {PRESETS.map((p) => (
              <Button
                key={p.key}
                variant={preset === p.key && !allTime ? 'default' : 'outline'}
                size="sm"
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
            >
              <Icon icon="solar:alt-arrow-right-linear" height={18} width={18} />
            </Button>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              From
              <Input
                type="date"
                className="h-9 w-40"
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
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              To
              <Input
                type="date"
                className="h-9 w-40"
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

      {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

      {loading ? (
        <div className="grid gap-6 md:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Total Income"
              value={fmtMoney(totals.income)}
              sub={periodLabel}
              icon="solar:wallet-money-bold"
              tone="success"
            />
            <StatCard
              label="Total Expenses"
              value={fmtMoney(totals.expenses)}
              sub={periodLabel}
              icon="solar:cart-large-2-bold"
              tone="warning"
            />
            <StatCard
              label="Net Cash Flow"
              value={fmtMoney(totals.net)}
              sub={totals.net >= 0 ? 'Positive balance' : 'Negative balance'}
              icon={totals.net >= 0 ? 'solar:trend-up-bold' : 'solar:trend-down-bold'}
              tone={totals.net >= 0 ? 'primary' : 'error'}
            />
            <StatCard
              label="Savings Rate"
              value={`${totals.savingsRate.toFixed(1)}%`}
              sub="of income saved"
              icon="solar:pie-chart-2-bold"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <CardBox className="xl:col-span-2">
              <div className="p-5">
                <h3 className="font-semibold text-foreground">{chartTitle}</h3>
                <p className="text-sm text-muted-foreground">
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
                          <stop offset="5%" stopColor="#5d87ff" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#5d87ff" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#fa896b" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#fa896b" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="label" stroke="var(--muted-foreground)" fontSize={11} interval="preserveStartEnd" />
                      <YAxis stroke="var(--muted-foreground)" fontSize={11} />
                      <Tooltip
                        contentStyle={{
                          background: 'var(--card)',
                          border: '1px solid var(--border)',
                          borderRadius: 8,
                        }}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="income"
                        name="Income"
                        stroke="#5d87ff"
                        fill="url(#incomeGrad)"
                      />
                      <Area
                        type="monotone"
                        dataKey="expenses"
                        name="Expenses"
                        stroke="#fa896b"
                        fill="url(#expenseGrad)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </CardBox>

            <CardBox>
              <div className="p-5">
                <h3 className="font-semibold text-foreground">Expenses by Category</h3>
                <p className="text-sm text-muted-foreground">Selected period breakdown</p>
                {categories.length === 0 ? (
                  <p className="mt-6 text-sm text-muted-foreground">No expense data in this period.</p>
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
                              <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              background: 'var(--card)',
                              border: '1px solid var(--border)',
                              borderRadius: 8,
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="mt-4 space-y-2">
                      {categories.map((cat, i) => (
                        <div key={cat.category} className="flex items-center justify-between text-sm">
                          <span className="flex items-center gap-2 text-muted-foreground">
                            <span
                              className="h-2.5 w-2.5 rounded-full"
                              style={{ background: PIE_COLORS[i % PIE_COLORS.length] }}
                            />
                            {cat.category}
                          </span>
                          <span className="font-medium text-foreground">{fmtMoney(cat.total)}</span>
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
                <h3 className="font-semibold text-foreground">
                  {dayMode ? 'Daily Net Trend' : 'Monthly Net Trend'}
                </h3>
                <p className="text-sm text-muted-foreground">
                  Net savings per {dayMode ? 'day' : 'month'}
                </p>
                <div className="mt-4 h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="label" stroke="var(--muted-foreground)" fontSize={11} interval="preserveStartEnd" />
                      <YAxis stroke="var(--muted-foreground)" fontSize={11} />
                      <Tooltip
                        contentStyle={{
                          background: 'var(--card)',
                          border: '1px solid var(--border)',
                          borderRadius: 8,
                        }}
                      />
                      <Bar dataKey="net" name="Net" fill="#5d87ff" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </CardBox>

            <CardBox>
              <div className="p-5">
                <h3 className="font-semibold text-foreground">Financial Health Ratios</h3>
                {allTime ? (
                  <p className="mt-4 text-sm text-muted-foreground">
                    Ratios are shown per period — select a month, quarter or year to view them.
                  </p>
                ) : ratios ? (
                  <div className="mt-4 grid grid-cols-2 gap-4">
                    <RatioTile label="Current Ratio" value={ratios.liquidity.current_ratio} />
                    <RatioTile label="Cash Ratio" value={ratios.liquidity.cash_ratio} />
                    <RatioTile label="Net Profit Margin" value={ratios.profitability.net_profit_margin} />
                    <RatioTile label="Expense Ratio" value={ratios.profitability.expense_ratio} />
                    <RatioTile label="Debt to Income" value={ratios.solvency.debt_to_income} unit="%" />
                    <RatioTile label="Income Growth YoY" value={ratios.growth.income_growth_yoy} unit="%" />
                  </div>
                ) : null}
                {debtSummary && (
                  <div className="mt-5 rounded-lg bg-lightprimary p-4">
                    <p className="text-sm font-medium text-primary">Debt Summary</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">
                      {fmtMoney(debtSummary.total_balance)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {debtSummary.total_debts} active debt{debtSummary.total_debts === 1 ? '' : 's'} · min
                      payment {fmtMoney(debtSummary.total_monthly_payment)}
                    </p>
                  </div>
                )}
              </div>
            </CardBox>
          </div>
        </>
      )}
    </div>
  );
}

function RatioTile({ label, value, unit }: { label: string; value: number | null; unit?: string }) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground">
        {value === null || value === undefined ? '—' : `${value}${unit ?? ''}`}
      </p>
    </div>
  );
}