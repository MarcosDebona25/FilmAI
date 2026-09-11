"""
Vistas de autenticación.

`GoogleLogin` expone el login social de Google (flujo `id_token`) de
dj-rest-auth. El registro tradicional y el login por credenciales los proveen
los endpoints de `dj_rest_auth` montados en `filmai/urls.py`.
`ConfirmarCorreoView` reemplaza al `VerifyEmailView` de dj-rest-auth para
poder distinguir por qué falló un enlace de confirmación.
"""

import logging
from typing import ClassVar

from allauth.account import app_settings as allauth_account_settings
from allauth.account.internal.flows.email_verification import (
    mark_email_address_as_verified,
)
from allauth.account.models import EmailAddress
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.jwt_auth import JWTCookieAuthentication
from dj_rest_auth.registration.views import (
    RegisterView as BaseRegisterView,
)
from dj_rest_auth.registration.views import (
    SocialLoginView,
)
from dj_rest_auth.views import LoginView as BaseLoginView
from django.core import signing
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Usuario
from .serializers import (
    EnlaceRestablecimientoInvalido,
    GoogleSocialLoginSerializer,
    RecuperarContrasenaSerializer,
    RestablecerContrasenaSerializer,
)
from .throttles import EmailRateThrottle, EmailThrottleStatusMixin
from .validators import USERNAME_REGEX

logger = logging.getLogger(__name__)


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


class LoginView(BaseLoginView):
    """Login que usa ``LenientJWTCookieAuthentication``.

    Evita 401 cuando el browser manda una cookie JWT vieja (p.ej. después de
    re-seed o de que la cuenta fue eliminada).
    """

    authentication_classes = (LenientJWTCookieAuthentication,)


class RegisterView(BaseRegisterView):
    """Registro tradicional sin el `complete_signup` de dj-rest-auth.

    `serializer.save()` ya crea el `EmailAddress` y envía el correo de
    confirmación (`setup_user_email`). No se llama a `complete_signup` porque,
    con `ACCOUNT_EMAIL_VERIFICATION="mandatory"` y nuestro modelo (`is_active`
    es `False` mientras `estado=PENDIENTE`, Opción A1), allauth intentaría
    `perform_login` → `respond_user_inactive` → `reverse("account_inactive")`
    (URL que no montamos), rompiendo el registro.
    """

    def perform_create(self, serializer):
        user = serializer.save(self.request)
        # `setup_user_email` (dentro de serializer.save) creó el EmailAddress
        # pero NO envía el correo. Enviamos la confirmación manualmente:
        # `complete_signup` de dj-rest-auth lo haría vía `perform_login`, que con
        # nuestro modelo (`is_active=False` mientras `estado=PENDIENTE`) rompe
        # con NoReverseMatch de `account_inactive`.
        from allauth.account.models import EmailAddress

        email_address = EmailAddress.objects.filter(user=user, primary=True).first()
        if email_address:
            email_address.send_confirmation(self.request._request, signup=True)
        return user


class GoogleLogin(SocialLoginView):
    """Login/registro con Google OAuth 2.0 (Google Identity Services)."""

    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    serializer_class = GoogleSocialLoginSerializer


