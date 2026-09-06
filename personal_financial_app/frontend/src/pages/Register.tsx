/**
 * Registration — creates the account and signs in immediately.
 *
 * A new account never has a second factor, so this path always ends in a
 * token pair; the challenge branch belongs to Login only.
 */
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import AuthLayout from '../layouts/AuthLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useAuth } from '../auth/AuthContext';
import { getErrorMessage } from '../api/client';

export default function Register() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError(t('auth.passwordsDoNotMatch'));
      return;
    }
    setSubmitting(true);
    try {
      await register(username, password, email);
      navigate('/', { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      headline={t('auth.registerHeadline')}
      blurb={t('auth.registerBlurb')}
      footnote={t('auth.registerFootnote')}
    >
      <p className="letterhead mb-3.5">{t('auth.createAccount')}</p>
      <h1 className="fig m-0 text-[32px] font-medium">{t('auth.registerTitle')}</h1>
      <p className="m-0 mt-3 text-[15px] leading-relaxed text-inksoft">
        {t('auth.registerSubtitle')}
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
          <Label htmlFor="email">
            {t('auth.email')}{' '}
            <span className="font-normal text-muted-foreground">{t('auth.emailOptional')}</span>
          </Label>
          <Input
            id="email"
            type="email"
            className="mt-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </div>
        <div>
          <Label htmlFor="regpwd">
            {t('auth.password')}{' '}
            <span className="font-normal text-muted-foreground">{t('auth.passwordHint')}</span>
          </Label>
          <Input
            id="regpwd"
            type="password"
            className="mt-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
            minLength={8}
          />
        </div>
        <div>
          <Label htmlFor="confirmpwd">{t('auth.repeatPassword')}</Label>
          <Input
            id="confirmpwd"
            type="password"
            className="mt-2"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            autoComplete="new-password"
          />
        </div>

        {error && <p className="bg-lighterror px-3 py-2 text-sm text-error">{error}</p>}

        <Button type="submit" className="w-full py-3.5 text-[15px]" disabled={submitting}>
          {submitting ? t('auth.creatingAccount') : t('auth.createAccount')}
        </Button>
      </form>

      <div className="mt-7 flex items-center justify-between border-t border-border pt-5">
        <p className="text-sm text-muted-foreground">{t('auth.haveAccount')}</p>
        <Link to="/login" className="text-sm font-semibold text-primary hover:underline">
          {t('auth.signIn')}
        </Link>
      </div>
    </AuthLayout>
  );
}
