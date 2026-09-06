/**
 * API calls for the second factor.
 *
 * Two separate flows live here and must not be confused:
 *
 *   - Enrollment, from the profile screen, on an already-authenticated
 *     session: setup → enable → backup codes.
 *   - The login challenge, on a session that has cleared the password step
 *     but holds no access token yet — that one lives in api/auth.ts, because
 *     it is part of signing in, not part of managing the account.
 */
import { apiClient } from './client';
import type { TwoFactorEnrollment, TwoFactorStatus } from '../types';

export interface BackupCodesResponse extends TwoFactorStatus {
  backup_codes: string[];
  message: string;
}

export const twoFactorApi = {
  async status(): Promise<TwoFactorStatus> {
    const { data } = await apiClient.get<TwoFactorStatus>('/profile/2fa/');
    return data;
  },

  /** Hands out the secret and its QR. The secret is shown exactly once. */
  async setup(): Promise<TwoFactorEnrollment> {
    const { data } = await apiClient.post<TwoFactorEnrollment>('/profile/2fa/setup/');
    return data;
  },

  /** Proves the authenticator works, switches 2FA on, returns backup codes. */
  async enable(code: string): Promise<BackupCodesResponse> {
    const { data } = await apiClient.post<BackupCodesResponse>('/profile/2fa/enable/', { code });
    return data;
  },

  /** Turning the second factor off asks for the password again. */
  async disable(password: string): Promise<TwoFactorStatus> {
    const { data } = await apiClient.post<TwoFactorStatus>('/profile/2fa/disable/', { password });
    return data;
  },

  /** New codes invalidate the old ones. Also password-gated. */
  async regenerateBackupCodes(password: string): Promise<BackupCodesResponse> {
    const { data } = await apiClient.post<BackupCodesResponse>('/profile/2fa/backup-codes/', {
      password,
    });
    return data;
  },
};
