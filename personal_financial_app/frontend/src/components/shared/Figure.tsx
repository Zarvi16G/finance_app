/**
 * Figures and their labels — the two elements every screen in the design is
 * built out of.
 *
 * A `Figure` is any number set in Newsreader with tabular numerals.
 *
 * The `tone` prop is the one place the money-colour rule is enforced: an
 * amount may be neutral, income green or expense red, and nothing else.
 * Amber ("intermediate") is deliberately not available here — it belongs to
 * a metric's status band, never to a sum of money.
 */
import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

export type FigureTone = 'neutral' | 'income' | 'expense' | 'brand' | 'faint';

const TONE_CLASS: Record<FigureTone, string> = {
  neutral: 'text-foreground',
  income: 'text-success',
  expense: 'text-error',
  brand: 'text-primary',
  faint: 'text-secondary',
};

export function Figure({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode;
  tone?: FigureTone;
  className?: string;
}) {
  return <span className={cn('fig', TONE_CLASS[tone], className)}>{children}</span>;
}

