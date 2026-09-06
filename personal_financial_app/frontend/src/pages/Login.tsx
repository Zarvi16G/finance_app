/**
 * Login — the password step.
 *
 * The one thing to get right here: the password step no longer always ends in
 * a session. For an account with a second factor the backend answers with a
 * challenge and no tokens, and this page routes to /login/2fa carrying that
 * challenge in router state rather than in storage — the intermediate token
 * is short-lived and single-purpose, and putting it in localStorage would
 * outlive the attempt it belongs to.
 */
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import AuthLayout from '../layouts/AuthLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useAuth } from '../auth/AuthContext';
import { authErrorMessage } from '../lib/authErrors';
import { isMfaChallenge } from '../types';

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const result = await login(username, password);
      if (typeof result === 'object' && 'mfa_required' in result && isMfaChallenge(result)) {
        navigate('/login/2fa', { replace: true, state: { challenge: result, username } });
        return;
      }
      navigate('/', { replace: true });
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      headline={t('auth.loginHeadline')}
      blurb={t('auth.loginBlurb')}
      footnote={t('auth.loginFootnote')}
    >
      <p className="letterhead mb-3.5">{t('auth.signIn')}</p>
      <h1 className="fig m-0 text-[32px] font-medium">{t('auth.signInTitle')}</h1>
      <p className="m-0 mt-3 text-[15px] leading-relaxed text-inksoft">
        {t('auth.signInSubtitle')}
      </p>

      <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
        <div>
          <Label htmlFor="username">{t('auth.username')}</Label>
          <Input
            id="username"
            type="text"
            className="mt-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
          />
        </div>
        <div>
          <Label htmlFor="userpwd">{t('auth.password')}</Label>
          <Input
            id="userpwd"
            type="password"
            className="mt-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>

        {error && <p className="bg-lighterror px-3 py-2 text-sm text-error">{error}</p>}

        <Button type="submit" className="w-full py-3.5 text-[15px]" disabled={submitting}>
          {submitting ? t('auth.signingIn') : t('auth.signIn')}
        </Button>
      </form>

      <div className="mt-7 flex items-center justify-between border-t border-border pt-5">
        <p className="text-sm text-muted-foreground">{t('auth.noAccount')}</p>
        <Link to="/register" className="text-sm font-semibold text-primary hover:underline">
          {t('auth.createOne')}
        </Link>
      </div>
    </AuthLayout>
  );
}
