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
      headline="Tu contraseña ya fue aceptada."
      blurb="Falta el segundo paso. Hasta que confirmes el código, esta sesión no tiene acceso a ninguno de tus datos — el paso intermedio no otorga permisos por sí solo."
      footnote="Verificación en dos pasos"
    >
      <p className="letterhead mb-3.5">Paso 2 de 2</p>
      <h1 className="fig m-0 text-[32px] font-medium">
        {useBackup ? 'Usa un código de recuperación' : 'Introduce tu código'}
      </h1>
      <p className="m-0 mt-3 text-[15px] leading-relaxed text-inksoft">
        {useBackup
          ? 'Cualquiera de los diez que guardaste al activar la verificación. Cada uno sirve una sola vez.'
          : 'El de seis dígitos que muestra tu app de autenticación.'}
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
            aria-label="Código de recuperación"
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
              Este intento caducó. Vuelve a iniciar sesión para empezar de nuevo.
            </span>
          ) : (
            <span>
              Este intento caduca en{' '}
              <span className="fig text-foreground">{mmss(remaining)}</span>. Después habrá que
              empezar de nuevo.
            </span>
          )}
        </div>

        {error && <p className="mt-4 bg-lighterror px-3 py-2 text-sm text-error">{error}</p>}

        <Button
          type="submit"
          className="mt-6 w-full py-3.5 text-[15px]"
          disabled={submitting || expired || (useBackup ? !backupCode.trim() : code.length < 6)}
        >
          {submitting ? 'Verificando…' : 'Entrar'}
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
          {useBackup ? 'Volver al código de la app' : 'Usar un código de recuperación'}
        </button>
        {!useBackup && (
          <p className="m-0 mt-2.5 text-[13px] leading-relaxed text-muted-foreground">
            Si perdiste el teléfono, cualquiera de los diez códigos que guardaste sirve — una sola
            vez cada uno.
          </p>
        )}
      </div>

      <div className="mt-6">
        <button
          type="button"
          onClick={() => navigate('/login', { replace: true })}
          className="text-[13px] text-muted-foreground hover:text-foreground"
        >
          Volver e iniciar sesión con otra cuenta
        </button>
      </div>
    </AuthLayout>
  );
}
