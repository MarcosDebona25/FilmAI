"""
URL configuration for filmai project.

Rutas de autenticación (docs/05 — A-01..A-09):

- `api/auth/`                 → dj-rest-auth (login, logout, password reset,
                                 password change, token verify/refresh).
- `api/auth/registration/`    → dj-rest-auth registration (registro,
                                 verify-email, resend-email).
- `api/auth/google/`          → login social con Google (id_token).
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

urlpatterns = [
    path("admin/", admin.site.urls),
    # Recuperación de contraseña custom (CU-020): serializers propios con
    # campos `password1`/`password2`, email en español y rate limit 1/min.
    # Van ANTES del include() para pisar las rutas de dj-rest-auth.
    re_path(
        r"^api/auth/password/reset/?$",
        RecuperarContrasenaView.as_view(),
        name="rest_password_reset",
    ),
    re_path(
        r"^api/auth/password/reset/confirm/?$",
        RestablecerContrasenaView.as_view(),
        name="rest_password_reset_confirm",
    ),
    # Login custom: usa LenientJWTCookieAuthentication para no revientar
    # cuando el browser manda una cookie JWT vieja (p.ej. después de re-seed).
    re_path(
        r"^api/auth/login/?$",
        LoginView.as_view(),
        name="rest_login",
    ),
    path("api/auth/", include("dj_rest_auth.urls")),
    # Registro (view custom que omite `complete_signup`) + confirmación de email.
    path("api/auth/registration/", RegisterView.as_view(), name="rest_register"),
    # Confirmación custom: distingue expirado/invalido/ya_confirmada (CU-002).
    # Mantiene la ruta que ya usaba el frontend.
    re_path(
        r"^api/auth/registration/verify-email/?$",
        ConfirmarCorreoView.as_view(),
        name="rest_verify_email",
    ),
    re_path(
        r"^api/auth/registration/resend-email/?$",
        ResendEmailVerificationView.as_view(),
        name="rest_resend_email",
    ),
    # TemplateViews que allauth referencia por `reverse()` al construir mails.
    re_path(
        r"^api/auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$",
        TemplateView.as_view(),
        name="account_confirm_email",
    ),
    re_path(
        r"^api/auth/registration/account-email-verification-sent/?$",
        TemplateView.as_view(),
        name="account_email_verification_sent",
    ),
    path("api/auth/google/", GoogleLogin.as_view(), name="google_login"),
    # Entrega la cookie `csrftoken` para que el frontend mande `X-CSRFToken`
    # en las mutaciones (JWT_AUTH_COOKIE_USE_CSRF=True). Ver usuarios.views.
    path("api/auth/csrf/", CSRFTokenView.as_view(), name="csrf_token"),
    # Disponibilidad de nombre de usuario en tiempo real (A-05, docs/04:696).
    path(
        "api/auth/username-available/",
        UsernameDisponibleView.as_view(),
        name="username_disponible",
    ),
]
