"""Cryptographic helpers for protecting secrets (AI API keys) at rest."""
import hashlib
import base64

from cryptography.fernet import Fernet, InvalidToken

_FERNET = None


def _get_fernet():
    global _FERNET
    if _FERNET is None:
        from django.conf import settings
        raw = getattr(settings, 'SECRET_KEY', 'insecure-dev-key') or 'insecure-dev-key'
        digest = hashlib.sha256(raw.encode('utf-8')).digest()
        key = base64.urlsafe_b64encode(digest)
        _FERNET = Fernet(key)
    return _FERNET


def encrypt_text(plaintext: str) -> str:
    """Encrypt a string for storage. Raises ValueError on empty input."""
    if not plaintext:
        raise ValueError('Cannot encrypt an empty value')
    return _get_fernet().encrypt(plaintext.encode('utf-8')).decode('utf-8')


def decrypt_text(ciphertext: str) -> str:
    """Decrypt a stored string. Returns '' if the value is not valid/decodable."""
    if not ciphertext:
        return ''
    try:
        return _get_fernet().decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except (InvalidToken, ValueError):
        return ''


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """Mask a secret for safe display: '••••abcd'."""
    if not secret:
        return ''
    if len(secret) <= visible_chars:
        return '••••'
    return '••••' + secret[-visible_chars:]