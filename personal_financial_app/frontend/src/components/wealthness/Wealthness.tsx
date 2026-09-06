/**
 * Wealthness — financial health, read from /api/wealthness/.
 *
 * The screen deliberately has no single score. Each metric is a row stating
 * its value, the rule of thumb it is being judged against, and its band; the
 * footnote says out loud that those thresholds are conventions, not results
 * derived from the user's data. That is the honest shape for numbers whose
 * precision is borrowed.
 *
 * A metric whose status comes back `unknown` keeps its row and says what is
 * missing, rather than disappearing or rendering as zero.
 */
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import PageHeader from '../shared/PageHeader';
import BaseCurrencyBadge from '../shared/BaseCurrencyBadge';
import ConversionNotice from '../shared/ConversionNotice';
import StatusBadge from '../shared/StatusBadge';
import { Figure } from '../shared/Figure';
import { wealthnessApi } from '../../api/wealthness';
import { getErrorMessage } from '../../api/client';
import { useChartPalette } from '../../lib/chartColors';
import { fmtFigure, fmtMonth, fmtNumber, fmtPercent, fmtSignedPercent } from '../../lib/money';
import {
  moneyTooltipFormatter,
  monthLabelFormatter,
  shortMonthTick,
  tooltipStyle,
} from '../../lib/chartFormat';
import { metricNote, trendNote } from '../../lib/metricCopy';
import type { MetricStatus, NetFlowPoint, WealthnessOverview } from '../../types';

const WINDOWS = [6, 12, 24];

/** The headline sentence, built from the trend the backend reported.
 *
 *  Each shape is its own dictionary key rather than a sentence assembled from
 *  fragments: word order and agreement differ between languages, and gluing
 *  a verb into a template is how a translation ends up ungrammatical. */
function headlineFor(data: WealthnessOverview, t: TFunction): string {
  const { direction, change_pct, basis } = data.trend;
  const subject = t(
    basis === 'net_flow' ? 'wealthness.subjectNetFlow' : 'wealthness.subjectNetWorth',
  );

  if (direction === 'unknown') return t('wealthness.unknownTrend');
  if (direction === 'stable') return t('wealthness.stable', { subject });
  if (change_pct === null) {
    return t(direction === 'growing' ? 'wealthness.growing' : 'wealthness.decliningPlain', {
      subject,
    });
  }
  return t(direction === 'growing' ? 'wealthness.grew' : 'wealthness.declined', {
    subject,
    pct: fmtPercent(Math.abs(change_pct)),
  });
}

/** One metric: name, figure, the reasoning, and the band. */
function MetricRow({
  name,
  value,
  note,
  status,
  strong,
}: {
  name: string;
  value: React.ReactNode;
  note: string;
  status: MetricStatus;
  /** The first row opens the block, so it carries the heavy rule. */
  strong?: boolean;
}) {
  return (
    <div
      className={`grid grid-cols-1 items-center gap-4 border-t py-5 md:grid-cols-[210px_170px_1fr_140px] md:gap-6 ${
        strong ? 'rule-strong' : 'border-border'
      }`}
    >
      <div className="fig text-[19px] font-medium">{name}</div>
      <div className="fig text-[30px] font-medium">{value}</div>
      <p className="m-0 text-sm leading-relaxed text-inksoft">{note}</p>
      <div className="md:text-right">
        <StatusBadge status={status} />
      </div>
    </div>
  );
}

