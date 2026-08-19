/**
 * Registration page (public-only route). Creates the account
 * via AuthContext.register and redirects once logged in.
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

export default function Register() {
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
      setError('Passwords do not match.');
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
    <div className="ledger-ruled relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-10">
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
            <p className="letterhead">Account Holder · New Account</p>
            <h1 className="mt-1 font-display text-3xl font-normal text-foreground">
              Open a new ledger
            </h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              One account, one ledger. No fees, no banks attached — the records are yours.
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
              <Label htmlFor="email" className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Email <span className="normal-case tracking-normal text-muted-foreground/70">(optional)</span>
              </Label>
              <Input
                id="email"
                type="email"
                className="mt-1 rounded-none border-x-0 border-t-0 bg-transparent px-0 focus-visible:border-b-2"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>
            <div>
              <Label htmlFor="regpwd" className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Password <span className="normal-case tracking-normal text-muted-foreground/70">(8+ characters)</span>
              </Label>
              <Input
                id="regpwd"
                type="password"
                className="mt-1 rounded-none border-x-0 border-t-0 bg-transparent px-0 focus-visible:border-b-2"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                minLength={8}
              />
            </div>
            <div>
              <Label htmlFor="confirmpwd" className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                Confirm Password
              </Label>
              <Input
                id="confirmpwd"
                type="password"
                className="mt-1 rounded-none border-x-0 border-t-0 bg-transparent px-0 focus-visible:border-b-2"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>

            {error && (
              <p className="rounded-sm bg-error/10 px-3 py-2 font-mono text-xs text-error">
                {error}
              </p>
            )}

            <Button type="submit" className="w-full font-mono text-[12px] uppercase tracking-[0.14em]" disabled={submitting}>
              {submitting ? 'Opening account…' : 'Create account'}
            </Button>
          </form>

          <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
            <p className="text-sm text-muted-foreground">Already have an account?</p>
            <Button asChild variant="ghost" size="sm" className="font-mono text-[11px] uppercase tracking-[0.12em]">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>
        </CardBox>
      </div>
    </div>
  );
}