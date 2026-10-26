from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Usuario

# Campos que otorgan poder. Quien no es superusuario los ve pero no los cambia:
# con `change_usuario` solo se puede editar a otros usuarios, no concederse más
# privilegios.
CAMPOS_DE_PRIVILEGIO = ("is_superuser", "is_staff", "groups", "user_permissions")


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """Admin para el modelo personalizado de usuario.

    Adapta `UserAdmin` de Django a los campos de `usuarios.Usuario`
    (correo, nombre_usuario, nombre, apellido, etc.) en lugar de los
    campos por defecto de `auth.User`.
    """

    # --- Listado ---
    list_display = (
        "correo",
        "nombre_usuario",
        "nombre",
        "apellido",
        "estado",
        "is_staff",
    )
    list_filter = ("estado", "is_staff", "is_superuser", "genero")
    search_fields = ("correo", "nombre_usuario", "nombre", "apellido")
    ordering = ("correo",)

    # --- Campos de solo lectura ---
    # Estos campos pueden consultarse pero no modificarse manualmente
    readonly_fields = (
        "fecha_registro",
        "fecha_aceptacion_terminos",
        "last_login",
        "google_id",
    )

    # --- Formulario de edición ---
    fieldsets = (
        (None, {"fields": ("correo", "password")}),
        (
            "Información personal",
            {
                "fields": (
                    "nombre_usuario",
                    "nombre",
                    "apellido",
                    "fecha_nacimiento",
                    "genero",
                    "pais",
                    "avatar_id",
                )
            },
        ),
        (
            "Estado y permisos",
            {
                "fields": (
                    "estado",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Preferencias",
            {
                "fields": (
                    "perfil_publico",
                    "notif_recomendaciones",
                    "notif_resenas",
                    "notif_novedades",
                )
            },
        ),
        (
            "Información del sistema",
            {
                "fields": (
                    "fecha_registro",
                    "fecha_aceptacion_terminos",
                    "last_login",
                    "google_id",
                )
            },
        ),
    )

    # --- Formulario de creación ---
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "correo",
                    "nombre_usuario",
                    "nombre",
                    "apellido",
                    "fecha_nacimiento",
                    "genero",
                    "pais",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    # --- Límites para quien no es superusuario ---
    # `UserAdmin` de Django trata «puede cambiar usuarios» como «administra
    # todo»: sin esto, un staff con solo `change_usuario` se marca superusuario,
    # se da permisos o fija la contraseña de un superusuario (auditoría F5).

    def get_queryset(self, request):
        usuarios = super().get_queryset(request)
        if request.user.is_superuser:
            return usuarios
        return usuarios.exclude(is_superuser=True)

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        if request.user.is_superuser:
            return campos
        return (*campos, *CAMPOS_DE_PRIVILEGIO)

    def _puede_actuar_sobre(self, request, obj):
        """Regla por objeto, común a editar y borrar.

        Nadie sin ser superusuario toca a un superusuario ni a otro staff (cuya
        contraseña o cuya baja le cambiaría los permisos al sistema); sí a sí
        mismo y a usuarios comunes. Sin objeto (listado, acciones masivas) no se
        decide acá: Django vuelve a preguntar por cada fila.
        """
        if request.user.is_superuser or obj is None:
            return True
        if obj.is_superuser:
            return False
        return obj.pk == request.user.pk or not obj.is_staff

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._puede_actuar_sobre(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._puede_actuar_sobre(
            request, obj
        )


# --- Modelos de terceros: solo superusuarios (revisión de seguridad, 26/10/2026) ---
#
# Los límites de staff parcial de F5 cubren a `Usuario`, pero allauth, simplejwt y
# `Group` vienen con su admin original:
# - `SocialAccount` deja editar `user` y `uid`: con ese permiso, un staff vinculaba
#   su propio Google a un superusuario y entraba como él.
# - `OutstandingToken` muestra el refresh JWT entero: copiándolo se obtiene una
#   sesión de cualquier usuario.
# - `Group` permite armarse un grupo con todos los permisos.
# Se importan sus admins primero, para que ya estén registrados (el orden de
# carga sigue `INSTALLED_APPS`, y `usuarios` va antes que ellos).
import allauth.account.admin  # noqa: E402
import allauth.socialaccount.admin  # noqa: E402, F401
import django.contrib.auth.admin  # noqa: E402, F401
import rest_framework_simplejwt.token_blacklist.admin  # noqa: E402, F401
from allauth.account.models import EmailAddress  # noqa: E402
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402
from rest_framework_simplejwt.token_blacklist.models import (  # noqa: E402
    BlacklistedToken,
    OutstandingToken,
)

MODELOS_SOLO_SUPERUSUARIO = (
    SocialAccount,
    SocialApp,
    SocialToken,
    EmailAddress,
    OutstandingToken,
    BlacklistedToken,
    Group,
)


def _solo_para_superusuarios(clase_admin):
    """La misma clase de admin, visible y editable solo por superusuarios."""

    class SoloSuperusuarios(clase_admin):
        def has_module_permission(self, request):
            return request.user.is_superuser

        def has_view_permission(self, request, obj=None):
            return request.user.is_superuser

        def has_add_permission(self, request, *args, **kwargs):
            return request.user.is_superuser and super().has_add_permission(
                request, *args, **kwargs
            )

        def has_change_permission(self, request, obj=None):
            return request.user.is_superuser and super().has_change_permission(
                request, obj
            )

        def has_delete_permission(self, request, obj=None):
            return request.user.is_superuser and super().has_delete_permission(
                request, obj
            )

    SoloSuperusuarios.__name__ = f"SoloSuperusuarios{clase_admin.__name__}"
    return SoloSuperusuarios


for _modelo in MODELOS_SOLO_SUPERUSUARIO:
    _original = type(admin.site._registry[_modelo])
    admin.site.unregister(_modelo)
    admin.site.register(_modelo, _solo_para_superusuarios(_original))
