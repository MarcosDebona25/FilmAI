import re
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
from catalogo.presupuesto import registrar_llamada

# Keyword «softcore» de TMDB (verificada el 13/11/2026 con /search/keyword). Miles de
# títulos eróticos la llevan SIN que TMDB los marque `adult` (with_keywords=155477 trae
# 3682 películas con `adult` en false: 9 Songs, Emmanuelle...), así que `include_adult`
# no los frena. `discover` la excluye con `without_keywords`; el resto de los
# endpoints (search, trending) no filtran por keyword y quedan fuera de este alcance.
KEYWORD_SOFTCORE = 155477

# httpx cierra por defecto las conexiones que pasan 5 s sin usarse, y abrir una
# nueva (TCP + TLS) contra TMDB cuesta ~300 ms (medido el 13/11/2026). Entre
# dos fichas separadas por más de 5 s, ese costo caía sobre el usuario. Con 60 s
# la conexión sigue abierta y la siguiente ficha la reutiliza.
KEEPALIVE_SEGUNDOS = 60
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
# La clave de TMDB (v3) viaja en la query (`?api_key=...`), así que cualquier
# texto que lleve la URL de un pedido —el mensaje de un error de httpx, el
# registro de un logger— la arrastra. `_redactar_clave` la tapa antes de que el
# texto salga de este módulo. No se pasa a `Authorization: Bearer` porque eso
# exige el token v4 y el proyecto usa la clave v3.
_CLAVE_EN_URL = re.compile(r"(api_key=)[^&\s\"']*", re.IGNORECASE)


def _redactar_clave(texto, clave=""):
    """Reemplaza el valor de `api_key=` en `texto` (y la clave suelta, si se la pasa)."""
    texto = _CLAVE_EN_URL.sub(r"\1***", texto)
    return texto.replace(clave, "***") if clave else texto


def crear_http_client(*, base_url=None, timeout=None, transport=None):
    """Arma el `httpx.Client` hacia TMDB, con conexiones que duran 60 s ociosas.

    Un `httpx.Client` es como un pool de conexiones de JDBC: abrirlo es caro y
    se reutiliza. Es seguro usarlo desde varios hilos, por eso se puede
    compartir entre los clientes de distintos idiomas (ver `services/tmdb.py`).
    """
    return httpx.Client(
        base_url=settings.TMDB_API_BASE_URL if base_url is None else base_url,
        timeout=settings.TMDB_TIMEOUT if timeout is None else timeout,
        transport=transport,
        limits=httpx.Limits(keepalive_expiry=KEEPALIVE_SEGUNDOS),
    )


def _sin_adultos(cuerpo):
    """Saca de una respuesta de TMDB todo lo que ella misma marca como `adult`.

    TMDB devuelve las listas bajo `results` (trending, discover, search,
    recommendations, changes) o bajo `cast`/`crew` (créditos de una persona), y cada
    persona de una búsqueda trae sus `known_for`. Se filtran todas: así ningún
    camino (Inicio, Buscar, chatbot, seed, similares) recibe un título para adultos.
    Un ítem sin el campo `adult` se conserva: solo se saca lo marcado en `true`.
    """
    if not isinstance(cuerpo, dict):
        return cuerpo
    for clave in ("results", "cast", "crew"):
        items = cuerpo.get(clave)
        if isinstance(items, list):
            cuerpo[clave] = [
                _con_known_for_limpio(item)
                for item in items
                if not (isinstance(item, dict) and item.get("adult"))
            ]
    return cuerpo


def _con_known_for_limpio(item):
    if isinstance(item, dict) and isinstance(item.get("known_for"), list):
        item["known_for"] = [
            x for x in item["known_for"] if not (isinstance(x, dict) and x.get("adult"))
        ]
    return item


