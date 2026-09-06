/**
 * Formatters for Recharts tooltips and axes.
 *
 * Recharts types a tooltip value as `ValueType | undefined` and a label as
 * `ReactNode`, so the callbacks have to accept those wide types and narrow
 * inside. Keeping that narrowing here means the chart components stay
 * readable and every chart in the app formats money the same way.
 */
import { fmtFigure, fmtMonth } from './money';

/** `[formatted amount, series name]`, in the given currency. */
export const moneyTooltipFormatter =
  (currency: string) =>
  (value: unknown, name: unknown): [string, string] => [
    fmtFigure(typeof value === 'number' || typeof value === 'string' ? value : 0, currency),
    String(name ?? ''),
  ];

/** A `2027-04` tick or tooltip label as `abr 2027`. */
export const monthLabelFormatter = (label: unknown): string =>
  fmtMonth(typeof label === 'string' ? label : undefined);

/** Just the month name, for a crowded axis: `abr`. */
export const shortMonthTick = (label: unknown): string =>
  monthLabelFormatter(label).split(' ')[0];

/** The tooltip's own styling, so it reads as part of the page. */
export const tooltipStyle = {
  background: 'var(--card)',
  border: '1px solid var(--input)',
  borderRadius: 0,
  fontSize: 13,
} as const;
