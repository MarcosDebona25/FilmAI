"""Validación de sesiones JWT, incluida su renovación por cookie."""

import logging

from dj_rest_auth.jwt_auth import (
    CookieTokenRefreshSerializer,
    JWTCookieAuthentication,
    get_refresh_view,
)
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

logger = logging.getLogger(__name__)


# Vivía en `usuarios/views.py`; se mudó acá el 13/11/2026 para que otras apps
# (la fila «Parecidos» de la ficha, en `catalogo`) la usen sin importar un
# módulo de vistas desde otro.
class LenientJWTCookieAuthentication(JWTCookieAuthentication):
    """Variante que no revienta si la cookie JWT es inválida o está vencida.

    ``JWTCookieAuthentication.authenticate`` lanza ``AuthenticationFailed``
    cuando encuentra una cookie ``access`` que no pasa la validación (expirada,
    de otro seed, blacklistada, etc.).  Eso bloquea endpoints públicos como el
    login: el browser manda la cookie vieja, el auth falla *antes* de llegar a
    la vista y el usuario recibe 401 sin entender por qué.

    Esta sub-clase captura la excepción y devuelve ``None`` (no autenticado),
    igual que cuando no hay cookie.  El endpoint de login sigue funcionando
    porque su permission es ``AllowAny``.

    ``PermissionDenied`` (que `enforce_csrf` lanza cuando falla CSRF con
    ``JWT_AUTH_COOKIE_USE_CSRF``) NO se captura: propagarla produce un 403.
    Tragarla haría que un request sin CSRF válido pase por anónimo y el login
    pierda su protección CSRF siempre que el browser traiga alguna cookie
    ``access`` previa.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except PermissionDenied:
            raise
        except Exception:
            logger.debug(
                "Cookie JWT inválida ignorada en %s", request.path, exc_info=True
            )
            return None


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
