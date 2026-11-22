"""Envío único de los cuatro correos de cuenta, en el idioma del destinatario."""

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from kombu.exceptions import OperationalError
from redis.exceptions import RedisError

from filmai.tasks import enviar_correo_tarea

CASOS = frozenset(
    {
        "confirmacion_registro",
        "confirmacion_correo",
        "restablecer_contrasena",
        "contrasena_actualizada",
    }
)


class CorreoNoEncolado(Exception):
    """El broker (Redis) no aceptó la tarea: el correo no va a salir.

    Es lo único que `enviar_correo` levanta por un fallo de infraestructura. Un
    proveedor caído ya no llega hasta acá: se reintenta dentro de la tarea.
    """


def vigencia_en_horas(caso):
    """La vigencia del enlace sale de la configuración, no de la plantilla."""
    if caso in {"confirmacion_registro", "confirmacion_correo"}:
        return settings.ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS * 24
    if caso == "restablecer_contrasena":
        return settings.PASSWORD_RESET_TIMEOUT // 3600
    return None


def enviar_correo(caso, destinatario, contexto, idioma):
    """Renderiza una variante completa y la encola para que la envíe el worker.

    Levanta `CorreoNoEncolado` si el broker no responde.
    """
    if caso not in CASOS or idioma not in settings.IDIOMAS_SOPORTADOS:
        raise ValueError("Caso o idioma de correo no soportado.")
    contexto = {
        **contexto,
        "idioma": idioma,
        "anio": timezone.now().year,
        # Base de la imagen del logo (`/correos/ticket.png`, en `frontend/public/`).
        "url_app": settings.FRONTEND_URL.rstrip("/"),
        # La notificación no lleva token: enlaza al inicio de sesión real.
        "enlace_correo": f"{settings.FRONTEND_URL}/login/"
        if caso == "contrasena_actualizada"
        else contexto.get("activate_url") or contexto.get("reset_url"),
        "expiry_hours": vigencia_en_horas(caso),
    }
    prefijo = f"correos/{caso}/{idioma}"
    asunto = " ".join(
        render_to_string(f"{prefijo}/subject.txt", contexto).splitlines()
    ).strip()
    texto = render_to_string(f"{prefijo}/message.txt", contexto)
    html = render_to_string(f"{prefijo}/message.html", contexto)
    texto = texto.strip()
    html = html.strip()
    # Se encola ya renderizado: el worker no lee la base ni las plantillas. Los
    # `argsrepr` redactan lo que el worker imprime al recibir la tarea (el
    # destinatario y el enlace del correo no deben quedar en sus logs).
    try:
        enviar_correo_tarea.apply_async(
            args=(caso, asunto, texto, html, destinatario),
            argsrepr=f"({caso!r}, <asunto y cuerpo redactados>, <correo redactado>)",
            # Sin reintentos de publicación: con el broker caído el pedido HTTP
            # falla en segundos y no se queda esperando.
            retry=False,
        )
    except (OperationalError, RedisError) as error:
        raise CorreoNoEncolado(type(error).__name__) from error
