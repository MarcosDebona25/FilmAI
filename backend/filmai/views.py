"""Respuestas JSON para errores de Django fuera de DRF."""

from django.http import JsonResponse


def custom_404(request, exception=None):
    """Devuelve un 404 JSON."""
    return JsonResponse(
        {"detail": "La ruta solicitada no existe."},
        status=404,
    )


def custom_500(request):
    """Devuelve un 500 JSON sin detalles internos."""
    return JsonResponse(
        {"detail": "Error interno del servidor."},
        status=500,
    )
