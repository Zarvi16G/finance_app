/**
 * PageHeader — the letterhead every Ledgerline page opens with:
 * a mono uppercase eyebrow naming the statement type, a Gloock
 * serif title, one sentence of purpose, and a hairline rule.
 * Actions sit on the right like a "return this form" note.
 */
import type { ReactNode } from 'react';

export default function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="border-b border-border pb-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="letterhead">{eyebrow}</p>
          <h1 className="font-display text-3xl font-normal tracking-tight text-foreground md:text-4xl">
            {title}
          </h1>
          {description && (
            <p className="mt-1.5 max-w-xl text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
}