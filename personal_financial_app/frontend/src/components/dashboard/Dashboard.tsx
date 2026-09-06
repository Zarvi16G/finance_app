/**
 * Dashboard — the one screen that answers "how am I doing" without asking the
 * user to choose a period or a lens first.
 *
 * It reads two aggregate endpoints and nothing else: /wealthness/ for the
 * flow series and the health bands, /patrimony/ for net worth. Both already
 * return figures converted to the base currency, so this component never
 * adds two amounts together — which is exactly the mistake a multi-currency
 * dashboard is prone to.
 *
 * Categories come from /analytics/, which is snapshot-backed.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Icon } from '@iconify/react';
import PageHeader from '../shared/PageHeader';
import BaseCurrencyBadge from '../shared/BaseCurrencyBadge';
import StatusBadge from '../shared/StatusBadge';
import { Figure } from '../shared/Figure';
import { wealthnessApi } from '../../api/wealthness';
import { analyticsApi } from '../../api/ai';
import { getErrorMessage } from '../../api/client';
import { useChartPalette } from '../../lib/chartColors';
import { fmtFigure, fmtNumber, fmtPercent, fmtSigned, fmtSignedPercent } from '../../lib/money';
import {
  moneyTooltipFormatter,
  monthLabelFormatter,
  shortMonthTick,
  tooltipStyle,
} from '../../lib/chartFormat';
import { useAuth } from '../../auth/AuthContext';
import type { DashboardData, WealthnessOverview } from '../../types';

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Buenos días';
  if (hour < 19) return 'Buenas tardes';
  return 'Buenas noches';
}

const currentMonthLabel = () => {
  const label = new Date().toLocaleDateString('es-CO', { month: 'long', year: 'numeric' });
  return label.charAt(0).toUpperCase() + label.slice(1);
};

/** One figure in the top strip, separated by a hairline from the next. */
function StripCell({
  label,
  children,
  className = '',
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`px-6 py-6 ${className}`}>
      <div className="eyebrow-sm mb-3">{label}</div>
      {children}
    </div>
  );
}

