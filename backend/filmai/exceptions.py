"""Manejador global de excepciones de FilmAI."""

import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from catalogo.exceptions import TMDBError, tmdb_exception_handler

logger = logging.getLogger(__name__)


def filmai_exception_handler(exc, context):
    """Unifica errores DRF y conserva el mapeo especializado de TMDB."""
    if isinstance(exc, TMDBError):
        return tmdb_exception_handler(exc, context)

    response = drf_exception_handler(exc, context)

    if response is None:
        from django.conf import settings

        logger.exception("Error no manejado: %s", exc)
        if settings.DEBUG:
            return Response(
                {"detail": f"Error interno del servidor: {exc!s}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"detail": "Error interno del servidor."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, NotAuthenticated):
        response.data = {"detail": "Autenticación requerida. Por favor, iniciá sesión."}
    elif isinstance(exc, AuthenticationFailed):
        response.data = {
            "detail": "Credenciales inválidas. Verificá tu correo/nombre de usuario y contraseña."
        }
    elif isinstance(exc, PermissionDenied):
        response.data = {"detail": "No tenés permisos para realizar esta acción."}
    elif isinstance(exc, Http404):
        response.data = {"detail": "El recurso solicitado no existe."}
    elif isinstance(exc, MethodNotAllowed):
        detalle = (
            exc.detail[0]
            if isinstance(exc.detail, (list, tuple)) and exc.detail
            else str(exc.detail)
        )
        response.data = {
            "detail": f"Método HTTP {detalle} no permitido para este endpoint."
        }
    elif isinstance(exc, Throttled):
        response.data = {
            "detail": "Demasiadas solicitudes. Intentá de nuevo más tarde."
        }
    elif isinstance(exc, ValidationError):
        pass

    return response
