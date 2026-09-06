/**
 * The second-factor block of the profile screen.
 *
 * It walks three states, and each one is a separate thing to look at:
 *
 *   off        the authenticator card offers "Activar"; the SMS card is
 *              visibly disabled with the reason written on it
 *   enrolling  QR + manual key + confirmation code — not yet active
 *   on         status, remaining backup codes, and the two password-gated
 *              actions (regenerate codes, turn off)
 *
 * Two design decisions worth keeping:
 *
 * SMS is shown, greyed, with the reason stated. The backend reports
 * `sms_available: false` because no provider is connected. Hiding the option
 * would suggest it does not exist; offering a live switch would suggest it
 * works. Showing it as unavailable, with why, is the only honest option.
 *
 * The backup codes are shown once and the panel says so in the loudest voice
 * on the page. Without them, losing the phone means losing the account, so
 * this is the one place the design uses a heavy 2px frame.
 */
import { useState } from 'react';
import { Icon } from '@iconify/react';
import CodeInput from '../shared/CodeInput';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { twoFactorApi } from '../../api/twoFactor';
import { authErrorMessage } from '../../lib/authErrors';
import type { TwoFactorEnrollment, TwoFactorStatus } from '../../types';

function BackupCodes({ codes, onDone }: { codes: string[]; onDone: () => void }) {
  const [copied, setCopied] = useState(false);

  const download = () => {
    const blob = new Blob(
      [
        'Códigos de recuperación · Patrimonio\n',
        'Cada uno sirve una sola vez. Guárdalos donde no esté tu teléfono.\n\n',
        codes.join('\n'),
        '\n',
      ],
      { type: 'text/plain' },
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'codigos-recuperacion-patrimonio.txt';
    link.click();
    URL.revokeObjectURL(url);
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(codes.join('\n'));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      // Clipboard access can be denied; the codes are on screen either way.
    }
  };

  return (
    <div className="border-2 border-foreground bg-card p-6">
      <div className="mb-4 flex items-start gap-3.5">
        <Icon
          icon="solar:danger-triangle-linear"
          height={20}
          width={20}
          className="mt-0.5 shrink-0 text-warning"
        />
        <div>
          <div className="fig mb-1.5 text-[19px] font-medium">Guarda estos códigos ahora</div>
          <p className="m-0 max-w-[78ch] text-sm leading-relaxed text-inksoft">
            Se muestran una sola vez y cada uno sirve una única vez. Son la forma de entrar si
            pierdes el teléfono — sin ellos, perder el dispositivo es perder la cuenta.
          </p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2.5 font-mono text-[15px] tracking-[0.06em] sm:grid-cols-3 lg:grid-cols-5">
        {codes.map((code) => (
          <div key={code} className="border border-border p-2.5 text-center">
            {code}
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-3">
        <Button onClick={download} className="bg-foreground text-background hover:bg-foreground/90">
          Descargar .txt
        </Button>
        <Button variant="outline" onClick={copy}>
          {copied ? 'Copiado' : 'Copiar'}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          Ya los guardé
        </Button>
      </div>
    </div>
  );
}

export default function TwoFactorSection({
  status,
  onChanged,
}: {
  status: TwoFactorStatus;
  onChanged: (status: TwoFactorStatus) => void;
}) {
  const [enrollment, setEnrollment] = useState<TwoFactorEnrollment | null>(null);
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [passwordFor, setPasswordFor] = useState<'disable' | 'regenerate' | null>(null);
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const run = async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
    setError('');
    setBusy(true);
    try {
      return await action();
    } catch (err) {
      setError(authErrorMessage(err));
      return undefined;
    } finally {
      setBusy(false);
    }
  };

  const startSetup = () =>
    run(async () => {
      setEnrollment(await twoFactorApi.setup());
      setCode('');
    });

  const confirm = (value: string) =>
    run(async () => {
      const res = await twoFactorApi.enable(value);
      setBackupCodes(res.backup_codes);
      setEnrollment(null);
      setCode('');
      onChanged(res);
    });

  const submitPassword = () =>
    run(async () => {
      if (passwordFor === 'disable') {
        onChanged(await twoFactorApi.disable(password));
      } else {
        const res = await twoFactorApi.regenerateBackupCodes(password);
        setBackupCodes(res.backup_codes);
        onChanged(res);
      }
      setPassword('');
      setPasswordFor(null);
    });

  return (
    <section className="border-t rule-strong pt-6">
      <div className="fig mb-1.5 text-[19px] font-medium">Verificación en dos pasos</div>
      <p className="m-0 mb-5 max-w-[72ch] text-sm leading-relaxed text-inksoft">
        Con esto activo, tu contraseña deja de ser suficiente por sí sola para entrar.
      </p>

      {error && <p className="mb-4 bg-lighterror px-3 py-2 text-sm text-error">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Authenticator app — the one that works */}
        <div className="border border-input bg-card p-6">
          <div className="mb-3.5 flex items-start justify-between gap-4">
            <div>
              <div className="mb-1 text-base font-semibold">App de autenticación</div>
              <div className="text-[13px] text-muted-foreground">
                Google Authenticator, 1Password, Authy…
              </div>
            </div>
            <span
              className={`shrink-0 border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.07em] ${
                status.enabled
                  ? 'border-success text-success'
                  : 'border-input text-muted-foreground'
              }`}
            >
              {status.enabled ? 'Activada' : 'Desactivada'}
            </span>
          </div>
          <p className="m-0 mb-4 text-sm leading-relaxed text-inksoft">
            Genera un código de seis dígitos que cambia cada 30 segundos. No depende de la señal ni
            de ningún proveedor externo.
          </p>

          {status.enabled ? (
            <div className="flex flex-col gap-3">
              <p className="m-0 text-[13px] text-muted-foreground">
                Te quedan{' '}
                <span className="fig text-foreground">{status.backup_codes_remaining}</span> códigos
                de recuperación sin usar.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button variant="outline" onClick={() => setPasswordFor('regenerate')}>
                  Generar códigos nuevos
                </Button>
                <Button variant="outline" onClick={() => setPasswordFor('disable')}>
                  Desactivar
                </Button>
              </div>
            </div>
          ) : (
            <Button onClick={startSetup} disabled={busy || Boolean(enrollment)}>
              {enrollment ? 'Configuración en curso' : 'Activar'}
            </Button>
          )}
        </div>

        {/* SMS — honestly unavailable */}
        <div className="border border-dashed border-input bg-accent p-6">
          <div className="mb-3.5 flex items-start justify-between gap-4">
            <div>
              <div className="mb-1 text-base font-semibold text-muted-foreground">
                Código por SMS
              </div>
              <div className="text-[13px] text-secondary">
                {status.phone_number ? `Al ${status.phone_number}` : 'Sin número registrado'}
              </div>
            </div>
            <span className="shrink-0 border border-input px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">
              No disponible
            </span>
          </div>
          <p className="m-0 mb-4 text-sm leading-relaxed text-muted-foreground">
            Todavía no hay un proveedor de SMS conectado, así que esta opción no puede enviarte
            nada. La dejamos visible para que sepas que existe, no para aparentar que funciona.
          </p>
          <button
            type="button"
            disabled
            className="cursor-not-allowed border border-input px-5 py-2.5 text-sm font-semibold text-secondary"
          >
            Activar
          </button>
        </div>
      </div>

      {/* Mid-enrolment */}
      {enrollment && (
        <div className="mt-8 border-t rule-strong pt-6">
          <div className="mb-5 flex flex-wrap items-baseline gap-3.5">
            <div className="fig text-[19px] font-medium">Activando la app de autenticación</div>
            <span className="text-xs text-muted-foreground">
              Estado intermedio · aún no está activa
            </span>
          </div>

          <div className="grid items-start gap-8 lg:grid-cols-[190px_1fr_1fr]">
            <div>
              <img
                src={enrollment.qr_code}
                alt="Código QR para tu app de autenticación"
                width={170}
                height={170}
                className="block border border-input bg-card"
              />
              <p className="m-0 mt-3 text-xs leading-relaxed text-muted-foreground">
                Escanéalo con tu app
              </p>
            </div>

            <div>
              <div className="mb-2 text-xs text-muted-foreground">
                ¿No puedes escanear? Escribe esta clave
              </div>
              <div className="break-all border border-input bg-card p-3.5 font-mono text-sm leading-relaxed tracking-[0.09em]">
                {enrollment.secret}
              </div>
              <p className="m-0 mt-3.5 text-[13px] leading-relaxed text-muted-foreground">
                Esta clave se muestra una sola vez. Después queda cifrada en el servidor y no se
                vuelve a mostrar.
              </p>
            </div>

            <div>
              <CodeInput
                label="Confirma con el código que muestra tu app"
                value={code}
                onChange={setCode}
                onComplete={confirm}
                disabled={busy}
              />
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => confirm(code)} disabled={busy || code.length < 6}>
                  Confirmar y activar
                </Button>
                <Button variant="ghost" onClick={() => setEnrollment(null)} disabled={busy}>
                  Cancelar
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Password gate for the two destructive actions */}
      {passwordFor && (
        <div className="mt-6 border border-input bg-card p-6">
          <div className="mb-2 text-base font-semibold">
            {passwordFor === 'disable'
              ? 'Confirma con tu contraseña para desactivar'
              : 'Confirma con tu contraseña para generar códigos nuevos'}
          </div>
          <p className="m-0 mb-4 max-w-[70ch] text-sm leading-relaxed text-inksoft">
            {passwordFor === 'disable'
              ? 'Desactivar la verificación en dos pasos debilita tu cuenta, así que se pide la contraseña otra vez: una sesión abierta y desatendida no debería poder hacerlo sola.'
              : 'Los códigos anteriores dejarán de funcionar en cuanto se generen los nuevos.'}
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[240px] flex-grow">
              <Label htmlFor="tfa-password">Contraseña</Label>
              <Input
                id="tfa-password"
                type="password"
                className="mt-2"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <Button onClick={submitPassword} disabled={busy || !password}>
              Confirmar
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setPasswordFor(null);
                setPassword('');
                setError('');
              }}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}

      {backupCodes && (
        <div className="mt-6">
          <BackupCodes codes={backupCodes} onDone={() => setBackupCodes(null)} />
        </div>
      )}
    </section>
  );
}
