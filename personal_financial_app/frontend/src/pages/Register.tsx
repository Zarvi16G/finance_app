/**
 * Registration page (public-only route). Creates the account
via AuthContext.register and redirects once logged in.
 */
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import CardBox from '../components/shared/CardBox';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useAuth } from '../auth/AuthContext';
import { getErrorMessage } from '../api/client';
import logo from '../assets/logo.svg';

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
    <div className="relative overflow-hidden h-screen bg-lightprimary dark:bg-darkprimary">
      <div className="flex h-full justify-center items-center px-4">
        <CardBox className="md:w-[450px] w-full border-none">
          <div className="mx-auto mb-6 text-center">
            <img src={logo} alt="FinanceApp logo" className="mx-auto h-14 w-14" />
            <h3 className="mt-2 text-2xl font-semibold text-foreground">FinanceApp</h3>
            <p className="text-sm text-muted-foreground mt-1">Create your account</p>
          </div>

          <form className="mt-6" onSubmit={handleSubmit}>
            <div className="mb-4">
              <div className="mb-2 block">
                <Label htmlFor="username">Username</Label>
              </div>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
              />
            </div>
            <div className="mb-4">
              <div className="mb-2 block">
                <Label htmlFor="email">Email (optional)</Label>
              </div>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>
            <div className="mb-4">
              <div className="mb-2 block">
                <Label htmlFor="regpwd">Password</Label>
              </div>
              <Input
                id="regpwd"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                minLength={8}
              />
            </div>
            <div className="mb-4">
              <div className="mb-2 block">
                <Label htmlFor="confirmpwd">Confirm Password</Label>
              </div>
              <Input
                id="confirmpwd"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>

            {error && (
              <p className="mb-3 rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>
            )}

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? 'Creating account…' : 'Create account'}
            </Button>
          </form>

          <div className="flex gap-2 text-base text-ld font-medium mt-6 items-center justify-center">
            <p>Already have an account?</p>
            <Link to="/login" className="text-primary text-sm font-medium">
              Sign in
            </Link>
          </div>
        </CardBox>
      </div>
    </div>
  );
}