class TMDBClient:
    def __init__(
        self,
        *,
        api_key=None,
        base_url=None,
        timeout=None,
        transport=None,
        idioma=None,
        http_client=None,
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
        # `http_client` permite compartir una sola conexión entre idiomas (inyección
        # de dependencias); sin él, cada TMDBClient arma la suya, como siempre.
        self._client = http_client or crear_http_client(
            base_url=self.base_url, timeout=self.timeout, transport=transport
        )

    def _get(self, path, params=None):
        return self._request(path, params or {})

    def _get_localizado(self, path, params=None):
        return self._get(path, {**(params or {}), "language": self.idioma})

    def _request(self, path, params):
        request_params = {**params, "api_key": self.api_key}
        for attempt in range(MAX_RETRIES + 1):
            # Cada intento cuenta para el tope del pedido, reintentos incluidos
            # (auditoría F6). Fuera de un pedido HTTP no hay tope.
            registrar_llamada()
            try:
                response = self._client.get(path, params=request_params)
            except httpx.TransportError as error:
                if attempt < MAX_RETRIES:
                    time.sleep(self._backoff(attempt))
                    continue
                # `from None`: la causa original lleva la URL con la clave y
                # saldría en el traceback de `logger.exception`.
                raise TMDBTransportError(
                    _redactar_clave(str(error), self.api_key)
                ) from None

            if 200 <= response.status_code < 300:
                try:
                    return _sin_adultos(response.json())
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
        duracion_max=None,
        con_keywords=None,
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
        `hasta_fecha`, hasta ese día (décadas en Buscar). `duracion_max` son
        minutos y solo sirve en películas: en series TMDB casi no tiene el dato.
        El mínimo de 1 deja afuera las películas con duración desconocida (0).
        `con_keywords` son ids de keywords de TMDB (`with_keywords`), separados por
        coma (todos) o por barra (alguno). A diferencia de `with_people`, TMDB sí lo
        respeta en series (verificado el 13/11/2026 con 818, «based on novel or book»).
        """
        # `include_adult=false` ya es el default de TMDB, pero se pide explícito. Lo que
        # no frena es el erotismo sin marcar: por eso también `without_keywords`.
        params = {
            "page": page,
            "include_adult": "false",
            "without_keywords": KEYWORD_SOFTCORE,
        }
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
        if duracion_max is not None:
            params["with_runtime.gte"] = 1
            params["with_runtime.lte"] = duracion_max
        if con_keywords is not None:
            params["with_keywords"] = con_keywords
        return self._get_localizado(f"/discover/{tipo}", params)

    def search(self, query, tipo, page=1, anio=None):
        """Búsqueda por nombre. TMDB no filtra acá por género ni por nota.

        El año va con el mismo parámetro que `discover` (`primary_release_year`
        o `first_air_date_year`): `year`, el genérico, es flojo y trae
        producciones de otros años (verificado el 14/10/2026, C-06).
        """
        params = {"query": query, "page": page, "include_adult": "false"}
        if anio is not None:
            params[_DISCOVER_YEAR_PARAM[tipo]] = anio
        return self._get_localizado(f"/search/{tipo}", params)

    def get_movie_detail(self, id_tmdb):
        return self._detalle_sin_adultos(f"/movie/{id_tmdb}")

    def get_tv_detail(self, id_tmdb):
        return self._detalle_sin_adultos(f"/tv/{id_tmdb}")

    def _detalle_sin_adultos(self, path):
        """Un título marcado `adult` se trata como inexistente: 404 en la ficha y,
        como la materialización lo recibe como `TMDBNotFound`, no se guarda la fila."""
        detalle = self._get_localizado(path)
        if isinstance(detalle, dict) and detalle.get("adult"):
            raise TMDBNotFound("TMDB marca este título como para adultos")
        return detalle

    def get_recommendations(self, id_tmdb, tipo):
        # No `/similar`: compara poco más que géneros y para Paddington 2 trae El
        # Señor de los Anillos. Este usa lo que ve la gente (05/11/2026).
        return self._get_localizado(f"/{tipo}/{id_tmdb}/recommendations")

    def search_multi(self, query, page=1):
        """Películas, series y personas en una sola búsqueda (sugerencias de la navbar).

        Para la grilla de Buscar no sirve (mezcla personas, 14/10/2026); para
        sugerir, que es lo que se quiere, alcanza con una llamada.
        """
        return self._get_localizado(
            "/search/multi",
            {"query": query, "page": page, "include_adult": "false"},
        )

    def search_person(self, nombre):
        return self._get_localizado(
            "/search/person", {"query": nombre, "include_adult": "false"}
        )

    def get_person_detail(self, id_persona):
        """Nombre, género y foto de una persona (el chip del filtro por persona)."""
        return self._get_localizado(f"/person/{id_persona}")

    def get_person_credits(self, id_persona):
        # Películas y series, como actor (`cast`) o en el equipo (`crew`). `discover`
        # con `with_people` no sirve: en series TMDB ignora el filtro sin avisar.
        return self._get_localizado(f"/person/{id_persona}/combined_credits")

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
