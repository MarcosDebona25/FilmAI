from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"

    def ready(self):
        # Conecta la señal que crea listas predeterminadas y chat por defecto.
        from . import signals  # noqa: F401
