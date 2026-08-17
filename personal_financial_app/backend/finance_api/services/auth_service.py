"""Authentication business logic: registration, token issuing and session helpers.

The views layer stays thin and delegates all logic here, following the
services/ organization used across the app.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class RegistrationError(ValueError):
    """Raised when a user cannot be registered (invalid or duplicated data)."""


def register_user(username: str, password: str, email: str = '') -> User:
    """
    Validates credentials and creates a new user.

    Username uniqueness is checked case-insensitively and the password is
    validated against Django's configured password validators.
    """
    username = (username or '').strip()
    email = (email or '').strip()

    if not username:
        raise RegistrationError('Username is required.')
    if not password:
        raise RegistrationError('Password is required.')

    if User.objects.filter(username__iexact=username).exists():
        raise RegistrationError('This username is already taken.')

    try:
        validate_password(password)
    except ValidationError as exc:
        raise RegistrationError(' '.join(exc.messages)) from exc

    return User.objects.create_user(username=username, email=email, password=password)


def issue_tokens(user: User) -> dict:
    """Build the JWT pair (access + refresh) for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def get_user_payload(user: User) -> dict:
    """Safe, serializable representation of the authenticated user."""
    return {
        'id': user.pk,
        'username': user.username,
        'email': user.email,
        'is_staff': user.is_staff,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
    }


def blacklist_refresh(refresh_token: str) -> bool:
    """
    Blacklist a refresh token so it can no longer be used to obtain
    new access tokens. Returns False when the token is invalid or revoked.
    """
    try:
        RefreshToken(refresh_token).blacklist()
        return True
    except (TokenError, ValueError):
        return False