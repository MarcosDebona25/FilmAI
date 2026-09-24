"""Validación de sesiones JWT, incluida su renovación por cookie."""

from dj_rest_auth.jwt_auth import CookieTokenRefreshSerializer, get_refresh_view
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenRefreshSerializer


class RefreshSesionSerializer(CookieTokenRefreshSerializer):
    def validate(self, attrs):
        request = self.context["request"]
        # Un token enviado explícitamente no depende de credenciales ambientales.
        if not request.data.get("refresh"):
            SessionAuthentication().enforce_csrf(request)
        token = self.extract_refresh_token()
        refresh = self.token_class(token)
        # SimpleJWT comprueba el hash de contraseña en access, pero no en refresh.
        JWTAuthentication().get_user(refresh)
        return TokenRefreshSerializer.validate(self, {"refresh": token})


class RefreshSesionView(get_refresh_view()):
    serializer_class = RefreshSesionSerializer
