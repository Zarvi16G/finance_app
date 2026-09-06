/**
 * API calls for the auth endpoints (register/login/refresh/logout/me).
Used by pages/Login, pages/Register and auth/AuthContext.
 */
import { apiClient } from './client';
import type { AuthResponse, LoginResult, User } from '../types';

export const authApi = {
  async register(username: string, password: string, email?: string): Promise<AuthResponse> {
    const { data } = await apiClient.post<AuthResponse>('/auth/register/', {
      username,
      password,
      email: email || '',
    });
    return data;
  },

  /**
   * Password step. Returns the token pair for an account without a second
   * factor, or an `MfaChallenge` when one is enabled — never both. Callers
   * must branch on `isMfaChallenge` before reaching for `.access`.
   */
  async login(username: string, password: string): Promise<LoginResult> {
    const { data } = await apiClient.post<LoginResult>('/auth/login/', { username, password });
    return data;
  },

  /**
   * Second step. `code` accepts either a six-digit TOTP code or one of the
   * single-use backup codes — the backend tries both, so the UI does not need
   * to ask the user which kind they are typing.
   */
  async verifyTwoFactor(mfaToken: string, code: string): Promise<AuthResponse> {
    const { data } = await apiClient.post<AuthResponse>('/auth/2fa/verify/', {
      mfa_token: mfaToken,
      code,
    });
    return data;
  },

  async logout(refresh: string): Promise<void> {
    await apiClient.post('/auth/logout/', { refresh });
  },

  async me(): Promise<User> {
    const { data } = await apiClient.get<User>('/auth/me/');
    return data;
  },
};