/**
 * Global authentication state (React context).
 *
 * Exposes `user`, `login`, `register` and `logout` to the whole app.
 * On mount it restores the session from localStorage (auth/tokenStorage.ts)
 * and validates it against GET /auth/me; a 401 makes the axios interceptor
 * emit "auth:unauthorized", which signs the user out automatically.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { authApi } from '../api/auth';
import { tokenStorage } from './tokenStorage';
import { isMfaChallenge, type LoginResult, type MfaChallenge, type User } from '../types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  /**
   * The password step. Resolves to the signed-in user, or to a challenge when
   * the account has a second factor — in which case no tokens are stored and
   * nothing about the session has changed yet.
   */
  login: (username: string, password: string) => Promise<User | MfaChallenge>;
  /** The second step: spends the challenge token for a real session. */
  completeTwoFactor: (mfaToken: string, code: string) => Promise<User>;
  register: (username: string, password: string, email?: string) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const restoreSession = useCallback(async () => {
    if (!tokenStorage.getAccess()) {
      setLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      tokenStorage.clear();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      tokenStorage.clear();
    };
    window.addEventListener('auth:unauthorized', onUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', onUnauthorized);
  }, []);

  /** Turns a token pair into a live session. Shared by both login paths. */
  const adoptSession = useCallback((res: Exclude<LoginResult, MfaChallenge>) => {
    tokenStorage.setTokens(res.access, res.refresh);
    setUser(res.user);
    return res.user;
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await authApi.login(username, password);
      // A challenge is not a session: store nothing, sign nobody in, and hand
      // it back for the caller to route to the second step.
      if (isMfaChallenge(res)) return res;
      return adoptSession(res);
    },
    [adoptSession],
  );

  const completeTwoFactor = useCallback(
    async (mfaToken: string, code: string) => {
      const res = await authApi.verifyTwoFactor(mfaToken, code);
      return adoptSession(res);
    },
    [adoptSession],
  );

  const register = useCallback(async (username: string, password: string, email?: string) => {
    const res = await authApi.register(username, password, email);
    tokenStorage.setTokens(res.access, res.refresh);
    setUser(res.user);
    return res.user;
  }, []);

  const logout = useCallback(async () => {
    const refresh = tokenStorage.getRefresh();
    try {
      if (refresh) await authApi.logout(refresh);
    } catch {
      // ignore network errors during logout
    } finally {
      setUser(null);
      tokenStorage.clear();
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, completeTwoFactor, register, logout }),
    [user, loading, login, completeTwoFactor, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}