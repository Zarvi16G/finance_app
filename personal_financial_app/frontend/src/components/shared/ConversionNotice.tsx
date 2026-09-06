/**
 * The banner a screen shows when its totals had to leave something out.
 *
 * The backend now excludes an amount it cannot convert rather than adding it
 * unconverted, which means a total is never in the wrong currency — but it
 * can be understated. That is only honest if the screen says so, otherwise
 * the user reads a smaller number and has no way to know why.
 *
 * It renders nothing when the conversion was complete, which is the normal
 * case, so screens can drop it in unconditionally.
 */
import { useTranslation } from 'react-i18next';
import { Icon } from '@iconify/react';
import { fmtMonth } from '../../lib/money';
import type { ConversionReport } from '../../types';

export default function ConversionNotice({
  report,
  baseCurrency,
}: {
  report: ConversionReport | undefined;
  baseCurrency: string;
}) {
  const { t } = useTranslation();
  if (!report || report.complete) return null;

  const currencies = report.unconvertible_currencies;
  const months = report.partial_months ?? [];

  return (
    <div className="flex items-start gap-3.5 border border-warning/50 bg-lightwarning px-4 py-3.5">
      <Icon
        icon="solar:danger-triangle-linear"
        height={18}
        width={18}
        className="mt-0.5 shrink-0 text-warning"
      />
      <div className="min-w-0">
        <div className="text-sm font-semibold">{t('conversion.title')}</div>
        {currencies.length > 0 && (
          <p className="m-0 mt-1 text-sm leading-relaxed text-inksoft">
            {t('conversion.body', {
              currencies: currencies.join(', '),
              base: baseCurrency,
            })}
          </p>
        )}
        {months.length > 0 && (
          <p className="m-0 mt-1.5 text-sm leading-relaxed text-inksoft">
            {t('conversion.partialMonths', {
              months: months.map((m) => fmtMonth(m)).join(', '),
            })}
          </p>
        )}
        <p className="m-0 mt-1.5 text-[13px] text-muted-foreground">{t('conversion.fix')}</p>
      </div>
    </div>
  );
}
