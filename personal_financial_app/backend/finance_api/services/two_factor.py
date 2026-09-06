"""Two-factor authentication (TOTP, RFC 6238).

Everything the second factor needs lives here so the views stay thin:
secret generation, the QR payload an authenticator app scans, code
verification with replay protection, and single-use backup codes.

Design notes
- The shared secret is Fernet-encrypted at rest (crypto.py) and never leaves
  the server after enrollment — only the enrollment response shows it, once.
- Verification remembers the last accepted time step. A TOTP code is valid for
  its whole window, so without this an intercepted code could be replayed
  within those seconds.
- Backup codes are hashed with Django's password hashers and removed as they
  are used. Without them, losing the phone means losing the account.
- The intermediate login token is a signed value, NOT a JWT: it must never be
  accepted as an API credential, only exchanged for real tokens once the
  second factor checks out.
"""
import base64
import secrets
import time
from io import BytesIO

import pyotp
import qrcode
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing

from ..crypto import decrypt_text, encrypt_text

ISSUER = 'Personal Financial App'

# Accept codes one step either side of now, so a slightly wrong device clock
# does not lock people out. One step is 30 seconds.
VALID_WINDOW = 1

BACKUP_CODE_COUNT = 10
BACKUP_CODE_BYTES = 5  # -> 10 hex characters

# The token handed out between password and second factor.
MFA_TOKEN_SALT = 'finance_api.mfa'
MFA_TOKEN_MAX_AGE = 5 * 60  # seconds


# --- Enrollment ---------------------------------------------------------

def generate_secret() -> str:
    """A fresh base32 shared secret."""
    return pyotp.random_base32()


def provisioning_uri(secret: str, username: str) -> str:
    """The otpauth:// URI an authenticator app scans."""
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER)


def qr_data_uri(uri: str) -> str:
    """Render the provisioning URI as a PNG data URI.

    Returned inline so the client can show the QR with a plain <img> tag and
    the secret never has to travel through a third-party QR service.
    """
    image = qrcode.make(uri)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def start_enrollment(setting, username: str) -> dict:
    """Create (or replace) a pending secret and return what the client shows.

    The secret is stored immediately but `two_factor_enabled` stays False:
    enrollment only completes once the user proves they can generate a code.
    """
    secret = generate_secret()
    setting.totp_secret = encrypt_text(secret)
    setting.totp_last_step = None
    setting.save(update_fields=['totp_secret', 'totp_last_step', 'updated_at'])

    uri = provisioning_uri(secret, username)
    return {
        'secret': secret,          # shown once, for manual entry
        'otpauth_uri': uri,
        'qr_code': qr_data_uri(uri),
    }


def confirm_enrollment(setting, code: str) -> list[str]:
    """Finish enrollment. Returns the backup codes, which are shown once.

    Raises ValueError when there is no pending secret or the code is wrong.
    """
    secret = get_secret(setting)
    if not secret:
        raise ValueError('Start the setup first: no pending secret for this account.')
    if not verify_totp(setting, code, persist=False):
        raise ValueError('That code is not valid. Check your authenticator app and try again.')

    codes = _new_backup_codes(setting)
    setting.two_factor_enabled = True
    setting.two_factor_method = 'totp'
    _remember_step(setting, code, secret)
    setting.save()
    return codes


def regenerate_backup_codes(setting) -> list[str]:
    """Replace the recovery codes. The previous set stops working."""
    codes = _new_backup_codes(setting)
    setting.save(update_fields=['backup_codes', 'updated_at'])
    return codes


def _new_backup_codes(setting) -> list[str]:
    """Generate codes, store only their hashes, return the plaintext once."""
    codes = [secrets.token_hex(BACKUP_CODE_BYTES) for _ in range(BACKUP_CODE_COUNT)]
    setting.backup_codes = [make_password(code) for code in codes]
    return codes


def disable(setting) -> None:
    """Turn the second factor off and destroy its secrets."""
    setting.two_factor_enabled = False
    setting.two_factor_method = ''
    setting.totp_secret = ''
    setting.totp_last_step = None
    setting.backup_codes = []
    setting.save()


# --- Verification -------------------------------------------------------

def get_secret(setting) -> str:
    """Decrypt the stored shared secret ('' when none is stored)."""
    return decrypt_text(setting.totp_secret)


def verify_totp(setting, code: str, persist: bool = True) -> bool:
    """Check a 6-digit code, rejecting one already used in its window."""
    secret = get_secret(setting)
    if not secret or not code:
        return False

    code = str(code).strip().replace(' ', '')
    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=VALID_WINDOW):
        return False

    step = _step_for(code, secret)
    if setting.totp_last_step is not None and step is not None and step <= setting.totp_last_step:
        return False  # already used: replay inside the same window

    if persist:
        setting.totp_last_step = step
        setting.save(update_fields=['totp_last_step', 'updated_at'])
    return True


def verify_backup_code(setting, code: str) -> bool:
    """Consume a recovery code. Each one works exactly once."""
    if not code or not setting.backup_codes:
        return False

    code = str(code).strip().replace(' ', '').replace('-', '').lower()
    for stored in list(setting.backup_codes):
        if check_password(code, stored):
            remaining = [c for c in setting.backup_codes if c != stored]
            setting.backup_codes = remaining
            setting.save(update_fields=['backup_codes', 'updated_at'])
            return True
    return False


def verify_any(setting, code: str) -> bool:
    """Accept either a TOTP code or one of the backup codes."""
    return verify_totp(setting, code) or verify_backup_code(setting, code)


def _step_for(code: str, secret: str):
    """Which time step produced this code, within the accepted window."""
    totp = pyotp.TOTP(secret)
    now = int(time.time())
    for offset in range(-VALID_WINDOW, VALID_WINDOW + 1):
        timestamp = now + offset * totp.interval
        if totp.at(timestamp) == code:
            return timestamp // totp.interval
    return None


def _remember_step(setting, code: str, secret: str) -> None:
    setting.totp_last_step = _step_for(code, secret)


# --- Intermediate login token -------------------------------------------

def issue_mfa_token(user) -> str:
    """Short-lived proof that the password was already accepted.

    Deliberately a signed payload rather than a JWT: it carries no API
    authority, so it cannot be used as an access token if it leaks.
    """
    return signing.dumps({'user_id': user.pk}, salt=MFA_TOKEN_SALT)


def read_mfa_token(token: str):
    """Return the user id inside a valid, unexpired token, else None."""
    try:
        data = signing.loads(token, salt=MFA_TOKEN_SALT, max_age=MFA_TOKEN_MAX_AGE)
    except (signing.BadSignature, signing.SignatureExpired, TypeError):
        return None
    return data.get('user_id')


# --- Status -------------------------------------------------------------

def public_status(setting) -> dict:
    """What the profile screen may safely display."""
    return {
        'enabled': setting.two_factor_enabled,
        'method': setting.two_factor_method or None,
        'backup_codes_remaining': len(setting.backup_codes or []),
        'phone_number': setting.phone_number,
        'phone_verified': setting.phone_verified,
        'sms_available': False,  # no SMS provider wired up yet
    }
