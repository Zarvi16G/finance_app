"""API views for managing the second factor from the profile screen.

Enrollment is deliberately two calls: `setup` hands out a secret, and
`enable` only switches 2FA on once the user proves the authenticator app is
producing valid codes. Turning it off asks for the password again, so a
walked-away session cannot silently weaken the account.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes

from ..models import UserSetting
from ..services import two_factor


def _setting(user) -> UserSetting:
    setting, _ = UserSetting.objects.get_or_create(owner=user)
    return setting


@extend_schema_view(
    get=extend_schema(
        responses={200: OpenApiTypes.OBJECT},
        description='Current second-factor status. Never returns the shared secret.',
    ),
)
class TwoFactorStatusView(APIView):
    """GET /api/profile/2fa/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(two_factor.public_status(_setting(request.user)))


@extend_schema_view(
    post=extend_schema(
        request=None,
        responses={200: OpenApiTypes.OBJECT, 409: OpenApiTypes.OBJECT},
        description=(
            'Starts enrollment: returns the shared secret, its otpauth URI and '
            'an inline QR image. This is the only time the secret is exposed. '
            '2FA is not active until POST /api/profile/2fa/enable/ succeeds.'
        ),
    )
)
class TwoFactorSetupView(APIView):
    """POST /api/profile/2fa/setup/"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'mfa'

    def post(self, request):
        setting = _setting(request.user)
        if setting.two_factor_enabled:
            return Response(
                {'error': 'Two-factor is already enabled. Disable it first to enroll a new device.',
                 'error_code': 'already_enabled'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(two_factor.start_enrollment(setting, request.user.username))


@extend_schema_view(
    post=extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
        description=(
            'Completes enrollment with {code} from the authenticator app. '
            'Returns the single-use backup codes — shown once and never again.'
        ),
    )
)
class TwoFactorEnableView(APIView):
    """POST /api/profile/2fa/enable/"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'mfa'

    def post(self, request):
        setting = _setting(request.user)
        try:
            codes = two_factor.confirm_enrollment(setting, request.data.get('code', ''))
        except ValueError as exc:
            return Response(
                {'error': str(exc), 'error_code': 'mfa_code_invalid'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            'backup_codes': codes,
            'message': 'Save these recovery codes now — they are shown only once.',
            **two_factor.public_status(setting),
        })


@extend_schema_view(
    post=extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
        description='Turns 2FA off. Requires the account password in {password}.',
    )
)
class TwoFactorDisableView(APIView):
    """POST /api/profile/2fa/disable/"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'mfa'

    def post(self, request):
        password = request.data.get('password')
        if not password:
            return Response(
                {'error': 'Your password is required to turn off two-factor authentication.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(password):
            return Response(
                {'error': 'That password is not correct.', 'error_code': 'invalid_password'},
                status=status.HTTP_403_FORBIDDEN,
            )

        setting = _setting(request.user)
        two_factor.disable(setting)
        return Response(two_factor.public_status(setting))


@extend_schema_view(
    post=extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
        description='Issues a fresh set of backup codes, invalidating the old ones. Requires {password}.',
    )
)
class TwoFactorBackupCodesView(APIView):
    """POST /api/profile/2fa/backup-codes/"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'mfa'

    def post(self, request):
        password = request.data.get('password')
        if not password or not request.user.check_password(password):
            return Response(
                {'error': 'Your password is required to regenerate recovery codes.',
                 'error_code': 'invalid_password'},
                status=status.HTTP_403_FORBIDDEN,
            )

        setting = _setting(request.user)
        if not setting.two_factor_enabled:
            return Response(
                {'error': 'Enable two-factor authentication first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        codes = two_factor.regenerate_backup_codes(setting)
        return Response({
            'backup_codes': codes,
            'message': 'Your previous recovery codes no longer work.',
            **two_factor.public_status(setting),
        })
