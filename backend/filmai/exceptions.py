"""
Manejador global de excepciones para FilmAI.

Proporciona respuestas HTTP consistentes y códigos apropiados para cada tipo
de error, reemplazando los códigos genéricos de DRF cuando existe un código
más representativo del error producido.
"""

import logging

from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def filmai_exception_handler(exc, context):
    """
    Manejador global de excepciones de FilmAI.

    Prioriza códigos HTTP específicos sobre los genéricos de DRF:
    - 400: ValidationError (datos inválidos)
    - 401: NotAuthenticated, AuthenticationFailed (autenticación requerida/fallida)
    - 403: PermissionDenied (permisos insuficientes)
    - 404: Http404 (recurso no encontrado)
    - 405: MethodNotAllowed (método HTTP no permitido)
    - 429: Throttled (límite de solicitudes excedido)
    - 500: Errores no manejados (solo en desarrollo)

    Para errores de TMDB, delega al manejador especializado.
    """
    # Importar aquí para evitar dependencias circulares
    from catalogo.exceptions import tmdb_exception_handler

    # Primero intentar con el manejador de TMDB
    response = tmdb_exception_handler(exc, context)
    if response is not None:
        return response

    # Manejador estándar de DRF
    response = drf_exception_handler(exc, context)

    if response is None:
        # Error no manejado por DRF (ej: Exception genérico)
        # En producción, devolver 500 genérico sin detalles
        # En desarrollo, incluir detalles para debugging
        from django.conf import settings

        if settings.DEBUG:
            logger.exception("Error no manejado: %s", exc)
            return Response(
                {"detail": f"Error interno del servidor: {exc!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            logger.exception("Error no manejado: %s", exc)
            return Response(
                {"detail": "Error interno del servidor."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Mejorar mensajes de error para mayor claridad
    if isinstance(exc, NotAuthenticated):
        response.data = {"detail": "Autenticación requerida. Por favor, iniciá sesión."}
    elif isinstance(exc, AuthenticationFailed):
        response.data = {
            "detail": "Credenciales inválidas. Verificá tu correo/nombre de usuario y contraseña."
        }
    elif isinstance(exc, PermissionDenied):
        response.data = {"detail": "No tenés permisos para realizar esta acción."}
    elif isinstance(exc, MethodNotAllowed):
        response.data = {
            "detail": f"Método HTTP {exc.detail} no permitido para este endpoint."
        }
    elif isinstance(exc, ValidationError):
        # DRF ya formatea ValidationError correctamente, no modificar
        pass

    return response
