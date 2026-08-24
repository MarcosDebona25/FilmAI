"""
URL configuration for filmai project.

Rutas de autenticación (docs/05 — A-01..A-09):

- `api/auth/`                 → dj-rest-auth (login, logout, password reset,
                                 password change, token verify/refresh).
- `api/auth/registration/`    → dj-rest-auth registration (registro,
                                 verify-email, resend-email).
- `api/auth/google/`          → login social con Google (id_token).
"""

from dj_rest_auth.registration.views import (
    ResendEmailVerificationView,
    VerifyEmailView,
)
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from usuarios.views import GoogleLogin, RegisterView, UsernameDisponibleView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("dj_rest_auth.urls")),
    # Registro (view custom que omite `complete_signup`) + confirmación de email.
    path("api/auth/registration/", RegisterView.as_view(), name="rest_register"),
    re_path(
        r"^api/auth/registration/verify-email/?$",
        VerifyEmailView.as_view(),
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
    # Disponibilidad de nombre de usuario en tiempo real (A-05, docs/04:696).
    path(
        "api/auth/username-available/",
        UsernameDisponibleView.as_view(),
        name="username_disponible",
    ),
]
