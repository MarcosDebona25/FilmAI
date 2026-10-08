"""Adaptadores de allauth para el modelo de usuario de FilmAI."""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_date

from filmai.correos.servicio import enviar_correo
from filmai.idioma import idioma_efectivo

from .models import EstadoCuenta, TipoGenero, Usuario


class UsuarioAccountAdapter(DefaultAccountAdapter):
    """Adaptador de cuenta para el registro tradicional (dj-rest-auth)."""

    def save_user(self, request, user, form, commit=True):
        """Mapea los campos de allauth a los de ``Usuario``."""
        data = form.cleaned_data

        user.correo = data.get("correo", user.correo)
        user.nombre_usuario = data.get("nombre_usuario")

        user.nombre = data.get("nombre", "")
        user.apellido = data.get("apellido", "")

        user.fecha_nacimiento = data.get("fecha_nacimiento")
        user.genero = data.get("genero", TipoGenero.NO_ESPECIFICA)
        user.idioma = idioma_efectivo(request, user)

        if "password1" in data:
            user.set_password(data["password1"])
        else:
            user.set_unusable_password()

        if commit:
            with transaction.atomic():
                user.save()

        return user

    def confirm_email(self, request, email_address):
        """Activa la cuenta al confirmar su correo de forma atómica."""
        with transaction.atomic():
            usuario = Usuario.objects.select_for_update().get(pk=email_address.user_id)
            if usuario.estado == EstadoCuenta.BAJA:
                return False
            usuario.estado = EstadoCuenta.ACTIVA
            usuario.save(update_fields=["estado"])
            return super().confirm_email(request, email_address)

    def send_mail(self, template_prefix, email, context):
        casos = {
            "account/email/email_confirmation_signup": "confirmacion_registro",
            "account/email/email_confirmation": "confirmacion_correo",
        }
        caso = casos.get(template_prefix)
        if caso is None:
            return super().send_mail(template_prefix, email, context)
        # Idioma guardado del destinatario; si es nulo, el del request; si no, inglés.
        idioma = idioma_efectivo(
            context.get("request") or getattr(self, "request", None),
            context.get("user"),
        )
        return enviar_correo(caso, email, context, idioma)

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Envía la confirmación a la pantalla correspondiente de la SPA."""
        return f"{settings.FRONTEND_URL}/confirmar-correo/{emailconfirmation.key}/"


class UsuarioSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Adaptador social (Google OAuth) para `usuarios.Usuario`."""

    def save_user(self, request, sociallogin, form=None):
        """Persiste el alta social de forma atómica."""
        with transaction.atomic():
            return super().save_user(request, sociallogin, form)

    def populate_user(self, request, sociallogin, data):
        """Construye un perfil nuevo sin sobrescribir una cuenta vinculada."""
        cuenta_existente = (
            SocialAccount.objects.select_related("user")
            .filter(
                provider=sociallogin.account.provider,
                uid=sociallogin.account.uid,
            )
            .first()
        )

        if cuenta_existente:
            return cuenta_existente.user

        user = super().populate_user(request, sociallogin, data)
        nombre = data.get("given_name") or data.get("first_name") or ""
        apellido = data.get("family_name") or data.get("last_name") or ""

        if not nombre and data.get("name"):
            partes = data["name"].strip().split(" ", 1)
            nombre = partes[0]
            apellido = partes[1] if len(partes) > 1 else ""

        user.nombre = nombre
        user.apellido = apellido
        user.estado = EstadoCuenta.ACTIVA
        user.idioma = idioma_efectivo(request, user)

        extra = getattr(request, "google_extra", {})
        user.nombre_usuario = extra.get("nombre_usuario") or ""

        fecha = extra.get("fecha_nacimiento")
        user.fecha_nacimiento = parse_date(fecha) if isinstance(fecha, str) else fecha

        user.genero = extra.get("genero") or TipoGenero.NO_ESPECIFICA

        return user
