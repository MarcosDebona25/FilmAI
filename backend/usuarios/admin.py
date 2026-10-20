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

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if request.user.is_superuser or obj is None:
            return True
        # Nadie sin ser superusuario toca a un superusuario ni a otro staff
        # (cuya contraseña le daría sus permisos); sí a sí mismo y a usuarios comunes.
        if obj.is_superuser:
            return False
        return obj.pk == request.user.pk or not obj.is_staff
