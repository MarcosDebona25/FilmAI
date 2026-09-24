from dj_rest_auth.registration.views import ResendEmailVerificationView
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from usuarios.authentication import RefreshSesionView
from usuarios.perfil import CambiarContrasenaView, PerfilView
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

handler404 = "filmai.views.custom_404"
handler500 = "filmai.views.custom_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[]),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[]),
        # Swagger UI view with no permission restrictions; consider authentication in production
        name="swagger-ui",
    ),
    path("api/catalogo/", include("catalogo.urls")),
    path("api/lists/", include("listas.urls")),
    path("api/profile/", PerfilView.as_view(), name="perfil"),
    path(
        "api/profile/change-password/",
        CambiarContrasenaView.as_view(),
        name="cambiar_contrasena",
    ),
    # El alias previo también exige contraseña actual y cierra las sesiones.
    path(
        "api/auth/password/change/",
        CambiarContrasenaView.as_view(),
        name="rest_password_change",
    ),
    path("api/auth/token/refresh/", RefreshSesionView.as_view(), name="token_refresh"),
    path(
        "api/auth/password/reset/",
        RecuperarContrasenaView.as_view(),
        name="rest_password_reset",
    ),
    path(
        "api/auth/password/reset/confirm/",
        RestablecerContrasenaView.as_view(),
        name="rest_password_reset_confirm",
    ),
    path("api/auth/login/", LoginView.as_view(), name="rest_login"),
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", RegisterView.as_view(), name="rest_register"),
    path(
        "api/auth/registration/verify-email/",
        ConfirmarCorreoView.as_view(),
        name="rest_verify_email",
    ),
    path(
        "api/auth/registration/resend-email/",
        ResendEmailVerificationView.as_view(),
        name="rest_resend_email",
    ),
    # ``\w`` también permite guion bajo.
    re_path(
        r"^api/auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$",
        TemplateView.as_view(),
        name="account_confirm_email",
    ),
    path(
        "api/auth/registration/account-email-verification-sent/",
        TemplateView.as_view(),
        name="account_email_verification_sent",
    ),
    path("api/auth/google/", GoogleLogin.as_view(), name="google_login"),
    path("api/auth/csrf/", CSRFTokenView.as_view(), name="csrf_token"),
    path(
        "api/auth/username-available/",
        UsernameDisponibleView.as_view(),
        name="username_disponible",
    ),
]
