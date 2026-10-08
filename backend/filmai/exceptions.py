"""Manejador global de excepciones de FilmAI."""

import logging
import math

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
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

from catalogo.exceptions import (
    TMDBBadRequest,
    TMDBError,
    TMDBNotFound,
    TMDBRateLimited,
    TMDBServerError,
    TMDBTransportError,
    tmdb_exception_handler,
)

from .errores.catalogo import CATALOGO
from .errores.sobre import conservar_legacy, construir_sobre, entradas_validacion

logger = logging.getLogger(__name__)


def _respuesta_legacy(exc, context):
    """Unifica errores DRF y conserva el mapeo especializado de TMDB."""
    if isinstance(exc, TMDBError):
        return tmdb_exception_handler(exc, context)

    response = drf_exception_handler(exc, context)

    if response is None:
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


# Son códigos tipados de excepciones existentes; no se analizan sus mensajes.
_CODIGOS_HEREDADOS = {
    "authentication_failed": "invalid_credentials",
    "nombre_usuario_ocupado": "username_already_used",
    "nombre_lista_duplicado": "list_name_duplicated",
    "item_duplicado": "list_item_duplicated",
    "lista_predeterminada_protegida": "default_list_protected",
    "calificacion_impide_quitar_de_vistas": "rating_blocks_removal_from_watched",
    "calificacion_duplicada": "rating_duplicated",
}


# El manejador TMDB conserva `{"detail": ...}` y su HTTP; aquí solo se le da código.
_CODIGOS_TMDB = {
    TMDBBadRequest: "upstream_bad_request",
    TMDBNotFound: "upstream_not_found",
    TMDBRateLimited: "throttled",
    TMDBServerError: "upstream_error",
    TMDBTransportError: "upstream_unavailable",
}


def filmai_exception_handler(exc, context):
    """Añade el sobre a las excepciones DRF sin alterar HTTP, headers ni legacy."""
    response = _respuesta_legacy(exc, context)
    parametros = getattr(exc, "parametros", {})
    errores = []
    if isinstance(exc, TMDBError):
        codigo = _CODIGOS_TMDB.get(type(exc), "upstream_error")
    elif isinstance(exc, ValidationError):
        codigo = "validation_error"
        errores = entradas_validacion(exc, estricto=False)
    elif isinstance(exc, Http404):
        codigo = "not_found"
    elif isinstance(exc, DjangoPermissionDenied):
        codigo = "permission_denied"
    elif not hasattr(exc, "default_code"):
        codigo = "server_error"
    else:
        codigo = getattr(exc, "codigo", exc.default_code)
        codigo = _CODIGOS_HEREDADOS.get(codigo, codigo)
        if codigo == "error" and response.status_code == 500:
            codigo = "server_error"
    if codigo not in CATALOGO:
        # OT-31/OT-32 adoptan aliases de terceros; OT-34 impone cobertura total.
        logger.warning("Excepción pendiente de registrar: %s", codigo)
        return response
    request = context.get("request")
    if isinstance(exc, Throttled) and exc.wait is not None:
        # DRF ya fija `Retry-After` con `exc.wait`; el parámetro lo repite en el sobre.
        parametros = {"retry_after_seconds": math.ceil(exc.wait)}
    if isinstance(exc, MethodNotAllowed) and request is not None:
        parametros = {"method": request.method}
    elif codigo == "unsupported_media_type" and request is not None:
        parametros = {"mediaType": request.content_type}
    sobre = construir_sobre(
        codigo,
        response.status_code,
        parametros=parametros,
        errores=errores,
        debug=settings.DEBUG,
        mensaje=str(exc),
    )
    response.data = conservar_legacy(response.data, sobre)
    return response
