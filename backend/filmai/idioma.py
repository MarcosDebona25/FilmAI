"""Idioma de aplicación sin activar la traducción global de Django."""

from django.conf import settings
from django.utils.translation.trans_real import parse_accept_lang_header


def idioma_efectivo(request, usuario=None):
    """Prioriza la cuenta, las preferencias HTTP con peso y finalmente EN."""
    if usuario is None:
        usuario = getattr(request, "user", None)
    guardado = getattr(usuario, "idioma", None)
    if guardado in settings.IDIOMAS_SOPORTADOS:
        return guardado

    encabezado = request.headers.get("Accept-Language", "") if request else ""
    for idioma, peso in parse_accept_lang_header(encabezado):
        base = idioma.split("-", 1)[0]
        if peso > 0 and base in settings.IDIOMAS_SOPORTADOS:
            return base
    return settings.IDIOMA_POR_DEFECTO
