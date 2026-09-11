"""
Configuración de URLs de FilmAI.

PARÁMETROS EN URLs:
===================

Route Parameters (en la ruta):
- account-confirm-email/<key>: Clave de confirmación de email (allauth)

Query Parameters (en el body o URL):
- /api/auth/login/: email/username + password (body JSON)
- /api/auth/registration/: correo, nombre_usuario, nombre, apellido, fecha_nacimiento, genero, password (body JSON)
- /api/auth/password/reset/: email (body JSON)
- /api/auth/password/reset/confirm/: uid, token, password1, password2 (body JSON)
- /api/auth/username-available/: nombre_usuario (body JSON)
- /api/auth/google/: id_token + campos extra (body JSON)

Todos los parámetros son validados en los serializers correspondientes.
"""

from dj_rest_auth.registration.views import ResendEmailVerificationView
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from usuarios.views import (
    ConfirmarCorreoView,
    CSRFTokenView,
    GoogleLogin,
    LoginView,
    RecuperarContrasenaView,
    RegisterView,
    RestablecerContrasenaView,
    UsernameDisponibleView,
)

# Manejadores personalizados de errores HTTP
handler404 = "filmai.views.custom_404"
handler500 = "filmai.views.custom_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Deben preceder a dj-rest-auth para usar el flujo propio de recuperación.
    path("api/auth/password/reset/", RecuperarContrasenaView.as_view(), name="rest_password_reset"),
    path("api/auth/password/reset/confirm/", RestablecerContrasenaView.as_view(), name="rest_password_reset_confirm"),
    # Tolera una cookie JWT obsoleta durante un nuevo inicio de sesión.
    path("api/auth/login/", LoginView.as_view(), name="rest_login"),
    path("api/auth/", include("dj_rest_auth.urls")),
    # Registro propio y confirmación de email.
    path("api/auth/registration/", RegisterView.as_view(), name="rest_register"),
    # Distingue enlaces expirados, inválidos o ya confirmados (CU-002).
    path("api/auth/registration/verify-email/", ConfirmarCorreoView.as_view(), name="rest_verify_email"),
    path("api/auth/registration/resend-email/", ResendEmailVerificationView.as_view(), name="rest_resend_email"),
    # Rutas requeridas por allauth al construir enlaces de email.
    # El parámetro key usa un patrón específico (alfanumérico + guiones + colon).
    re_path(
        r"^api/auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$",
        TemplateView.as_view(),
        name="account_confirm_email",
    ),
    path("api/auth/registration/account-email-verification-sent/", TemplateView.as_view(), name="account_email_verification_sent"),
    path("api/auth/google/", GoogleLogin.as_view(), name="google_login"),
    # Entrega el token CSRF para mutaciones autenticadas por cookie.
    path("api/auth/csrf/", CSRFTokenView.as_view(), name="csrf_token"),
    path("api/auth/username-available/", UsernameDisponibleView.as_view(), name="username_disponible"),
]
