"""API views for authentication: register, login, logout, token lifecycle and me."""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from ..serializers.auth import RegisterSerializer
from ..services import auth_service


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Creates a new account and returns the JWT pair + user so the client
    is signed in immediately after registering.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            message = ' '.join(
                msg for msgs in errors.values()
                for msg in (msgs if isinstance(msgs, list) else [msgs])
            )
            return Response(
                {'error': message or 'Invalid input.', 'field_errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = auth_service.register_user(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password'],
                email=serializer.validated_data.get('email', ''),
            )
        except auth_service.RegistrationError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {**auth_service.issue_tokens(user), 'user': auth_service.get_user_payload(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/auth/login/
    Exchanges username + password for a JWT pair and the user profile.
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = getattr(serializer, 'user', None)
        return Response(
            {**serializer.validated_data, 'user': auth_service.get_user_payload(user)},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Revokes the refresh token (requires auth, refresh sent in the body).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        auth_service.blacklist_refresh(refresh_token)
        return Response({'message': 'Logged out successfully.'})


class MeView(APIView):
    """
    GET /api/auth/me/
    Returns the profile of the token owner.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(auth_service.get_user_payload(request.user))


__all__ = ['RegisterView', 'LoginView', 'LogoutView', 'MeView', 'TokenRefreshView']