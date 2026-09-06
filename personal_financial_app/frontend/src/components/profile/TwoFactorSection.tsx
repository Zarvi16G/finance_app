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
import { useTranslation } from 'react-i18next';
import { Icon } from '@iconify/react';
import CodeInput from '../shared/CodeInput';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { twoFactorApi } from '../../api/twoFactor';
import { authErrorMessage } from '../../lib/authErrors';
import type { TwoFactorEnrollment, TwoFactorStatus } from '../../types';

function BackupCodes({ codes, onDone }: { codes: string[]; onDone: () => void }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const download = () => {
    const blob = new Blob(
      [
        `${t('twoFactor.codesFileHeader')}\n`,
        `${t('twoFactor.codesFileNote')}\n\n`,
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
          <div className="fig mb-1.5 text-[19px] font-medium">{t('twoFactor.saveCodesTitle')}</div>
          <p className="m-0 max-w-[78ch] text-sm leading-relaxed text-inksoft">
            {t('twoFactor.saveCodesBody')}
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
          {t('twoFactor.downloadTxt')}
        </Button>
        <Button variant="outline" onClick={copy}>
          {copied ? t('twoFactor.copied') : t('twoFactor.copy')}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {t('twoFactor.savedThem')}
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
  const { t } = useTranslation();
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
      <div className="fig mb-1.5 text-[19px] font-medium">{t('twoFactor.title')}</div>
      <p className="m-0 mb-5 max-w-[72ch] text-sm leading-relaxed text-inksoft">
        {t('twoFactor.intro')}
      </p>

      {error && <p className="mb-4 bg-lighterror px-3 py-2 text-sm text-error">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Authenticator app — the one that works */}
        <div className="border border-input bg-card p-6">
          <div className="mb-3.5 flex items-start justify-between gap-4">
            <div>
              <div className="mb-1 text-base font-semibold">{t('twoFactor.appTitle')}</div>
              <div className="text-[13px] text-muted-foreground">
                {t('twoFactor.appSubtitle')}
              </div>
            </div>
            <span
              className={`shrink-0 border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.07em] ${
                status.enabled
                  ? 'border-success text-success'
                  : 'border-input text-muted-foreground'
              }`}
            >
              {t(status.enabled ? 'twoFactor.enabled' : 'twoFactor.disabled')}
            </span>
          </div>
          <p className="m-0 mb-4 text-sm leading-relaxed text-inksoft">
            {t('twoFactor.appNote')}
          </p>

          {status.enabled ? (
            <div className="flex flex-col gap-3">
              <p className="m-0 text-[13px] text-muted-foreground">
                {t('twoFactor.codesRemaining', { count: status.backup_codes_remaining })}
              </p>
              <div className="flex flex-wrap gap-3">
                <Button variant="outline" onClick={() => setPasswordFor('regenerate')}>
                  {t('twoFactor.regenerate')}
                </Button>
                <Button variant="outline" onClick={() => setPasswordFor('disable')}>
                  {t('twoFactor.disable')}
                </Button>
              </div>
            </div>
          ) : (
            <Button onClick={startSetup} disabled={busy || Boolean(enrollment)}>
              {t(enrollment ? 'twoFactor.inProgress' : 'twoFactor.enable')}
            </Button>
          )}
        </div>

        {/* SMS — honestly unavailable */}
        <div className="border border-dashed border-input bg-accent p-6">
          <div className="mb-3.5 flex items-start justify-between gap-4">
            <div>
              <div className="mb-1 text-base font-semibold text-muted-foreground">
                {t('twoFactor.smsTitle')}
              </div>
              <div className="text-[13px] text-secondary">
                {status.phone_number
                  ? t('twoFactor.smsTo', { phone: status.phone_number })
                  : t('twoFactor.smsNoPhone')}
              </div>
            </div>
            <span className="shrink-0 border border-input px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">
              {t('twoFactor.smsUnavailable')}
            </span>
          </div>
          <p className="m-0 mb-4 text-sm leading-relaxed text-muted-foreground">
            {t('twoFactor.smsNote')}
          </p>
          <button
            type="button"
            disabled
            className="cursor-not-allowed border border-input px-5 py-2.5 text-sm font-semibold text-secondary"
          >
            {t('twoFactor.enable')}
          </button>
        </div>
      </div>

      {/* Mid-enrolment */}
      {enrollment && (
        <div className="mt-8 border-t rule-strong pt-6">
          <div className="mb-5 flex flex-wrap items-baseline gap-3.5">
            <div className="fig text-[19px] font-medium">{t('twoFactor.enrolling')}</div>
            <span className="text-xs text-muted-foreground">
              {t('twoFactor.enrollingNote')}
            </span>
          </div>

          <div className="grid items-start gap-8 lg:grid-cols-[190px_1fr_1fr]">
            <div>
              <img
                src={enrollment.qr_code}
                alt={t('twoFactor.qrAlt')}
                width={170}
                height={170}
                className="block border border-input bg-card"
              />
              <p className="m-0 mt-3 text-xs leading-relaxed text-muted-foreground">
                {t('twoFactor.scanIt')}
              </p>
            </div>

            <div>
              <div className="mb-2 text-xs text-muted-foreground">
                {t('twoFactor.cannotScan')}
              </div>
              <div className="break-all border border-input bg-card p-3.5 font-mono text-sm leading-relaxed tracking-[0.09em]">
                {enrollment.secret}
              </div>
              <p className="m-0 mt-3.5 text-[13px] leading-relaxed text-muted-foreground">
                {t('twoFactor.secretNote')}
              </p>
            </div>

            <div>
              <CodeInput
                label={t('twoFactor.confirmWithCode')}
                value={code}
                onChange={setCode}
                onComplete={confirm}
                disabled={busy}
              />
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={() => confirm(code)} disabled={busy || code.length < 6}>
                  {t('twoFactor.confirmAndEnable')}
                </Button>
                <Button variant="ghost" onClick={() => setEnrollment(null)} disabled={busy}>
                  {t('common.cancel')}
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
            {t(
              passwordFor === 'disable'
                ? 'twoFactor.passwordToDisable'
                : 'twoFactor.passwordToRegenerate',
            )}
          </div>
          <p className="m-0 mb-4 max-w-[70ch] text-sm leading-relaxed text-inksoft">
            {t(passwordFor === 'disable' ? 'twoFactor.disableNote' : 'twoFactor.regenerateNote')}
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[240px] flex-grow">
              <Label htmlFor="tfa-password">{t('twoFactor.password')}</Label>
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
              {t('common.confirm')}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setPasswordFor(null);
                setPassword('');
                setError('');
              }}
            >
              {t('common.cancel')}
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