export default function Wealthness() {
  const { t } = useTranslation();
  const [months, setMonths] = useState(12);
  const [data, setData] = useState<WealthnessOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const palette = useChartPalette();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await wealthnessApi.overview(months));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [months]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !data) {
    return <p className="text-sm text-muted-foreground">{t('wealthness.loading')}</p>;
  }
  if (error) {
    return <p className="border border-error/40 bg-lighterror p-4 text-sm text-error">{error}</p>;
  }
  if (!data) return null;

  const base = data.base_currency;
  const { emergency_fund: fund, savings_rate: savings, debt_load: debt, net_worth: worth } = data;
  const series: NetFlowPoint[] = data.net_flow.series;

  return (
    <div className="flex flex-col gap-9">
      <ConversionNotice report={data.conversion} baseCurrency={base} />

      <PageHeader
        eyebrow={t('wealthness.eyebrow', {
          from: fmtMonth(data.period.from),
          to: fmtMonth(data.period.to),
        })}
        title={headlineFor(data, t)}
        description={
          `${trendNote(data.trend.basis, data.trend.note)} ` +
          `${metricNote('savingsRate', savings.status, savings.note)} ` +
          `${metricNote('emergencyFund', fund.status, fund.note)}`
        }
        actions={
          <div className="flex flex-col items-end gap-4">
            <BaseCurrencyBadge currency={base} />
            <div className="flex border border-input">
              {WINDOWS.map((w) => (
                <button
                  key={w}
                  type="button"
                  onClick={() => setMonths(w)}
                  className={`px-3 py-1.5 text-xs transition-colors ${
                    months === w
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {t('wealthness.window', { count: w })}
                </button>
              ))}
            </div>
          </div>
        }
      />

      {/* Net worth, stated once at full size — everything below explains it. */}
      <div className="flex flex-wrap items-end justify-between gap-6 border-t rule-strong pt-6">
        <div>
          <div className="eyebrow-sm mb-3">{t('patrimony.netWorth')}</div>
          <div className="fig text-[42px] font-medium leading-none">
            {fmtFigure(worth.current, base)}
          </div>
          <div className="mt-3 text-[13px] text-inksoft">
            {t('wealthness.assetsMinusDebt', {
              assets: fmtFigure(worth.total_assets, base),
              debt: fmtFigure(worth.total_liabilities, base),
            })}
          </div>
        </div>
        {data.trend.change_pct !== null && (
          <div className="text-right">
            <div className="eyebrow-sm mb-3">{t('wealthness.periodChange')}</div>
            <Figure
              className="text-[26px] font-medium"
              tone={data.trend.direction === 'declining' ? 'expense' : 'income'}
            >
              {fmtSignedPercent(data.trend.change_pct)}
            </Figure>
            <div className="mt-2 text-xs text-muted-foreground">
              {trendNote(data.trend.basis, data.trend.note)}
            </div>
          </div>
        )}
      </div>

      {/* The three judged metrics */}
      <div>
        <MetricRow
          strong
          name={t('wealthness.savingsRate')}
          value={savings.value === null ? <span className="text-secondary">—</span> : fmtPercent(savings.value)}
          note={metricNote('savingsRate', savings.status, savings.note)}
          status={savings.status}
        />
        <MetricRow
          name={t('wealthness.emergencyFund')}
          value={
            fund.months_covered === null ? (
              <span className="text-secondary">—</span>
            ) : (
              <>
                {fmtNumber(fund.months_covered)}{' '}
                <span className="text-base text-muted-foreground">{t('common.months')}</span>
              </>
            )
          }
          note={
            fund.months_covered === null
              ? metricNote('emergencyFund', fund.status, fund.note)
              : `${metricNote('emergencyFund', fund.status, fund.note)} ${t(
                  'wealthness.fundDetail',
                  {
                    liquid: fmtFigure(fund.liquid_assets, base),
                    monthly: fmtFigure(fund.avg_monthly_essentials, base),
                  },
                )}`
          }
          status={fund.status}
        />
        <MetricRow
          name={t('wealthness.debtLoad')}
          value={
            debt.debt_to_income === null ? (
              <span className="text-secondary">—</span>
            ) : (
              fmtPercent(debt.debt_to_income)
            )
          }
          note={metricNote('debtLoad', debt.status, debt.note)}
          status={debt.status}
        />
        <div className="border-b border-border" />
      </div>

      {/* Monthly net flow */}
      <div>
        <div className="mb-4 flex items-baseline justify-between">
          <div className="fig text-[19px] font-medium">{t('wealthness.monthlyNetFlow')}</div>
          <div className="flex gap-5 text-[13px] text-inksoft">
            <span className="flex items-center gap-2">
              <span className="h-0.5 w-5" style={{ background: palette.income }} />
              {t('dashboard.income')}
            </span>
            <span className="flex items-center gap-2">
              <span className="h-0.5 w-5" style={{ background: palette.expense }} />
              {t('dashboard.expenses')}
            </span>
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-5" style={{ background: palette.brand }} />
              {t('dashboard.net')}
            </span>
          </div>
        </div>

        {series.length === 0 ? (
          <p className="border border-input bg-card p-6 text-sm text-inksoft">
{t('wealthness.noSnapshots')}
          </p>
        ) : (
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={series} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
                <CartesianGrid stroke={palette.rule} vertical={false} />
                <XAxis
                  dataKey="month"
                  tickFormatter={shortMonthTick}
                  tick={{ fill: palette.mutedText, fontSize: 11 }}
                  axisLine={{ stroke: palette.ink }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: palette.mutedText, fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  width={70}
                  tickFormatter={(v: number) => fmtFigure(v, base)}
                />
                <Tooltip
                  formatter={moneyTooltipFormatter(base)}
                  labelFormatter={monthLabelFormatter}
                  contentStyle={tooltipStyle}
                />
                <Bar dataKey="net" name="Neto" fill={palette.brand} maxBarSize={34} />
                <Line
                  type="linear"
                  dataKey="income"
                  name="Ingresos"
                  stroke={palette.income}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="linear"
                  dataKey="expenses"
                  name="Gastos"
                  stroke={palette.expense}
                  strokeWidth={2}
                  strokeDasharray="5 4"
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <p className="m-0 max-w-[78ch] text-[13px] italic leading-relaxed text-muted-foreground">
{t('wealthness.footnote')}
      </p>
    </div>
  );
}
