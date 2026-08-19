/**
 * Login page (public-only route). Submits credentials through
 * AuthContext; redirects to the dashboard on success.
 */
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import CardBox from '../components/shared/CardBox';
import LedgerMark from '../components/shared/LedgerMark';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useAuth } from '../auth/AuthContext';
import { getErrorMessage } from '../api/client';

export default function Login() {
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
      await login(username, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="ledger-ruled relative flex h-screen items-center justify-center overflow-hidden bg-background px-4">
      <div className="w-full max-w-md">
        <CardBox className="border-border px-8 py-8 shadow-lg">
          <div className="flex items-center gap-3 border-b border-border pb-5">
            <LedgerMark className="h-9 w-9 text-foreground" />
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.22em] text-foreground">
                Ledgerline
              </p>
              <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
                Personal financial ledger
              </p>
            </div>
          </div>

          <div className="pt-6">
            <p className="letterhead">Account Holder · Sign-In</p>
            <h1 className="mt-1 font-display text-3xl font-normal text-foreground">
              Sign in to your ledger
            </h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Your records are private — they live on this server only.
            </p>
          </div>

          <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
            <div>
              <Label htmlFor="username" className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Username
              </Label>
              <Input
                id="username"
                type="text"
                className="mt-1 rounded-none border-x-0 border-t-0 bg-transparent px-0 focus-visible:border-b-2"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
              />
            </div>
            <div>
              <Label htmlFor="userpwd" className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Password
              </Label>
              <Input
                id="userpwd"
                type="password"
                className="mt-1 rounded-none border-x-0 border-t-0 bg-transparent px-0 focus-visible:border-b-2"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            {error && (
              <p className="rounded-sm bg-error/10 px-3 py-2 font-mono text-xs text-error">
                {error}
              </p>
            )}

            <Button type="submit" className="w-full font-mono text-[12px] uppercase tracking-[0.14em]" disabled={submitting}>
              {submitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
            <p className="text-sm text-muted-foreground">New to Ledgerline?</p>
            <Button asChild variant="ghost" size="sm" className="font-mono text-[11px] uppercase tracking-[0.12em]">
              <Link to="/register">Open an account</Link>
            </Button>
          </div>
        </CardBox>

        <p className="mt-4 text-center font-mono text-[9px] uppercase tracking-[0.2em] text-muted-foreground">
          Statement of identity · All figures stay yours
        </p>
      </div>
    </div>
  );
}
