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


TMDB_STATUS_CODES = {
    TMDBNotFound: 404,
    TMDBBadRequest: 400,
    TMDBRateLimited: 429,
    TMDBServerError: 502,
    TMDBTransportError: 503,
}


def tmdb_exception_handler(exc, context):
    if isinstance(exc, TMDBError):
        return Response(
            {"detail": str(exc)}, status=TMDB_STATUS_CODES.get(type(exc), 502)
        )
    return drf_exception_handler(exc, context)
