from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Usuario


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
    readonly_fields = ("fecha_registro", "last_login", "google_id")

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
                    "tema",
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
                    "password1",
                    "password2",
                ),
            },
        ),
    )
