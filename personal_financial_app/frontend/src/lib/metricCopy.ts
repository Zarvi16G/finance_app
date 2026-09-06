/**
 * Wording for the Wealthness metric bands.
 *
 * The backend sends a note with every metric, in English, written for the
 * service layer rather than for this UI — and one API should not hold the
 * copy for every language a client might read in. So the note is looked up
 * from the dictionary by the band's status code, which is a small stable
 * enum, and the server's own sentence is the fallback when a band has no
 * entry yet.
 */
import i18n from '../i18n';
import type { MetricStatus } from '../types';

export type MetricKey = 'savingsRate' | 'emergencyFund' | 'debtLoad';

/** The note for a metric's band, or the backend's own note. */
export function metricNote(metric: MetricKey, status: MetricStatus, fallback: string): string {
  return i18n.t(`metrics.${metric}.${status}`, { defaultValue: fallback });
}

/** The note explaining what the trend was measured on. */
export function trendNote(basis: string | null, fallback: string): string {
  if (!basis) return fallback;
  return i18n.t(`metrics.trend.${basis}`, { defaultValue: fallback });
}
