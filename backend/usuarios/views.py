"""
Vistas de autenticación.

`GoogleLogin` expone el login social de Google (flujo `id_token`) de
dj-rest-auth. El registro tradicional y el login por credenciales los proveen
los endpoints de `dj_rest_auth` montados en `filmai/urls.py`.
"""

from typing import ClassVar

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import (
    RegisterView as BaseRegisterView,
)
from dj_rest_auth.registration.views import (
    SocialLoginView,
)
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Usuario
from .serializers import GoogleSocialLoginSerializer
from .validators import USERNAME_REGEX


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


class UsernameDisponibleView(APIView):
    """Chequeo de disponibilidad de nombre de usuario en tiempo real (A-05).

    Devuelve `{"disponible": false}` si el formato no es válido (CU-001:
    alfanumérico, 5-25 caracteres) o si ya existe un usuario con ese nombre
    (comparación insensible a mayúsculas, igual que `validate_nombre_usuario`).
    """

    permission_classes: ClassVar[list] = [permissions.AllowAny]

    def get(self, request):
        username = request.query_params.get("username", "")
        if not USERNAME_REGEX.fullmatch(username):
            return Response({"disponible": False})
        disponible = not Usuario.objects.filter(
            nombre_usuario__iexact=username
        ).exists()
        return Response({"disponible": disponible})
