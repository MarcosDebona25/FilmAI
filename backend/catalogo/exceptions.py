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
