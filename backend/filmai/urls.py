from dj_rest_auth.registration.views import ResendEmailVerificationView
from dj_rest_auth.views import LogoutView
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser

from catalogo.reviews import (
    CalificacionDetailView,
    CalificacionesView,
    MisCalificacionesView,
    ResenaTextoView,
)
from filmai.documentation import documentacion_para_staff
from usuarios.authentication import RefreshSesionView
from usuarios.cuenta import DesactivarCuentaView, PreferenciasView
from usuarios.perfil import AvataresView, CambiarContrasenaView, PerfilView
from usuarios.views import (
    ConfirmarCorreoView,
    CSRFTokenView,
    GoogleLogin,
    LoginView,
    RecuperarContrasenaView,
    RegisterView,
    RestablecerContrasenaView,
    UsernameDisponibleView,
    con_codigo_exito,
)

handler404 = "filmai.views.custom_404"
handler500 = "filmai.views.custom_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/schema/",
        documentacion_para_staff(
            SpectacularAPIView.as_view(
                permission_classes=[IsAdminUser],
                authentication_classes=[SessionAuthentication],
            ),
            recurso="el esquema OpenAPI",
        ),
        name="schema",
    ),
    path(
        "api/docs/",
        documentacion_para_staff(
            SpectacularSwaggerView.as_view(
                url_name="schema",
                permission_classes=[IsAdminUser],
                authentication_classes=[SessionAuthentication],
            ),
            recurso="Swagger UI",
        ),
        name="swagger-ui",
    ),
    path("api/catalogo/", include("catalogo.urls")),
    path("api/lists/", include("listas.urls")),
    # C-08. El `{id}` es la pk de la Calificacion; `/texto/` borra solo el
    # texto y conserva la nota, mientras que la ruta sin sufijo borra las dos.
    path("api/reviews/", CalificacionesView.as_view(), name="calificaciones"),
    # Antes de `<int:calificacion_id>/` no hace falta desambiguar (`mias` no
    # es un entero), pero se declara primero por claridad de lectura.
    path(
        "api/reviews/mias/", MisCalificacionesView.as_view(), name="mis_calificaciones"
    ),
    path(
        "api/reviews/<int:calificacion_id>/",
        CalificacionDetailView.as_view(),
        name="calificacion_detail",
    ),
    path(
        "api/reviews/<int:calificacion_id>/texto/",
        ResenaTextoView.as_view(),
        name="resena_texto",
    ),
    path("api/profile/", PerfilView.as_view(), name="perfil"),
    path("api/avatars/", AvataresView.as_view(), name="avatares"),
    path("api/preferences/", PreferenciasView.as_view(), name="preferencias"),
    path(
        "api/account/deactivate/",
        DesactivarCuentaView.as_view(),
        name="desactivar_cuenta",
    ),
    path(
        "api/profile/change-password/",
        CambiarContrasenaView.as_view(),
        name="cambiar_contrasena",
    ),
    # El alias previo también exige contraseña actual y cierra las sesiones.
    # Se registra con y sin slash: dj-rest-auth expone ``password/change/?`` y
    # ``token/refresh/?``, y sin este control las variantes sin slash eludirían
    # la contraseña actual y la revocación por cambio de contraseña.
    path(
        "api/auth/password/change/",
        CambiarContrasenaView.as_view(),
        name="rest_password_change",
    ),
    path(
        "api/auth/password/change",
        CambiarContrasenaView.as_view(),
        name="rest_password_change_no_slash",
    ),
    path("api/auth/token/refresh/", RefreshSesionView.as_view(), name="token_refresh"),
    path(
        "api/auth/token/refresh",
        RefreshSesionView.as_view(),
        name="token_refresh_no_slash",
    ),
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
    path(
        "api/auth/logout/",
        con_codigo_exito(LogoutView.as_view(), "logged_out"),
        name="rest_logout",
    ),
    path("api/auth/", include("dj_rest_auth.urls")),
    path(
        "api/auth/registration/",
        con_codigo_exito(
            RegisterView.as_view(),
            "registration_pending_confirmation",
            status.HTTP_201_CREATED,
        ),
        name="rest_register",
    ),
    path(
        "api/auth/registration/verify-email/",
        ConfirmarCorreoView.as_view(),
        name="rest_verify_email",
    ),
    path(
        "api/auth/registration/resend-email/",
        con_codigo_exito(
            ResendEmailVerificationView.as_view(), "confirmation_email_sent"
        ),
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
