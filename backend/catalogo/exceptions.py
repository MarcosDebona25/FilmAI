from typing import ClassVar

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class TMDBError(Exception):
    """Base exception for TMDB client failures."""


class TMDBRateLimited(TMDBError):
    """TMDB rejected the request because its rate limit was exceeded."""


class TMDBNotFound(TMDBError):
    """TMDB could not find the requested resource."""


class TMDBBadRequest(TMDBError):
    """TMDB rejected the request as invalid."""


class TMDBServerError(TMDBError):
    """TMDB returned a server-side error."""


class TMDBTransportError(TMDBError):
    """The request could not reach TMDB or its response could not be read."""


class TMDBPresupuestoAgotado(TMDBError):
    """El pedido superó el tope de llamadas a TMDB (auditoría F6).

    Hereda de `TMDBError` a propósito: la caché de Redis lo trata como «TMDB no
    disponible» y sirve la copia de respaldo si la tiene, sin otra llamada.
    """


TMDB_STATUS_CODES = {
    TMDBNotFound: 404,
    TMDBBadRequest: 400,
    TMDBRateLimited: 429,
    TMDBServerError: 502,
    TMDBTransportError: 503,
    TMDBPresupuestoAgotado: 503,
}


def tmdb_exception_handler(exc, context):
    if isinstance(exc, TMDBError):
        return Response(
            {"detail": str(exc)}, status=TMDB_STATUS_CODES.get(type(exc), 502)
        )
    return drf_exception_handler(exc, context)


class CalificacionDuplicada(APIException):
    """Un usuario califica una misma producción una sola vez (CU-015).

    Existe el `UniqueConstraint`, así que sin esto un segundo POST terminaría
    en `IntegrityError` y el frontend recibiría un 500. Reusa el sobre
    `{codigo, detail}` que L-01 estableció en `listas/exceptions.py`: el modal
    necesita distinguir "ya la calificaste" de un error de validación, y que
    las dos APIs hablen igual vale más que cualquiera de las dos formas.
    """

    status_code = 409
    default_code = "calificacion_duplicada"
    default_detail: ClassVar[dict[str, str]] = {
        "codigo": default_code,
        "detail": "Ya calificaste esta producción. Editá tu calificación.",
    }


class ResenaModerada(APIException):
    """El texto de una reseña moderada no se edita ni se borra (F10, auditoría).

    Un administrador la ocultó (`activa=False`, AD-01'). Si su autor pudiera
    borrar el texto y escribir otro, la fila nueva nacería `activa=True` y la
    moderación se levantaría sola. La nota sigue siendo editable, y quitar la
    calificación entera también (CU-015 pide eliminar permanentemente).
    """

    status_code = 409
    default_code = "review_moderated"
    default_detail = "Esta reseña fue moderada: no se puede editar ni borrar su texto."
