/**
 * "Totales en COP" — the marker that appears in the corner of every screen
 * showing aggregated money.
 *
 * It exists because the app holds amounts in several currencies at once and
 * converts them for display. A total with no stated currency is ambiguous in
 * a way that a total in a single-currency app never is, so the design puts
 * this on every screen that adds anything up.
 */
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

export default function BaseCurrencyBadge({ currency }: { currency: string | undefined }) {
  const { t } = useTranslation();
  return (
    <Link
      to="/perfil"
      title={t('currency.changeInProfile')}
      className="flex items-center gap-2.5 border border-input px-3.5 py-2 transition-colors hover:border-primary"
    >
      <span className="text-xs text-muted-foreground">{t('currency.totalsIn')}</span>
      <span className="fig text-sm font-semibold text-foreground">{currency ?? '—'}</span>
    </Link>
  );
}
