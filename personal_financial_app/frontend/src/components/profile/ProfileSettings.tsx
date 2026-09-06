/**
 * Perfil y seguridad — identity, base currency, the second factor, and the
 * vocabulary of categories and types.
 *
 * The base currency is the setting with the widest reach: it decides the
 * currency every total on every other screen is read in. The copy next to it
 * says the thing that is easy to get wrong — each movement keeps the currency
 * it actually happened in, and the conversion is computed when it is
 * displayed, never written over the original amount.
 */
import { useEffect, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import PageHeader from '../shared/PageHeader';
import TwoFactorSection from './TwoFactorSection';
import { SettingsPanel } from './AiSettingsPanel';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { profileApi } from '../../api/profile';
import { currencyApi } from '../../api/currency';
import { getErrorMessage } from '../../api/client';
import type { Currency, ProfileSettings as ProfileSettingsType, TwoFactorStatus } from '../../types';

export default function ProfileSettings() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<ProfileSettingsType | null>(null);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [identity, setIdentity] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone_number: '',
  });
  const [currency, setCurrency] = useState('COP');
  const [newType, setNewType] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [newCategoryType, setNewCategoryType] = useState('expense');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const adopt = (data: ProfileSettingsType) => {
    setSettings(data);
    setCurrency(data.currency);
    setIdentity({
      first_name: data.first_name ?? '',
      last_name: data.last_name ?? '',
      email: data.email ?? '',
      phone_number: data.phone_number ?? '',
    });
  };

  useEffect(() => {
    profileApi.get().then(adopt).catch((err) => setError(getErrorMessage(err)));
    currencyApi
      .catalog()
      .then((c) => setCurrencies(c.currencies))
      .catch(() => setCurrencies([]));
  }, []);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError('');
    try {
      adopt(
        await profileApi.update({
          ...identity,
          currency,
          new_type: newType,
          new_category: newCategory,
          new_category_type: newCategoryType,
        }),
      );
      setNewType('');
      setNewCategory('');
      setSaved(true);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const onTwoFactorChanged = (status: TwoFactorStatus) =>
    setSettings((s) => (s ? { ...s, two_factor: status } : s));

  if (!settings) {
    return error ? (
      <p className="border border-error/40 bg-lighterror p-4 text-sm text-error">{error}</p>
    ) : (
      <p className="text-sm text-muted-foreground">{t('profile.loading')}</p>
    );
  }

  // The phone the user is currently editing may differ from the saved one; the
  // verification badge describes what is stored, not what is typed.
  const phoneChanged = identity.phone_number !== (settings.phone_number ?? '');

  return (
    <div className="flex flex-col gap-8">
      <PageHeader eyebrow={t('profile.eyebrow')} title={t('profile.title')} />

      {error && <p className="bg-lighterror px-3 py-2 text-sm text-error">{error}</p>}

      <form onSubmit={save} className="flex flex-col gap-8">
        {/* Identity + base currency */}
        <div className="grid gap-11 border-t rule-strong pt-6 lg:grid-cols-2">
          <div>
            <div className="fig mb-4 text-[19px] font-medium">{t('profile.personalDetails')}</div>
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="p-first">{t('profile.firstName')}</Label>
                  <Input
                    id="p-first"
                    className="mt-2"
                    value={identity.first_name}
                    onChange={(e) => setIdentity({ ...identity, first_name: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="p-last">{t('profile.lastName')}</Label>
                  <Input
                    id="p-last"
                    className="mt-2"
                    value={identity.last_name}
                    onChange={(e) => setIdentity({ ...identity, last_name: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <Label htmlFor="p-email">{t('profile.email')}</Label>
                <Input
                  id="p-email"
                  type="email"
                  className="mt-2"
                  value={identity.email}
                  onChange={(e) => setIdentity({ ...identity, email: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="p-phone">{t('profile.phone')}</Label>
                <div className="mt-2 flex items-center gap-3">
                  <Input
                    id="p-phone"
                    type="tel"
                    className="flex-grow"
                    value={identity.phone_number}
                    onChange={(e) => setIdentity({ ...identity, phone_number: e.target.value })}
                    placeholder={t('profile.phonePlaceholder')}
                  />
                  {identity.phone_number && !phoneChanged && (
                    <span
                      className={`shrink-0 text-xs ${
                        settings.phone_verified ? 'text-success' : 'text-warning'
                      }`}
                    >
                      {t(settings.phone_verified ? 'profile.verified' : 'profile.unverified')}
                    </span>
                  )}
                </div>
                <p className="m-0 mt-2 text-xs leading-relaxed text-muted-foreground">
                  {t('profile.phoneNote')}
                </p>
              </div>
            </div>
          </div>

          <div className="lg:border-l lg:border-border lg:pl-11">
            <div className="fig mb-4 text-[19px] font-medium">{t('profile.baseCurrency')}</div>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger id="p-currency" className="h-auto py-3">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(currencies.length
                  ? currencies
                  : [{ code: currency, name: currency, symbol: '', decimals: 2 }]
                ).map((c) => (
                  <SelectItem key={c.code} value={c.code}>
                    <span className="fig font-semibold">{c.code}</span>
                    <span className="ml-3 text-inksoft">{c.name}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="m-0 mt-3 text-sm leading-relaxed text-inksoft">
              {t('profile.baseCurrencyNote')}
            </p>
            <p className="m-0 mt-3.5 text-[13px] leading-relaxed text-muted-foreground">
              {t('profile.ratesNote')}
            </p>
          </div>
        </div>

        {/* Vocabulary */}
        <div className="grid gap-11 border-t rule-strong pt-6 lg:grid-cols-2">
          <div>
            <div className="fig mb-4 text-[19px] font-medium">{t('profile.vocabulary')}</div>
            <div className="flex flex-col gap-4">
              <div>
                <Label htmlFor="p-type">{t('profile.addType')}</Label>
                <Input
                  id="p-type"
                  className="mt-2"
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  placeholder={t('profile.addTypePlaceholder')}
                />
              </div>
              <div>
                <Label htmlFor="p-cat">{t('profile.addCategory')}</Label>
                <div className="mt-2 flex flex-wrap gap-3">
                  <Input
                    id="p-cat"
                    className="min-w-[180px] flex-grow"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    placeholder={t('profile.addCategoryPlaceholder')}
                  />
                  <Select value={newCategoryType} onValueChange={setNewCategoryType}>
                    <SelectTrigger className="w-36">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="expense">{t('profile.expense')}</SelectItem>
                      <SelectItem value="income">{t('profile.income')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:border-l lg:border-border lg:pl-11">
            <div className="eyebrow-sm mb-3">{t('profile.categories')}</div>
            <div className="flex flex-wrap gap-2">
              {settings.categories.map((cat) => (
                <Badge key={`${cat.id ?? 'builtin'}-${cat.type}-${cat.name}`} variant="gray">
                  {cat.name}
                  <span className="ml-1 text-xs opacity-70">
                    ({t(cat.type === 'income' ? 'profile.income' : 'profile.expense')})
                  </span>
                </Badge>
              ))}
            </div>
            <div className="eyebrow-sm mb-3 mt-5">{t('profile.types')}</div>
            <div className="flex flex-wrap gap-2">
              {settings.types.map((t) => (
                <Badge key={`${t.id ?? 'builtin'}-${t.name}`} variant="gray">
                  {t.name}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Button type="submit" disabled={saving}>
            {saving ? t('common.saving') : t('common.saveChanges')}
          </Button>
          {saved && <span className="text-sm text-success">{t('common.saved')}</span>}
        </div>
      </form>

      <TwoFactorSection status={settings.two_factor} onChanged={onTwoFactorChanged} />

      {/* AI assistant */}
      <section className="border-t rule-strong pt-6">
        <div className="fig mb-1.5 text-[19px] font-medium">{t('profile.aiAssistant')}</div>
        <p className="m-0 mb-5 max-w-[72ch] text-sm leading-relaxed text-inksoft">
          {t('profile.aiNote')}
        </p>
        <SettingsPanel />
      </section>
    </div>
  );
}
