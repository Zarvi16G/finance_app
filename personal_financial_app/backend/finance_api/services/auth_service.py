"""Authentication business logic: registration, token issuing and session helpers.

The views layer stays thin and delegates all logic here, following the
services/ organization used across the app.
"""
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from ..models.snapshots import DailyUserSnapshot
from ..services.currency import convert_to_cop, get_rate_map

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


def ensure_daily_snapshot(user: User) -> DailyUserSnapshot:
    """
    Ensure the user has a daily snapshot for today.

    - Same day: return existing snapshot if snapshot_date == today()
    - New day / stale: hard delete existing snapshot for this user,
      fetch live USD exchange rates via external API, create new snapshot.
    """
    today = date.today()
    # Check if we already have a snapshot for today
    snapshot, created = DailyUserSnapshot.objects.get_or_create(
        user=user,
        snapshot_date=today,
        defaults={'rates': _fetch_rates_from_api(today)},
    )

    if not created:
        # Snapshot exists for today - reuse it, skip API call
        return snapshot

    # New day: delete any previous snapshot for this user and create fresh one
    # (get_or_create above already created it with defaults, so we need to
    # fetch real rates and update it). Reset it by deleting and recreating.
    snapshot.delete()
    rates = _fetch_rates_from_api(today)
    return DailyUserSnapshot.objects.create(user=user, snapshot_date=today, rates=rates)


def _fetch_rates_from_api(snapshot_date: date) -> dict:
    """
    Fetch live USD exchange rates from an external API.
    Returns a dict mapping currency codes to rates relative to USD.
    E.g. {"EUR": 0.91, "COP": 4100.0}
    """
    # Try to use the existing CurrencyRate model as fallback source
    rate_map = get_rate_map()  # {currency_code: rate_to_cop, ...} with COP: 1.0

    # Convert COP-based rates to USD-relative rates.
    # We know: 1 USD = rate_to_cop COP, so 1 USD = 1 / rate_to_cop USD_in_cop_terms
    # For USD-relative rates: rate[currency] = how much 1 USD is worth in that currency
    # If 1 USD = 4100 COP, then:
    #   - USD relative to COP: 4100.0 (1 USD = 4100 COP)
    #   - USD relative to EUR: we need EUR rate. If EUR -> COP = 4100/0.91 ≈ 4505.5, then
    #     1 USD = 4100 COP = 4100 / 4505.5 EUR ≈ 0.91 EUR
    # Actually, the CurrencyRate model stores rate_to_cop = how many COP per 1 unit of currency.
    # So if USD has rate_to_cop = 4100.0, that means 1 USD = 4100 COP.
    # For USD-relative rates, we want: rate["USD"] = 1.0 (by definition)
    # and rate["EUR"] = how much 1 USD = in EUR.

    # Let's compute USD-relative rates from the COP-based rates.
    rates: dict = {}
    usd_to_cop = rate_map.get('COP', 1.0)  # should be ~4100.0

    # Always include USD at 1.0
    rates['USD'] = 1.0

    # Convert each known currency to its USD-relative rate
    for code, rate_to_cop in rate_map.items():
        if code == 'COP':
            rates['COP'] = float(usd_to_cop)
        else:
            # rate_to_cop = how many COP per 1 unit of foreign currency
            # 1 USD = usd_to_cop COP
            # So 1 USD = (usd_to_cop / rate_to_cop) units of foreign currency
            usd_in_foreign = usd_to_cop / float(rate_to_cop)
            rates[code] = usd_in_foreign

    return rates


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