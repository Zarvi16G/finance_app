/**
 * Spanish wording for the Wealthness metrics.
 *
 * The backend already sends a note with every metric, but in English — its
 * band tables are written for the service layer, not for this UI, and one API
 * should not have to hold the copy for every locale a client might use.
 *
 * The mapping keys off the status code, which is a small stable enum, rather
 * than off the English sentence, which is prose and will drift. Anything not
 * mapped falls through to whatever the backend sent, so a new band added
 * server-side shows up as English rather than as a blank.
 */
import type { MetricStatus } from '../types';

type Notes = Partial<Record<MetricStatus, string>>;

const SAVINGS_RATE: Notes = {
  strong: 'Conservas una quinta parte o más de lo que ingresas.',
  adequate: 'Conservas entre una décima y una quinta parte.',
  low: 'Conservas menos de una décima parte.',
  unknown: 'No hay ingresos registrados en este periodo.',
};

const EMERGENCY_FUND: Notes = {
  strong: 'Seis meses o más de gastos esenciales cubiertos.',
  adequate: 'Entre tres y seis meses cubiertos: el objetivo habitual.',
  low: 'Menos de tres meses. Un solo contratiempo dolería.',
  critical: 'Menos de un mes de cobertura.',
  unknown: 'Todavía no hay gastos registrados contra los que medir.',
};

const DEBT_LOAD: Notes = {
  healthy: 'Por debajo del 36 % que la banca considera cómodo.',
  high: 'Por encima de la línea habitual de comodidad, el 36 %.',
  critical: 'Por encima de lo que la mayoría de prestamistas acepta.',
  unknown: 'Hace falta una instantánea mensual con ingresos.',
};

const TREND: Record<string, string> = {
  net_worth: 'Medido sobre patrimonio neto.',
  net_flow: 'Sin activos registrados, medido sobre el flujo neto acumulado.',
};

const TABLES = {
  savings_rate: SAVINGS_RATE,
  emergency_fund: EMERGENCY_FUND,
  debt_load: DEBT_LOAD,
} as const;

export type MetricKey = keyof typeof TABLES;

/** The Spanish note for a metric's band, or the backend's own note. */
export function metricNote(metric: MetricKey, status: MetricStatus, fallback: string): string {
  return TABLES[metric][status] ?? fallback;
}

/** The Spanish note explaining what the trend was measured on. */
export function trendNote(basis: string | null, fallback: string): string {
  return (basis && TREND[basis]) || fallback;
}
