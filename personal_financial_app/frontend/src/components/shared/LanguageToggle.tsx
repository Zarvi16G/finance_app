/**
 * Interface language switcher, next to the theme toggle in the header.
 *
 * The choice is stored per device (localStorage, via the detector), the same
 * way the theme is: it is a reading preference, not account data, and someone
 * signing in on a borrowed machine should not have their language follow them
 * there.
 */
import { useTranslation } from 'react-i18next';
import { LANGUAGES } from '../../i18n';

export default function LanguageToggle() {
  const { i18n, t } = useTranslation();
  const current = i18n.resolvedLanguage ?? 'es';

  return (
    <div className="flex border border-input" role="group" aria-label={t('common.language')}>
      {LANGUAGES.map((lang) => (
        <button
          key={lang.code}
          type="button"
          onClick={() => i18n.changeLanguage(lang.code)}
          aria-pressed={current === lang.code}
          title={lang.label}
          className={`px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] transition-colors ${
            current === lang.code
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          {lang.code}
        </button>
      ))}
    </div>
  );
}
