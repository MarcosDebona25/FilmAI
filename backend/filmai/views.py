"""Respuestas JSON para errores de Django fuera de DRF."""

from django.conf import settings
from django.http import JsonResponse

from .errores.sobre import construir_sobre


def custom_404(request, exception=None):
    """Devuelve un 404 JSON."""
    sobre = construir_sobre("not_found", 404, debug=settings.DEBUG)
    return JsonResponse(
        sobre,
        status=404,
    )


def custom_500(request):
    """Devuelve un 500 JSON sin detalles internos."""
    sobre = construir_sobre("server_error", 500, debug=settings.DEBUG)
    return JsonResponse(
        sobre,
        status=500,
    )