class CSRFTokenView(APIView):
    """Entrega la cookie `csrftoken` para el frontend (SPA).

    Con `JWT_AUTH_COOKIE_USE_CSRF=True`, las mutaciones autenticadas por la
    cookie httpOnly `access` exigen el header `X-CSRFToken`. Esta vista (GET)
    fuerza a Django a setear la cookie `csrftoken` (`ensure_csrf_cookie` →
    `get_token` → `CsrfViewMiddleware.process_response`), que el frontend lee y
    devuelve en cada request que modifica datos.
    """

    permission_classes: ClassVar[list] = [permissions.AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        return Response({"detail": "ok"})


class UsernameDisponibleView(APIView):
    """Chequeo de disponibilidad de nombre de usuario en tiempo real (A-05).

    Devuelve `{"disponible": false}` si el formato no es válido (CU-001:
    alfanumérico, 5-25 caracteres) o si ya existe un usuario con ese nombre
    (comparación insensible a mayúsculas, igual que `validate_nombre_usuario`).
    """

    permission_classes: ClassVar[list] = [permissions.AllowAny]
    throttle_classes: ClassVar[list] = [ScopedRateThrottle]
    throttle_scope = "username_disponible"

    def get(self, request):
        username = request.query_params.get("username", "")
        if not USERNAME_REGEX.fullmatch(username):
            return Response({"disponible": False})
        disponible = not Usuario.objects.filter(
            nombre_usuario__iexact=username
        ).exists()
        return Response({"disponible": disponible})


class ConfirmarCorreoView(APIView):
    """Confirma la cuenta a partir del enlace del email (CU-002).

    Reemplaza al `VerifyEmailView` de dj-rest-auth, que responde el mismo
    error genérico para todos los casos. Esta vista decodifica la misma key
    firmada (HMAC + timestamp) que allauth generó en el enlace y distingue:

    - `ok`: email confirmado → `mark_email_address_as_verified` llama al
      adapter (`confirm_email`), que pone la cuenta en estado `ACTIVA`.
    - `expirado`: la key tiene más de `ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS`.
    - `invalido`: firma inválida o el email ya no existe.
    - `ya_confirmada`: el EmailAddress ya estaba verificado (enlace reusado).
    """

    permission_classes: ClassVar[list] = [permissions.AllowAny]

    def post(self, request):
        key = str(request.data.get("key", ""))
        logger.info("ConfirmarCorreo: key recibida (len=%d): %r", len(key), key)
        ttl_segundos = (
            allauth_account_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS * 24 * 3600
        )

        try:
            pk = signing.loads(
                key,
                max_age=ttl_segundos,
                salt=allauth_account_settings.SALT,
            )
        except signing.SignatureExpired:
            logger.info("ConfirmarCorreo: key expirada")
            return Response({"codigo": "expirado"}, status=status.HTTP_400_BAD_REQUEST)
        except (signing.BadSignature, ValueError, TypeError) as exc:
            logger.warning(
                "ConfirmarCorreo: key inválida — %s: %s", type(exc).__name__, exc
            )
            return Response({"codigo": "invalido"}, status=status.HTTP_400_BAD_REQUEST)

        email_address = (
            EmailAddress.objects.filter(pk=pk).select_related("user").first()
        )
        if email_address is None:
            return Response({"codigo": "invalido"}, status=status.HTTP_400_BAD_REQUEST)
        if email_address.verified:
            return Response(
                {"codigo": "ya_confirmada"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Delega en allauth: marca `verified=True` y pasa por nuestro adapter
        # (estado → ACTIVA). Si devuelve None hubo una carrera y otro request
        # la confirmó primero.
        if mark_email_address_as_verified(request._request, email_address) is None:
            return Response(
                {"codigo": "ya_confirmada"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"detail": "ok"})


class RecuperarContrasenaView(EmailThrottleStatusMixin, APIView):
    """POST `/api/auth/password/reset/` — solicitud de restablecimiento.

    CU-020: responde siempre con el mismo mensaje genérico, exista o no el
    correo. Aplica rate limit de 5 solicitudes por día por email (no por IP),
    e informa cuántos intentos restantes le quedan al usuario.
    """

    permission_classes: ClassVar[list] = [permissions.AllowAny]
    throttle_classes: ClassVar[list] = [EmailRateThrottle]

    def post(self, request):
        serializer = RecuperarContrasenaSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": (
                    "Si el correo está registrado, se envió un email con "
                    "instrucciones para restablecer la contraseña."
                )
            }
        )


class RestablecerContrasenaView(APIView):
    """POST `/api/auth/password/reset/confirm/` — nueva contraseña.

    Valida el enlace firmado (`uid`/`token`, válido 1 hora) y la política de
    contraseñas del CU-001. Enlace inválido o vencido →
    `400 {"codigo": "invalido"}`; contraseña inválida → errores de campo.
    """

    permission_classes: ClassVar[list] = [permissions.AllowAny]
    throttle_classes: ClassVar[list] = [ScopedRateThrottle]
    throttle_scope = "restablecer_contrasena"

    def post(self, request):
        serializer = RestablecerContrasenaSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except EnlaceRestablecimientoInvalido:
            return Response({"codigo": "invalido"}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({"detail": "La contraseña fue restablecida."})
