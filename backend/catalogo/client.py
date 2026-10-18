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
# Mismo problema que arriba, para rangos: TMDB filtra por fecha con un nombre
# distinto según el tipo. Pasar el del otro tipo no da error — TMDB lo ignora
# en silencio y devuelve el catálogo entero sin filtrar (C-04c).
_DISCOVER_DATE_PARAM = {
    "movie": "primary_release_date",
    "tv": "first_air_date",
}


class TMDBClient:
    def __init__(
        self, *, api_key=None, base_url=None, timeout=None, transport=None, idioma=None
    ):
        self.idioma = (
            settings.IDIOMAS_TMDB[settings.IDIOMA_POR_DEFECTO]
            if idioma is None
            else idioma
        )
        if self.idioma not in settings.IDIOMAS_TMDB.values():
            raise ValueError("Idioma TMDB no soportado.")
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

    def _get_localizado(self, path, params=None):
        return self._get(path, {**(params or {}), "language": self.idioma})

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
        return self._get_localizado(
            f"/trending/{media_type}/{time_window}", {"page": page}
        )

    def get_now_playing(self, page=1):
        return self._get_localizado("/movie/now_playing", {"page": page})

    def discover(
        self,
        tipo,
        genero=None,
        anio=None,
        min_rating=None,
        page=1,
        anio_desde=None,
        anio_hasta=None,
        sort_by=None,
        min_votos=None,
        max_rating=None,
        sin_generos=None,
        desde_fecha=None,
        hasta_fecha=None,
    ):
        """Busca producciones por filtros. Todo es opcional menos el tipo.

        `anio` filtra un año puntual; `anio_desde`/`anio_hasta` un rango, que
        es lo que el seed usa para muestrear por década (C-04c). `sort_by`
        decide qué entra primero: `vote_count.desc` trae los títulos que la
        gente conoce, el orden por defecto trae lo que trendea hoy. `min_votos`
        deja afuera los títulos con pocos votos (C-05) y `max_rating` es el
        techo de nota de «Below 5» en Buscar (C-06). `sin_generos` son ids
        separados por coma que se excluyen (`without_genres`); `desde_fecha`
        (AAAA-MM-DD) deja solo lo que estrena desde ese día («A estrenar») y
        `hasta_fecha`, hasta ese día (décadas en Buscar).
        """
        params = {"page": page}
        if genero is not None:
            params["with_genres"] = genero
        if anio is not None:
            params[_DISCOVER_YEAR_PARAM[tipo]] = anio
        if anio_desde is not None:
            params[f"{_DISCOVER_DATE_PARAM[tipo]}.gte"] = f"{anio_desde}-01-01"
        if anio_hasta is not None:
            params[f"{_DISCOVER_DATE_PARAM[tipo]}.lte"] = f"{anio_hasta}-12-31"
        if min_rating is not None:
            params["vote_average.gte"] = min_rating
        if sort_by is not None:
            params["sort_by"] = sort_by
        if min_votos is not None:
            params["vote_count.gte"] = min_votos
        if max_rating is not None:
            params["vote_average.lte"] = max_rating
        if sin_generos is not None:
            params["without_genres"] = sin_generos
        if desde_fecha is not None:
            params[f"{_DISCOVER_DATE_PARAM[tipo]}.gte"] = desde_fecha
        if hasta_fecha is not None:
            params[f"{_DISCOVER_DATE_PARAM[tipo]}.lte"] = hasta_fecha
        return self._get_localizado(f"/discover/{tipo}", params)

    def search(self, query, tipo, page=1, anio=None):
        """Búsqueda por nombre. TMDB no filtra acá por género ni por nota.

        El año va con el mismo parámetro que `discover` (`primary_release_year`
        o `first_air_date_year`): `year`, el genérico, es flojo y trae
        producciones de otros años (verificado el 14/10/2026, C-06).
        """
        params = {"query": query, "page": page}
        if anio is not None:
            params[_DISCOVER_YEAR_PARAM[tipo]] = anio
        return self._get_localizado(f"/search/{tipo}", params)

    def get_movie_detail(self, id_tmdb):
        return self._get_localizado(f"/movie/{id_tmdb}")

    def get_tv_detail(self, id_tmdb):
        return self._get_localizado(f"/tv/{id_tmdb}")

    def get_keywords(self, id_tmdb, tipo):
        return self._get(f"/{tipo}/{id_tmdb}/keywords")

    def get_credits(self, id_tmdb, tipo):
        # Los endpoints de detalle no incluyen cast ni crew: se piden aparte.
        return self._get(f"/{tipo}/{id_tmdb}/credits")

    def get_watch_providers(self, id_tmdb, tipo):
        # Una sola respuesta trae todos los países (`results.AR`, `results.US`…).
        return self._get(f"/{tipo}/{id_tmdb}/watch/providers")

    def get_changes(self, tipo, page=1):
        # IDs modificados en TMDB en las últimas 24 h, de a 100 por página.
        return self._get(f"/{tipo}/changes", {"page": page})

    def get_genres(self, tipo):
        # Catálogo de géneros con sus ids. Difiere por tipo: película tiene
        # `Action` y `Adventure` separados, serie tiene `Action & Adventure`.
        return self._get_localizado(f"/genre/{tipo}/list")
