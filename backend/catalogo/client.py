import time

import httpx
from django.conf import settings

from catalogo.exceptions import (
    TMDBBadRequest,
    TMDBError,
    TMDBNotFound,
    TMDBRateLimited,
    TMDBServerError,
    TMDBTransportError,
)

MAX_RETRIES = 3
BASE_BACKOFF = 1.0
BACKOFF_FACTOR = 2
MAX_BACKOFF = 8.0
_DISCOVER_YEAR_PARAM = {
    "movie": "primary_release_year",
    "tv": "first_air_date_year",
}


class TMDBClient:
    def __init__(self, *, api_key=None, base_url=None, timeout=None, transport=None):
        self.api_key = settings.TMDB_API_KEY if api_key is None else api_key
        self.base_url = settings.TMDB_API_BASE_URL if base_url is None else base_url
        self.timeout = settings.TMDB_TIMEOUT if timeout is None else timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=transport,
        )

    def _get(self, path, params=None):
        return self._request(path, params or {})

    def _request(self, path, params):
        request_params = {**params, "api_key": self.api_key}
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._client.get(path, params=request_params)
            except httpx.TransportError as error:
                if attempt < MAX_RETRIES:
                    time.sleep(self._backoff(attempt))
                    continue
                raise TMDBTransportError(str(error)) from error

            if 200 <= response.status_code < 300:
                try:
                    return response.json()
                except (ValueError, httpx.DecodingError) as error:
                    raise TMDBTransportError(
                        "Invalid JSON response from TMDB"
                    ) from error

            if response.status_code == 429 or response.status_code >= 500:
                if attempt < MAX_RETRIES:
                    delay = max(self._backoff(attempt), self._retry_after(response))
                    time.sleep(delay)
                    continue
                if response.status_code == 429:
                    raise TMDBRateLimited(self._error_message(response))
                raise TMDBServerError(self._error_message(response))

            self._raise_http_error(response)

        raise TMDBError("TMDB request exhausted retry budget")

    @staticmethod
    def _backoff(attempt):
        return min(BASE_BACKOFF * BACKOFF_FACTOR**attempt, MAX_BACKOFF)

    @staticmethod
    def _retry_after(response):
        try:
            return max(float(response.headers["Retry-After"]), 0.0)
        except (KeyError, TypeError, ValueError):
            return 0.0

    @staticmethod
    def _error_message(response):
        return f"TMDB returned HTTP {response.status_code}"

    @staticmethod
    def _raise_http_error(response):
        message = TMDBClient._error_message(response)
        if response.status_code == 404:
            raise TMDBNotFound(message)
        if 400 <= response.status_code < 500:
            raise TMDBBadRequest(message)
        raise TMDBError(message)

    def get_trending(self, media_type="all", time_window="week", page=1):
        return self._get(f"/trending/{media_type}/{time_window}", {"page": page})

    def get_now_playing(self, page=1):
        return self._get("/movie/now_playing", {"page": page})

    def discover(self, tipo, genero=None, anio=None, min_rating=None, page=1):
        params = {"page": page}
        if genero is not None:
            params["with_genres"] = genero
        if anio is not None:
            params[_DISCOVER_YEAR_PARAM[tipo]] = anio
        if min_rating is not None:
            params["vote_average.gte"] = min_rating
        return self._get(f"/discover/{tipo}", params)

    def search(self, query, tipo, page=1):
        return self._get(f"/search/{tipo}", {"query": query, "page": page})

    def get_movie_detail(self, id_tmdb):
        return self._get(f"/movie/{id_tmdb}")

    def get_tv_detail(self, id_tmdb):
        return self._get(f"/tv/{id_tmdb}")

    def get_keywords(self, id_tmdb, tipo):
        return self._get(f"/{tipo}/{id_tmdb}/keywords")

    def get_credits(self, id_tmdb, tipo):
        # Los endpoints de detalle no incluyen cast ni crew: se piden aparte.
        return self._get(f"/{tipo}/{id_tmdb}/credits")

    def get_changes(self, tipo, page=1):
        # IDs modificados en TMDB en las últimas 24 h, de a 100 por página.
        return self._get(f"/{tipo}/changes", {"page": page})
