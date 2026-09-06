/**
 * AI assistant settings: which provider reads the ledger, which model, and
 * the API key for it.
 *
 * The key never round-trips in the clear — it is validated live on save,
 * encrypted at rest with the same Fernet helper that protects the TOTP
 * secret, and comes back masked.
 */
import { useEffect, useState, type FormEvent } from 'react';
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
import { aiApi } from '../../api/ai';
import { getErrorMessage } from '../../api/client';
import type { AIConfig } from '../../types';
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
          <DialogTitle>Clave de {providerLabel}</DialogTitle>
          <DialogDescription>
            La clave se valida contra el proveedor al guardarla, se cifra en el servidor y solo vuelve enmascarada.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <Label htmlFor="api-key">Clave</Label>
            <Input
              id="api-key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Pega aquí tu clave"
              required
            />
            {fieldErrors.api_key && (
              <p className="mt-1 text-xs text-error">{fieldErrors.api_key}</p>
            )}
          </div>
          {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving || !apiKey}>
              {saving ? 'Validando…' : 'Guardar clave'}
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
            <Label htmlFor="ai-provider">Proveedor</Label>
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
            <Label htmlFor="ai-model">Modelo</Label>
            <Input
              id="ai-model"
              className="mt-2"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={config?.default_models?.[provider] ?? 'Modelo por defecto'}
            />
            {config?.default_models?.[provider] && (
              <p className="mt-1 text-xs text-muted-foreground">
                Por defecto: {config.default_models[provider]}
              </p>
            )}
          </div>
        </div>
        <Button type="submit" disabled={saving}>
          {saving ? 'Guardando…' : 'Guardar'}
        </Button>
      </form>

      <div className="rounded-sm border border-border p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-foreground">Clave de {provider}</p>
            <p className="text-sm text-muted-foreground">
              {maskedKey ? `Guardada: ${maskedKey}` : 'Todavía no hay ninguna clave guardada'}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => { setKeyProvider(provider); setKeyModalOpen(true); }}>
            <Icon icon="solar:key-linear" height={16} width={16} className="mr-2" />
            {maskedKey ? 'Reemplazar' : 'Añadir clave'}
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
