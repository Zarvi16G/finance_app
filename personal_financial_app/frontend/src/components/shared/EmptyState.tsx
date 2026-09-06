/**
 * What a screen shows when the backend answered `unknown` or returned nothing.
 *
 * The rule from the design's "Estados sin datos" board: a missing figure is
 * named as missing. It is never filled with a zero that would look like a
 * measurement, nor with a dash that would look like the app broke. So this
 * component always states three things — that the value is undetermined, why,
 * and what the user can do about it.
 */
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { cn } from '../../lib/utils';

export default function EmptyState({
  label,
  headline = 'Sin determinar',
  explanation,
  action,
  visual,
  className,
}: {
  /** The metric this stands in for, e.g. "Fondo de emergencia". */
  label: string;
  headline?: string;
  /** Why it cannot be measured yet — in the user's terms, not the API's. */
  explanation: ReactNode;
  action?: { label: string; to: string } | { label: string; onClick: () => void };
  visual?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-col gap-3.5 border border-input bg-card p-6', className)}>
      <div className="eyebrow-sm">{label}</div>
      <div className="fig text-[30px] font-medium text-secondary">{headline}</div>
      {visual}
      <p className="m-0 text-sm leading-relaxed text-inksoft">{explanation}</p>
      {action && (
        <div className="mt-auto border-t border-border pt-2.5">
          {'to' in action ? (
            <Link to={action.to} className="text-[13px] font-semibold text-primary hover:underline">
              {action.label}
            </Link>
          ) : (
            <button
              type="button"
              onClick={action.onClick}
              className="text-[13px] font-semibold text-primary hover:underline"
            >
              {action.label}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

