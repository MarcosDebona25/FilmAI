"""Envío único, manteniendo la copia y el formato anteriores a la traducción."""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

CASOS = frozenset(
    {
        "confirmacion_registro",
        "confirmacion_correo",
        "restablecer_contrasena",
        "contrasena_actualizada",
    }
)


def enviar_correo(caso, destinatario, contexto, idioma):
    """Renderiza una variante completa y delega en el backend de correo Django."""
    if caso not in CASOS or idioma not in settings.IDIOMAS_SOPORTADOS:
        raise ValueError("Caso o idioma de correo no soportado.")
    prefijo = f"correos/{caso}/{idioma}"
    asunto = " ".join(
        render_to_string(f"{prefijo}/subject.txt", contexto).splitlines()
    ).strip()
    texto = render_to_string(f"{prefijo}/message.txt", contexto)
    html = None
    if caso != "contrasena_actualizada":
        html = render_to_string(f"{prefijo}/message.html", contexto)
    # Allauth quitaba espacios extremos; los otros dos envíos no lo hacían.
    if caso in {"confirmacion_registro", "confirmacion_correo"}:
        texto = texto.strip()
        html = html.strip()
    return send_mail(
        asunto, texto, settings.DEFAULT_FROM_EMAIL, [destinatario], html_message=html
    )
