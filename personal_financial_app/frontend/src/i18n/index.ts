/**
 * Interface language: Spanish and English.
 *
 * Spanish is the fallback, not English — this app was designed in Spanish and
 * its copy is the original rather than a translation, so an untranslated key
 * should fall back to the text that was actually written for the screen.
 *
 * What lives here is *interface* copy. What does not, and deliberately:
 *
 *   - Category and type names. Those are user data — some seeded, some typed
 *     by the person using the app — and translating a value the user chose
 *     would mean showing them a word they did not write.
 *   - Currency codes and amounts. `es-CO` number formatting is a property of
 *     the currency, not of the reading language: a peso figure is grouped
 *     the same way whoever is looking at it.
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import es from './es.json';
import en from './en.json';

export const LANGUAGES = [
  { code: 'es', label: 'Español' },
  { code: 'en', label: 'English' },
] as const;

export type LanguageCode = (typeof LANGUAGES)[number]['code'];

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      es: { translation: es },
      en: { translation: en },
    },
    fallbackLng: 'es',
    supportedLngs: LANGUAGES.map((l) => l.code),
    // A stored choice wins; otherwise follow the browser. Nothing is read
    // from the URL or a cookie, so the setting is per device and survives a
    // reload without appearing in shareable links.
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'ui-language',
      caches: ['localStorage'],
    },
    interpolation: { escapeValue: false },
  });

export default i18n;
