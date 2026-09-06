/**
 * The status of a Wealthness metric, rendered as an underlined uppercase word.
 *
 * The mapping from the backend's band to a colour lives here and nowhere
 * else, so the same band always reads the same way across the dashboard, the
 * Wealthness page and anywhere else it surfaces. The word itself comes from
 * the dictionary, keyed by the same band.
 *
 * `unknown` is not an error state and is not red: it means the backend
 * declined to guess. It gets the faint tone, and the screens that show it
 * pair it with a sentence saying what is missing.
 */
import { useTranslation } from 'react-i18next';
import { cn } from '../../lib/utils';
import type { MetricStatus } from '../../types';

/** Green for a good band, amber for the middle, red for one needing action. */
const TONES: Record<MetricStatus, string> = {
  strong: 'text-success border-success',
  adequate: 'text-warning border-warning',
  healthy: 'text-success border-success',
  low: 'text-warning border-warning',
  high: 'text-error border-error',
  critical: 'text-error border-error',
  unknown: 'text-secondary border-secondary',
};

export default function StatusBadge({
  status,
  label,
  className,
}: {
  status: MetricStatus;
  /** Override the word, for a metric whose band reads oddly in context. */
  label?: string;
  className?: string;
}) {
  const { t } = useTranslation();
  const tone = TONES[status] ?? TONES.unknown;
  return (
    <span
      className={cn(
        'inline-block border-b-2 pb-0.5 text-[11px] font-semibold uppercase tracking-[0.06em]',
        tone,
        className,
      )}
    >
      {label ?? t(`status.${status}`, status)}
    </span>
  );
}