/** One metric in the health strip along the bottom. */
function HealthCell({
  label,
  value,
  status,
  unknownNote,
}: {
  label: string;
  value: string | null;
  status: WealthnessOverview['savings_rate']['status'];
  unknownNote: string;
}) {
  return (
    <div>
      <div className="eyebrow-sm mb-2.5">{label}</div>
      {value === null ? (
        <div>
          <span className="fig text-[23px] font-medium text-secondary">Sin determinar</span>
          <p className="mt-1.5 max-w-[34ch] text-xs leading-relaxed text-muted-foreground">
            {unknownNote}
          </p>
        </div>
      ) : (
        <div className="flex flex-wrap items-baseline gap-2.5">
          <span className="fig text-[23px] font-medium">{value}</span>
          <StatusBadge status={status} />
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [health, setHealth] = useState<WealthnessOverview | null>(null);
  const [analytics, setAnalytics] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const palette = useChartPalette();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [overview, dash] = await Promise.all([
          wealthnessApi.overview(12),
          // The category breakdown is a nice-to-have: if it fails the rest of
          // the page is still worth rendering.
          analyticsApi.dashboard().catch(() => null),
        ]);
        if (cancelled) return;
        setHealth(overview);
        setAnalytics(dash);
      } catch (err) {
        if (!cancelled) setError(getErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando tu resumen…</p>;
  if (error || !health) {
    return (
      <p className="border border-error/40 bg-lighterror p-4 text-sm text-error">
        {error ?? 'No se pudo cargar el resumen.'}
      </p>
    );
  }

  const base = health.base_currency;
  const series = health.net_flow.series;
  const latest = series.at(-1);
  const categories = (analytics?.expense_by_category ?? []).slice(0, 4);
  const categoryMax = categories[0]?.total ?? 0;
  // Greet by first name when there is one; the username is the fallback, not
  // the preference.
  const displayName = user?.first_name?.trim() || user?.username || '';

  return (
    <div className="flex flex-col gap-9">
      <PageHeader
        eyebrow={currentMonthLabel()}
        title={displayName ? `${greeting()}, ${displayName}.` : `${greeting()}.`}
        actions={<BaseCurrencyBadge currency={base} />}
      />

      {/* Net worth and the month's three figures */}
      <div className="grid border-y rule-strong border-b-border md:grid-cols-[1.35fr_1fr_1fr_1fr]">
        <StripCell label="Patrimonio neto" className="pl-0 md:border-r md:border-border">
          <div className="fig text-[42px] font-medium leading-none">
            {fmtFigure(health.net_worth.current, base)}
          </div>
          {health.trend.change_pct !== null && (
            <div className="mt-3 flex items-center gap-2">
              <Icon
                icon={
                  health.trend.direction === 'declining'
                    ? 'solar:arrow-right-down-linear'
                    : 'solar:arrow-right-up-linear'
                }
                height={13}
                width={13}
                className={health.trend.direction === 'declining' ? 'text-error' : 'text-success'}
              />
              <span
                className={`text-[13px] font-semibold ${
                  health.trend.direction === 'declining' ? 'text-error' : 'text-success'
                }`}
              >
                {fmtSignedPercent(health.trend.change_pct)} en {health.period.months} meses
              </span>
            </div>
          )}
        </StripCell>

        <StripCell label="Ingresos del mes" className="md:border-r md:border-border">
          <Figure tone="income" className="text-[26px] font-medium">
            {latest ? fmtFigure(latest.income, base) : '—'}
          </Figure>
        </StripCell>

        <StripCell label="Gastos del mes" className="md:border-r md:border-border">
          <Figure tone="expense" className="text-[26px] font-medium">
            {latest ? fmtFigure(latest.expenses, base) : '—'}
          </Figure>
        </StripCell>

        <StripCell label="Flujo neto" className="pr-0">
          <Figure className="text-[26px] font-medium">
            {latest ? fmtSigned(latest.net, base) : '—'}
          </Figure>
        </StripCell>
      </div>

      {/* Flow chart and where the money went */}
      <div className="grid gap-11 lg:grid-cols-[1.6fr_1fr]">
        <div>
          <div className="mb-5 flex items-baseline justify-between">
            <div className="fig text-[19px] font-medium">Ingresos y gastos</div>
            <div className="flex gap-5 text-xs text-inksoft">
              <span className="flex items-center gap-2">
                <span className="h-0.5 w-5" style={{ background: palette.income }} />
                Ingresos
              </span>
              <span className="flex items-center gap-2">
                <span className="h-0.5 w-5" style={{ background: palette.expense }} />
                Gastos
              </span>
            </div>
          </div>

          {series.length === 0 ? (
            <p className="border border-input bg-card p-6 text-sm text-inksoft">
              Aún no hay meses cerrados que dibujar. Las instantáneas mensuales se generan a partir
              de tus movimientos.{' '}
              <Link to="/movimientos" className="font-semibold text-primary hover:underline">
                Registrar movimientos
              </Link>
            </p>
          ) : (
            <div className="h-[230px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
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
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div>
          <div className="fig mb-5 text-[19px] font-medium">Gasto por categoría</div>
          {categories.length === 0 ? (
            <p className="text-sm text-inksoft">Sin gastos categorizados en el periodo.</p>
          ) : (
            <div className="flex flex-col gap-4">
              {categories.map((row, i) => (
                <div key={row.category} className="flex flex-col gap-2">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="truncate text-sm">{row.category}</span>
                    <span className="fig shrink-0 text-[15px]">{fmtFigure(row.total, base)}</span>
                  </div>
                  <div className="h-1.5 bg-muted">
                    <div
                      className="h-1.5"
                      style={{
                        // Bars are shaded by rank, not by hue: they are all
                        // expenses, so a colour difference would be lying.
                        width: categoryMax ? `${(row.total / categoryMax) * 100}%` : '0%',
                        background: palette.ink,
                        opacity: 1 - i * 0.22,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Health strip */}
      <div className="grid gap-8 border-t rule-strong pt-6 md:grid-cols-4">
        <HealthCell
          label="Tasa de ahorro"
          value={health.savings_rate.value === null ? null : fmtPercent(health.savings_rate.value)}
          status={health.savings_rate.status}
          unknownNote="No hay ingresos registrados en el periodo."
        />
        <HealthCell
          label="Fondo de emergencia"
          value={
            health.emergency_fund.months_covered === null
              ? null
              : `${fmtNumber(health.emergency_fund.months_covered)} meses`
          }
          status={health.emergency_fund.status}
          unknownNote="Sin gastos registrados no hay contra qué medir tus activos líquidos."
        />
        <HealthCell
          label="Deuda / ingreso"
          value={
            health.debt_load.debt_to_income === null
              ? null
              : fmtPercent(health.debt_load.debt_to_income)
          }
          status={health.debt_load.status}
          unknownNote="Hace falta una instantánea mensual con ingresos."
        />
        <div className="flex items-end md:justify-end">
          <Link
            to="/wealthness"
            className="flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
          >
            Ver salud financiera
            <Icon icon="solar:arrow-right-linear" height={14} width={14} />
          </Link>
        </div>
      </div>
    </div>
  );
}
