/**
 * The second step of signing in.
 *
 * Reached only from the login page, carrying the challenge in router state.
 * Landing here directly — a refresh, a bookmarked URL — means there is no
 * challenge to spend, so the page sends the visitor back to the password step
 * instead of showing a form that could not possibly work.
 *
 * The countdown is real: the backend's intermediate token has a five-minute
 * life, and when it runs out the attempt is genuinely over. Showing the clock
 * is the difference between "your code was wrong" and "you took too long",
 * which are different problems with different fixes.
 */
import { useEffect, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Icon } from '@iconify/react';
import AuthLayout from '../layouts/AuthLayout';
import CodeInput from '../components/shared/CodeInput';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { useAuth } from '../auth/AuthContext';
import { authErrorMessage } from '../lib/authErrors';
import type { MfaChallenge } from '../types';

/** Matches MFA_TOKEN_MAX_AGE in the backend's two_factor service. */
const CHALLENGE_SECONDS = 5 * 60;

const mmss = (total: number) => {
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
};

export default function TwoFactorChallenge() {
  const { t } = useTranslation();
  const { completeTwoFactor } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const challenge = (location.state as { challenge?: MfaChallenge } | null)?.challenge;

  const [code, setCode] = useState('');
  const [backupCode, setBackupCode] = useState('');
  const [useBackup, setUseBackup] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [remaining, setRemaining] = useState(CHALLENGE_SECONDS);

  useEffect(() => {
    if (!challenge) return;
    const id = window.setInterval(() => setRemaining((r) => Math.max(0, r - 1)), 1000);
    return () => window.clearInterval(id);
  }, [challenge]);

  if (!challenge) return <Navigate to="/login" replace />;

  const expired = remaining === 0;

  const submit = async (value: string) => {
    if (!value || submitting || expired) return;
    setError('');
    setSubmitting(true);
    try {
      await completeTwoFactor(challenge.mfa_token, value);
      navigate('/', { replace: true });
    } catch (err) {
      setError(authErrorMessage(err));
      setCode('');
    } finally {
      setSubmitting(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit(useBackup ? backupCode.trim() : code);
  };

  return (
    <AuthLayout
      headline={t('auth.mfaHeadline')}
      blurb={t('auth.mfaBlurb')}
      footnote={t('auth.mfaFootnote')}
    >
      <p className="letterhead mb-3.5">{t('auth.mfaStep')}</p>
      <h1 className="fig m-0 text-[32px] font-medium">
        {t(useBackup ? 'auth.backupTitle' : 'auth.mfaTitle')}
      </h1>
      <p className="m-0 mt-3 text-[15px] leading-relaxed text-inksoft">
        {t(useBackup ? 'auth.backupSubtitle' : 'auth.mfaSubtitle')}
      </p>

      <form className="mt-8" onSubmit={onSubmit}>
        {useBackup ? (
          <Input
            value={backupCode}
            onChange={(e) => setBackupCode(e.target.value)}
            disabled={submitting || expired}
            autoFocus
            autoComplete="one-time-code"
            placeholder="a3f9c1e072"
            className="font-mono tracking-[0.08em]"
            aria-label={t('auth.backupCodeLabel')}
          />
        ) : (
          <CodeInput
            size="lg"
            value={code}
            onChange={setCode}
            onComplete={submit}
            disabled={submitting || expired}
            autoFocus
          />
        )}

        <div className="mt-4 flex items-center gap-2.5 text-[13px] text-muted-foreground">
          <Icon icon="solar:clock-circle-linear" height={14} width={14} />
          {expired ? (
            <span className="text-error">
              {t('auth.expired')}
            </span>
          ) : (
            <span>
              {t('auth.expiresIn')}{' '}
              <span className="fig text-foreground">{mmss(remaining)}</span>
              {t('auth.expiresAfter')}
            </span>
          )}
        </div>

        {error && <p className="mt-4 bg-lighterror px-3 py-2 text-sm text-error">{error}</p>}

        <Button
          type="submit"
          className="mt-6 w-full py-3.5 text-[15px]"
          disabled={submitting || expired || (useBackup ? !backupCode.trim() : code.length < 6)}
        >
          {submitting ? t('auth.verifying') : t('auth.signIn')}
        </Button>
      </form>

      <div className="mt-6 border-t border-border pt-6">
        <button
          type="button"
          onClick={() => {
            setUseBackup((v) => !v);
            setError('');
          }}
          className="flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
        >
          <Icon icon="solar:lock-keyhole-minimalistic-linear" height={15} width={15} />
          {t(useBackup ? 'auth.backToApp' : 'auth.useBackup')}
        </button>
        {!useBackup && (
          <p className="m-0 mt-2.5 text-[13px] leading-relaxed text-muted-foreground">
            {t('auth.backupHint')}
          </p>
        )}
      </div>

      <div className="mt-6">
        <button
          type="button"
          onClick={() => navigate('/login', { replace: true })}
          className="text-[13px] text-muted-foreground hover:text-foreground"
        >
          {t('auth.otherAccount')}
        </button>
      </div>
    </AuthLayout>
  );
}
