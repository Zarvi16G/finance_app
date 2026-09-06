/**
 * The heading every page opens with: an uppercase eyebrow naming the section,
 * a Newsreader title, and optionally one sentence of purpose. Actions and the
 * base-currency marker sit on the right.
 *
 * There is no rule under it — in this design the rule belongs to the first
 * block of content, which is what it is separating the header from.
 */
import type { ReactNode } from 'react';

export default function PageHeader({
  eyebrow,
  title,
  description,
  meta,
  actions,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  /** A row under the title — dates, a location, whatever names the subject. */
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="letterhead mb-3">{eyebrow}</p>
        <h1 className="fig m-0 text-[30px] font-medium leading-tight md:text-[34px]">{title}</h1>
        {description && (
          <p className="mt-3.5 max-w-[56ch] text-[15px] leading-relaxed text-inksoft">
            {description}
          </p>
        )}
        {meta && <div className="mt-3 flex flex-wrap gap-4 text-sm text-inksoft">{meta}</div>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-3">{actions}</div>}
    </header>
  );
}
