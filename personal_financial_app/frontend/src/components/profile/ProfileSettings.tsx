/**
 * Profile settings page: currency preference
 plus custom category/type vocabulary
 (Choice) management with AI-key setup.
 */
import { useEffect, useState, type FormEvent } from 'react';
import CardBox from '../shared/CardBox';
import PageHeader from '../shared/PageHeader';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Badge } from '../ui/badge';
import { profileApi } from '../../api/profile';
import { exchangeRatesApi } from '../../api/exchangeRates';
import { aiApi } from '../../api/ai';
import { getErrorMessage } from '../../api/client';
import { useProfileCurrency } from '../../hooks/useProfileCurrency';
import type { AIConfig, ProfileSettings, CurrencyRate } from '../../types';
import { Icon } from '@iconify/react';

const PROVIDERS = [
  { value: 'gemini', label: 'Gemini (Google)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
];

export function ApiKeyModal({
  open,
  onOpenChange,
  provider,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  provider: string;
  onSaved: (config: AIConfig) => void;
}) {
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setFieldErrors({});
    try {
      const config = await aiApi.saveSettings({ provider, api_key: apiKey });
      setApiKey('');
      onSaved(config);
      onOpenChange(false);
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      const data = (err as { response?: { data?: { error_code?: string } } }).response?.data;
      if (data?.error_code === 'invalid_key') {
        setFieldErrors((f) => ({ ...f, api_key: message }));
      }
    } finally {
      setSaving(false);
    }
  };

  const providerLabel = PROVIDERS.find((p) => p.value === provider)?.label ?? provider;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Configure {providerLabel} API Key</DialogTitle>
          <DialogDescription>
            The key is validated live, encrypted at rest, and returned masked.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Paste your API key"
              required
            />
            {fieldErrors.api_key && (
              <p className="mt-1 text-xs text-error">{fieldErrors.api_key}</p>
            )}
          </div>
          {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving || !apiKey}>
              {saving ? 'Validating…' : 'Save Key'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function SettingsPanel() {
  const [config, setConfig] = useState<AIConfig | null>(null);
  const [provider, setProvider] = useState('gemini');
  const [model, setModel] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [keyModalOpen, setKeyModalOpen] = useState(false);
  const [keyProvider, setKeyProvider] = useState('gemini');

  useEffect(() => {
    aiApi
      .getSettings()
      .then((c) => {
        setConfig(c);
        setProvider(c.provider);
        setModel(c.model);
      })
      .catch((err) => setError(getErrorMessage(err)));
  }, []);

  const handleProviderChange = (value: string) => {
    setProvider(value);
    if (config?.default_models?.[value]) {
      setModel(config.default_models[value]);
    }
  };

  const handleSaveSettings = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const updated = await aiApi.saveSettings({ provider, model });
      setConfig(updated);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const maskedKey = config?.keys?.[provider];

  return (
    <div className="space-y-4">
      {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

      <form onSubmit={handleSaveSettings} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="ai-provider">AI Provider</Label>
            <Select value={provider} onValueChange={handleProviderChange}>
              <SelectTrigger id="ai-provider" className="mt-2">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="ai-model">Model</Label>
            <Input
              id="ai-model"
              className="mt-2"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={config?.default_models?.[provider] ?? 'Default model'}
            />
            {config?.default_models?.[provider] && (
              <p className="mt-1 text-xs text-muted-foreground">
                Default: {config.default_models[provider]}
              </p>
            )}
          </div>
        </div>
        <Button type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save Settings'}
        </Button>
      </form>

      <div className="rounded-sm border border-border p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-foreground">API Key — {provider}</p>
            <p className="text-sm text-muted-foreground">
              {maskedKey ? `Stored: ${maskedKey}` : 'No key stored yet'}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => { setKeyProvider(provider); setKeyModalOpen(true); }}>
            <Icon icon="solar:key-linear" height={16} width={16} className="mr-2" />
            {maskedKey ? 'Replace Key' : 'Add Key'}
          </Button>
        </div>
      </div>

      <ApiKeyModal
        open={keyModalOpen}
        onOpenChange={setKeyModalOpen}
        provider={keyProvider}
        onSaved={setConfig}
      />
    </div>
  );
}

export default function ProfileSettings() {
  const [settings, setSettings] = useState<ProfileSettings | null>(null);
  const [newType, setNewType] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [newCategoryType, setNewCategoryType] = useState('expense');
  const [rates, setRates] = useState<CurrencyRate[]>([]);
  const [newCurrencyCode, setNewCurrencyCode] = useState('');
  const [newCurrencyRate, setNewCurrencyRate] = useState('');
  const [saving, setSaving] = useState(false);
  const [savingRates, setSavingRates] = useState(false);
  const [ratesError, setRatesError] = useState('');
  const [error, setError] = useState('');
  const { profileCurrency } = useProfileCurrency();

  const fetchRates = async () => {
    setRatesError('');
    try {
      const data = await exchangeRatesApi.list();
      setRates(data);
    } catch (err) {
      setRatesError(getErrorMessage(err));
    }
  };

  useEffect(() => {
    // Use profileCurrency from hook (reads cookie on mount)
    setCurrency(profileCurrency);
  }, [profileCurrency]);

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const updated = await profileApi.update({
        currency,
        new_type: newType,
        new_category: newCategory,
        new_category_type: newCategoryType,
      });
      setSettings(updated);
      setNewType('');
      setNewCategory('');
      // Refresh page to apply new currency/state across all components
      window.location.reload();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    if (settings?.currency) {
      setCurrency(settings.currency);
    }
  }, [settings?.currency]);

  const handleRateChange = (index: number, field: 'currency_code' | 'rate_to_cop', value: string) => {
    setRates((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [field]: field === 'rate_to_cop' ? Number(value) : value } : r)),
    );
  };

  const handleSaveRates = async () => {
    setSavingRates(true);
    setRatesError('');
    try {
      const updated = await exchangeRatesApi.bulkUpsert(rates);
      setRates(updated);
    } catch (err) {
      setRatesError(getErrorMessage(err));
    } finally {
      setSavingRates(false);
    }
  };

  const handleAddCurrency = async () => {
    if (!newCurrencyCode.trim()) return;
    const code = newCurrencyCode.trim().toUpperCase();
    setSavingRates(true);
    setRatesError('');
    try {
      const rate = newCurrencyRate.trim() ? Number(newCurrencyRate) : 1;
      const created = await exchangeRatesApi.create({ currency_code: code, rate_to_cop: rate });
      setRates((prev) => [...prev, created]);
      setNewCurrencyCode('');
      setNewCurrencyRate('');
    } catch (err) {
      setRatesError(getErrorMessage(err));
    } finally {
      setSavingRates(false);
    }
  };

  const handleDeleteCurrency = async (code: string) => {
    if (code === BASE_CURRENCY || code === settings?.currency) return;
    setSavingRates(true);
    setRatesError('');
    try {
      await exchangeRatesApi.delete(code);
      setRates((prev) => prev.filter((r) => r.currency_code !== code));
    } catch (err) {
      setRatesError(getErrorMessage(err));
    } finally {
      setSavingRates(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Account Settings"
        title="Profile & preferences"
        description="Currency, categories and the AI assistant that reads your ledger."
      />

      {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

      <div className="grid gap-6 xl:grid-cols-2">
        <CardBox>
          <div className="p-6">
            <h3 className="font-display text-xl font-normal text-foreground">Currency & Categories</h3>
            <form onSubmit={handleSave} className="mt-4 space-y-4">
              <div>
                <Label htmlFor="currency">Currency Code</Label>
                <Input
                  id="currency"
                  className="mt-2"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                  required
                  maxLength={3}
                />
              </div>
              <div className="rounded-sm border border-border p-4">
                <p className="text-sm font-medium text-foreground">Add Transaction Type</p>
                <div className="mt-3 flex gap-2">
                  <Input
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                    placeholder="e.g. Bonus"
                  />
                </div>
              </div>
              <div className="rounded-sm border border-border p-4">
                <p className="text-sm font-medium text-foreground">Add Category</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Input
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    placeholder="e.g. Subscriptions"
                  />
                  <Select value={newCategoryType} onValueChange={setNewCategoryType}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="expense">Expense</SelectItem>
                      <SelectItem value="income">Income</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Save Changes'}
              </Button>
            </form>
          </div>
        </CardBox>

        <CardBox>
          <div className="p-6">
            <h3 className="font-display text-xl font-normal text-foreground">AI Assistant Settings</h3>
            <div className="mt-4">
              <SettingsPanel />
            </div>
          </div>
        </CardBox>
      </div>

      {settings && (
        <CardBox>
          <div className="p-6">
            <h3 className="font-display text-xl font-normal text-foreground">Your Categories</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {settings.categories.map((cat) => (
                <Badge key={`${cat.id ?? 'builtin'}-${cat.type}-${cat.name}`} variant="gray">
                  {cat.name}
                  <span className="ml-1 text-xs opacity-70">({cat.type})</span>
                </Badge>
              ))}
            </div>
            <h3 className="mt-5 font-display text-xl font-normal text-foreground">Transaction Types</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {settings.types.map((t) => (
                <Badge key={`${t.id ?? 'builtin'}-${t.name}`} variant="gray">
                  {t.name}
                </Badge>
              ))}
            </div>
          </div>
        </CardBox>
      )}

      <CardBox>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-xl font-normal text-foreground">Exchange Rates</h3>
            <p className="text-sm text-muted-foreground">
              Base currency: <strong>{BASE_CURRENCY}</strong> (COP)
            </p>
          </div>
          {ratesError && (
            <p className="mt-3 rounded-md bg-error/10 px-3 py-2 text-sm text-error">{ratesError}</p>
          )}
          <div className="mt-4 overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className="text-left font-medium text-muted-foreground">Currency</th>
                  <th className="text-left font-medium text-muted-foreground">
                    Rate to 1 {BASE_CURRENCY}
                  </th>
                  <th className="text-right font-medium text-muted-foreground">Action</th>
                </tr>
              </thead>
              <tbody>
                {rates.map((r, i) => (
                  <tr key={r.currency_code} className="border-b border-border">
                    <td className="py-2">
                      <Input
                        className="w-20 font-mono text-xs"
                        value={r.currency_code}
                        onChange={(e) =>
                          handleRateChange(i, 'currency_code', e.target.value.toUpperCase())
                        }
                        maxLength={3}
                      />
                    </td>
                    <td className="py-2">
                      <Input
                        className="w-32 font-mono text-xs"
                        type="number"
                        step="0.0001"
                        min={0}
                        value={r.rate_to_cop}
                        onChange={(e) => handleRateChange(i, 'rate_to_cop', e.target.value)}
                      />
                    </td>
                    <td className="py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteCurrency(r.currency_code)}
                        disabled={r.currency_code === BASE_CURRENCY || r.currency_code === settings?.currency}
                      >
                        <Icon icon="solar:trash-bin-minimal-linear" width={16} height={16} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <div>
              <Label htmlFor="new-currency-code">New Currency</Label>
              <Input
                id="new-currency-code"
                className="mt-1 w-20 font-mono text-xs"
                value={newCurrencyCode}
                onChange={(e) => setNewCurrencyCode(e.target.value.toUpperCase())}
                maxLength={3}
                placeholder="USD"
              />
            </div>
            <div>
              <Label htmlFor="new-currency-rate">Rate to {BASE_CURRENCY}</Label>
              <Input
                id="new-currency-rate"
                className="mt-1 w-32 font-mono text-xs"
                type="number"
                step="0.0001"
                min={0}
                value={newCurrencyRate}
                onChange={(e) => setNewCurrencyRate(e.target.value)}
                placeholder="0.0001"
              />
            </div>
            <Button type="button" variant="outline" size="sm" onClick={handleAddCurrency} disabled={!newCurrencyCode.trim() || savingRates}>
              <Icon icon="solar:add-linear" width={16} height={16} className="mr-1" />
              Add
            </Button>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={fetchRates} disabled={savingRates}>
              <Icon icon="solar:refresh-linear" width={16} height={16} className="mr-1" />
              Reload
            </Button>
            <Button size="sm" onClick={handleSaveRates} disabled={savingRates || rates.length === 0}>
              {savingRates ? 'Saving…' : 'Save Rates'}
            </Button>
          </div>
        </div>
      </CardBox>
    </div>
  );
}