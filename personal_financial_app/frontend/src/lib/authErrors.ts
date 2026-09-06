/**
 * Wording for the sign-in and second-factor errors.
 *
 * The backend tags these responses with an `error_code` precisely so a client
 * can word them itself. Keying off that code rather than off the English
 * sentence keeps the copy stable when the server's message is reworded, and
 * lets it follow the interface language. Anything unmapped falls through to
 * whatever the server said — an unfamiliar error in English beats a blank
 * one.
 */
import axios from 'axios';
import i18n from '../i18n';
import { getErrorMessage } from '../api/client';

const BY_CODE: Record<string, string> = {
  mfa_code_invalid: 'auth.errorCodeInvalid',
  mfa_token_invalid: 'auth.errorTokenInvalid',
  invalid_password: 'auth.errorPassword',
  already_enabled: 'auth.errorAlreadyEnabled',
};

export function authErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { error_code?: string; detail?: string } | undefined;
    const key = data?.error_code && BY_CODE[data.error_code];
    if (key) return i18n.t(key);
    // SimpleJWT answers 401 with a generic "No active account found…".
    if (error.response?.status === 401 && data?.detail) return i18n.t('auth.errorCredentials');
  }
  return getErrorMessage(error);
}
