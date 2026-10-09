"""Mapa entre idioma efectivo de aplicación y variante del proveedor."""

from django.conf import settings

from filmai.idioma import idioma_efectivo


def idioma_tmdb(request):
    return settings.IDIOMAS_TMDB[idioma_efectivo(request)]
