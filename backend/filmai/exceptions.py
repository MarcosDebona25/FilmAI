"""Manejador global de excepciones de FilmAI."""

import logging
import math

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    MethodNotAllowed,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework_simplejwt.exceptions import (
    AuthenticationFailed as JWTAuthenticationFailed,
)

from catalogo.exceptions import (
    TMDBBadRequest,
    TMDBError,
    TMDBNotFound,
    TMDBPresupuestoAgotado,
    TMDBRateLimited,
    TMDBServerError,
    TMDBTransportError,
    tmdb_exception_handler,
)

from .errores.catalogo import CATALOGO
from .errores.sobre import construir_sobre, entradas_validacion

logger = logging.getLogger(__name__)


def _respuesta_base(exc, context):
    """Conserva HTTP y encabezados; el cuerpo público se construye por código."""
    if isinstance(exc, TMDBError):
        return tmdb_exception_handler(exc, context)
    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Error no manejado: %s", exc)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
    # Para quien llama es lo mismo: TMDB no está disponible para este pedido.
    TMDBPresupuestoAgotado: "upstream_unavailable",
}


# simplejwt guarda su código propio en `detail["code"]` (DetailDictMixin).
_CODIGOS_SIMPLEJWT = {
    "token_not_valid": "invalid_token",
    "bad_authorization_header": "invalid_token",
    "user_not_found": "invalid_token",
    "user_inactive": "session_revoked",
    "password_changed": "session_revoked",
}


# Último recurso en producción cuando una excepción llega sin código registrado.
_CODIGO_POR_ESTADO = {
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    500: "server_error",
}


def _codigo_simplejwt(exc):
    sub = exc.detail.get("code") if isinstance(exc.detail, dict) else None
    return _CODIGOS_SIMPLEJWT.get(str(sub), "invalid_token")


def filmai_exception_handler(exc, context):
    """Emite el contrato definitivo sin alterar HTTP ni encabezados."""
    response = _respuesta_base(exc, context)
    parametros = getattr(exc, "parametros", {})
    errores = []
    if isinstance(exc, TMDBError):
        codigo = _CODIGOS_TMDB.get(type(exc), "upstream_error")
    elif isinstance(exc, JWTAuthenticationFailed):
        codigo = _codigo_simplejwt(exc)
    elif isinstance(exc, ValidationError):
        codigo = "validation_error"
        errores = entradas_validacion(
            exc, estricto=getattr(settings, "FILMAI_SOBRE_ESTRICTO", False)
        )
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
        # La suite corre en modo estricto (filmai.pruebas): un código sin
        # registrar es un bug a corregir, no algo que degradar en silencio.
        if getattr(settings, "FILMAI_SOBRE_ESTRICTO", False):
            raise ValueError(f"Código no registrado en el catálogo: {codigo}.")
        logger.error("Excepción sin código registrado: %s", codigo)
        codigo = _CODIGO_POR_ESTADO.get(response.status_code)
        if codigo is None:
            return response
        parametros = {}
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
    response.data = sobre
    return response
