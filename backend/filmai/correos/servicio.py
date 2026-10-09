"""Envío único de los cuatro correos de cuenta, en el idioma del destinatario."""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

CASOS = frozenset(
    {
        "confirmacion_registro",
        "confirmacion_correo",
        "restablecer_contrasena",
        "contrasena_actualizada",
    }
)


def vigencia_en_horas(caso):
    """La vigencia del enlace sale de la configuración, no de la plantilla."""
    if caso in {"confirmacion_registro", "confirmacion_correo"}:
        return settings.ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS * 24
    if caso == "restablecer_contrasena":
        return settings.PASSWORD_RESET_TIMEOUT // 3600
    return None


def enviar_correo(caso, destinatario, contexto, idioma):
    """Renderiza una variante completa y delega en el backend de correo Django."""
    if caso not in CASOS or idioma not in settings.IDIOMAS_SOPORTADOS:
        raise ValueError("Caso o idioma de correo no soportado.")
    contexto = {
        **contexto,
        "idioma": idioma,
        "anio": timezone.now().year,
        # La notificación no lleva token: enlaza al inicio de sesión real.
        "enlace_correo": f"{settings.FRONTEND_URL}/login/"
        if caso == "contrasena_actualizada"
        else contexto.get("activate_url") or contexto.get("reset_url"),
        "expiry_hours": vigencia_en_horas(caso),
        "color_secundario": "#a0a0a8"
        if caso == "restablecer_contrasena"
        else "#777777",
    }
    prefijo = f"correos/{caso}/{idioma}"
    asunto = " ".join(
        render_to_string(f"{prefijo}/subject.txt", contexto).splitlines()
    ).strip()
    texto = render_to_string(f"{prefijo}/message.txt", contexto)
    html = render_to_string(f"{prefijo}/message.html", contexto)
    texto = texto.strip()
    html = html.strip()
    return send_mail(
        asunto, texto, settings.DEFAULT_FROM_EMAIL, [destinatario], html_message=html
    )
