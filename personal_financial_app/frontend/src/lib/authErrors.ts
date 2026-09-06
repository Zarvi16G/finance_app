/**
 * Spanish wording for the sign-in and second-factor errors.
 *
 * The backend tags these responses with an `error_code` precisely so a client
 * can word them itself. Keying off that code rather than off the English
 * sentence keeps the copy stable when the server's own message is reworded,
 * and anything unmapped falls through to whatever the server said — an
 * unfamiliar error in English beats a blank one.
 */
import axios from 'axios';
import { getErrorMessage } from '../api/client';

const BY_CODE: Record<string, string> = {
  mfa_code_invalid: 'Ese código no es válido. Revisa tu app y prueba con el siguiente.',
  mfa_token_invalid: 'Este intento de inicio de sesión caducó. Empieza de nuevo.',
  invalid_password: 'Esa contraseña no es correcta.',
  already_enabled:
    'La verificación en dos pasos ya está activa. Desactívala primero para registrar otro dispositivo.',
};

/** The credentials error, which SimpleJWT returns without an error_code. */
const CREDENTIALS = 'Usuario o contraseña incorrectos.';

export function authErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { error_code?: string; detail?: string } | undefined;
    const mapped = data?.error_code && BY_CODE[data.error_code];
    if (mapped) return mapped;
    // SimpleJWT answers 401 with a generic "No active account found…".
    if (error.response?.status === 401 && data?.detail) return CREDENTIALS;
  }
  return getErrorMessage(error);
}
