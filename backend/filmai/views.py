"""
Vistas de manejo de errores HTTP.

Proporciona respuestas JSON consistentes para errores HTTP que ocurren fuera
del contexto de DRF (ej: rutas no encontradas a nivel de Django).
"""

from django.http import JsonResponse


def custom_404(request, exception=None):
    """
    Manejador personalizado para errores 404 (ruta no encontrada).

    Devuelve una respuesta JSON consistente con el formato de la API,
    en lugar de la página HTML por defecto de Django.
    """
    return JsonResponse(
        {"detail": "La ruta solicitada no existe."},
        status=404,
    )


def custom_500(request):
    """
    Manejador personalizado para errores 500 (error interno del servidor).

    Devuelve una respuesta JSON genérica para no exponer detalles internos.
    """
    return JsonResponse(
        {"detail": "Error interno del servidor."},
        status=500,
    )
