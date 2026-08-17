/**
 * Login page (public-only route). Submits credentials through
AuthContext; redirects to the dashboard on success.
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
    <div className="relative overflow-hidden h-screen bg-lightprimary dark:bg-darkprimary">
      <div className="flex h-full justify-center items-center px-4">
        <CardBox className="md:w-[450px] w-full border-none">
          <div className="mx-auto mb-6 text-center">
            <img src={logo} alt="FinanceApp logo" className="mx-auto h-14 w-14" />
            <h3 className="mt-2 text-2xl font-semibold text-foreground">FinanceApp</h3>
            <p className="text-sm text-muted-foreground mt-1">Sign in to your account</p>
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
                <Label htmlFor="userpwd">Password</Label>
              </div>
              <Input
                id="userpwd"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            {error && (
              <p className="mb-3 rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>
            )}

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          <div className="flex gap-2 text-base text-ld font-medium mt-6 items-center justify-center">
            <p>New to FinanceApp?</p>
            <Link to="/register" className="text-primary text-sm font-medium">
              Create an account
            </Link>
          </div>
        </CardBox>
      </div>
    </div>
  );
}