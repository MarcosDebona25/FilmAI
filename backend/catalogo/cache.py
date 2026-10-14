import json
from hashlib import sha256

import redis
from django.conf import settings

ENDPOINTS_LOCALIZADOS = frozenset(
    {
        "trending",
        "now_playing",
        "discover",
        "search",
        "movie_detail",
        "tv_detail",
        "genres",
    }
)

ENDPOINT_TTLS = {
    "trending": 6 * 3600,
    "now_playing": 6 * 3600,
    "discover": 6 * 3600,
    "search": 1 * 3600,
    "movie_detail": 24 * 3600,
    "tv_detail": 24 * 3600,
    "keywords": 24 * 3600,
    # El reparto de una producción ya estrenada casi no cambia: mismo TTL
    # largo que el detalle y las keywords.
    "credits": 24 * 3600,
    # La lista de cambios rueda a diario, así que 24 h sería demasiado; 6 h
    # alcanza para que una sync reintentada no vuelva a bajar ~100 páginas.
    "changes": 6 * 3600,
    # Los géneros de TMDB son prácticamente estáticos: un mes evita pedirlos en
    # cada corrida del seed sin volverlos eternos.
    "genres": 30 * 24 * 3600,
}

# Bounded timeouts so a hung Redis fails fast and the cache degrades to TMDB
# instead of blocking the request indefinitely.
REDIS_SOCKET_CONNECT_TIMEOUT = 2
REDIS_SOCKET_TIMEOUT = 2


def _build_key(endpoint, params):
    canonical = json.dumps(params, sort_keys=True, default=str)
    params_hash = sha256(canonical.encode()).hexdigest()[:16]
    return f"tmdb:{endpoint}:{params_hash}"


class TMDBClientCache:
    def __init__(self, client, redis_client):
        self.client = client
        self.redis = redis_client

    def _cached_call(self, endpoint, params, producer):
        if endpoint in ENDPOINTS_LOCALIZADOS:
            params = {
                **params,
                "language": getattr(
                    self.client,
                    "idioma",
                    settings.IDIOMAS_TMDB[settings.IDIOMA_POR_DEFECTO],
                ),
            }
        key = _build_key(endpoint, params)
        redis_available = True
        try:
            raw = self.redis.get(key)
        except redis.RedisError:
            redis_available = False
            raw = None

        if raw is not None:
            try:
                return json.loads(raw)
            except (TypeError, ValueError):
                pass

        result = producer()
        if redis_available:
            try:
                self.redis.set(key, json.dumps(result), ex=ENDPOINT_TTLS[endpoint])
            except redis.RedisError:
                pass
        return result

    def get_trending(self, media_type="all", time_window="week", page=1):
        params = {
            "media_type": media_type,
            "time_window": time_window,
            "page": page,
        }
        return self._cached_call(
            "trending",
            params,
            lambda: self.client.get_trending(media_type, time_window, page),
        )

    def get_now_playing(self, page=1):
        params = {"page": page}
        return self._cached_call(
            "now_playing", params, lambda: self.client.get_now_playing(page)
        )

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
    ):
        # Todos los filtros entran en la clave: dos consultas que difieren en
        # la década son dos respuestas distintas, no un cache hit.
        params = {
            "tipo": tipo,
            "genero": genero,
            "anio": anio,
            "min_rating": min_rating,
            "page": page,
            "anio_desde": anio_desde,
            "anio_hasta": anio_hasta,
            "sort_by": sort_by,
        }
        # Solo cuando se usa: así las consultas sin mínimo (C-03, C-04c)
        # conservan la clave que ya tenían en Redis.
        if min_votos is not None:
            params["min_votos"] = min_votos
        if max_rating is not None:
            params["max_rating"] = max_rating
        if sin_generos is not None:
            params["sin_generos"] = sin_generos
        if desde_fecha is not None:
            params["desde_fecha"] = desde_fecha
        return self._cached_call(
            "discover",
            params,
            lambda: self.client.discover(
                tipo,
                genero,
                anio,
                min_rating,
                page,
                anio_desde,
                anio_hasta,
                sort_by,
                min_votos,
                max_rating,
                sin_generos,
                desde_fecha,
            ),
        )

    def search(self, query, tipo, page=1, anio=None):
        params = {"query": query, "tipo": tipo, "page": page}
        # Igual que `min_votos`: solo cuando se usa, para no cambiar la clave de
        # las búsquedas que ya están en Redis.
        if anio is not None:
            params["anio"] = anio
        return self._cached_call(
            "search", params, lambda: self.client.search(query, tipo, page, anio)
        )

    def get_movie_detail(self, id_tmdb):
        params = {"id_tmdb": id_tmdb}
        return self._cached_call(
            "movie_detail", params, lambda: self.client.get_movie_detail(id_tmdb)
        )

    def get_tv_detail(self, id_tmdb):
        params = {"id_tmdb": id_tmdb}
        return self._cached_call(
            "tv_detail", params, lambda: self.client.get_tv_detail(id_tmdb)
        )

    def get_keywords(self, id_tmdb, tipo):
        params = {"id_tmdb": id_tmdb, "tipo": tipo}
        return self._cached_call(
            "keywords", params, lambda: self.client.get_keywords(id_tmdb, tipo)
        )

    def get_credits(self, id_tmdb, tipo):
        params = {"id_tmdb": id_tmdb, "tipo": tipo}
        return self._cached_call(
            "credits", params, lambda: self.client.get_credits(id_tmdb, tipo)
        )

    def get_changes(self, tipo, page=1):
        params = {"tipo": tipo, "page": page}
        return self._cached_call(
            "changes", params, lambda: self.client.get_changes(tipo, page)
        )

    def get_genres(self, tipo):
        params = {"tipo": tipo}
        return self._cached_call("genres", params, lambda: self.client.get_genres(tipo))


def get_redis():
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
        socket_timeout=REDIS_SOCKET_TIMEOUT,
    )
