import json
import logging
from hashlib import sha256

import redis
from django.conf import settings

from catalogo.exceptions import TMDBBadRequest, TMDBError, TMDBNotFound

logger = logging.getLogger(__name__)

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
    # Disponibilidad en plataformas (JustWatch vía TMDB): son contratos que
    # cambian seguido, así que el TTL es corto. Se cachea por título y no por
    # país: la respuesta trae todos los países y un llamado sirve a todos.
    "watch_providers": 12 * 3600,
    # La lista de cambios rueda a diario, así que 24 h sería demasiado; 6 h
    # alcanza para que una sync reintentada no vuelva a bajar ~100 páginas.
    "changes": 6 * 3600,
    # Los géneros de TMDB son prácticamente estáticos: un mes evita pedirlos en
    # cada corrida del seed sin volverlos eternos.
    "genres": 30 * 24 * 3600,
}

# Respaldo para cuando TMDB no responde (CU-008 2.A, CU-019 4.A, 16/10/2026):
# cada respuesta se guarda también con una vida mucho más larga que su TTL.
# Si TMDB está caído, devuelve error de servidor, se pasa del tiempo o limita
# los pedidos, se sirve esa copia —«la última disponible»— en vez de un 502.
RESPALDO_TTL = 30 * 24 * 3600
# La lista de cambios la usa la sync nocturna: con datos viejos refrescaría
# mal sin enterarse. Ahí conviene que el fallo se vea.
RESPALDO_TTLS = {"watch_providers": 7 * 24 * 3600}
SIN_RESPALDO = frozenset({"changes"})
# Con TMDB caído, cada pedido que sale del respaldo dejaría un aviso: uno por
# endpoint cada 5 minutos alcanza para enterarse sin llenar el log.
AVISO_RESPALDO_SEGUNDOS = 5 * 60

# Bounded timeouts so a hung Redis fails fast and the cache degrades to TMDB
# instead of blocking the request indefinitely.
REDIS_SOCKET_CONNECT_TIMEOUT = 2
REDIS_SOCKET_TIMEOUT = 2


def _build_key(endpoint, params):
    canonical = json.dumps(params, sort_keys=True, default=str)
    params_hash = sha256(canonical.encode()).hexdigest()[:16]
    return f"tmdb:{endpoint}:{params_hash}"


def _clave_respaldo(clave):
    return clave.replace("tmdb:", "tmdb:respaldo:", 1)


def _tmdb_no_disponible(error):
    """¿El fallo es de TMDB y no de lo que se pidió?

    Un 404 o un 400 dicen algo cierto sobre el pedido (no existe, no es
    válido): servir una copia vieja los escondería.
    """
    return isinstance(error, TMDBError) and not isinstance(
        error, (TMDBNotFound, TMDBBadRequest)
    )


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

        try:
            result = producer()
        except TMDBError as error:
            respaldo = self._respaldo(endpoint, key, error, redis_available)
            if respaldo is None:
                raise
            return respaldo
        if redis_available:
            try:
                serializado = json.dumps(result)
                self.redis.set(key, serializado, ex=ENDPOINT_TTLS[endpoint])
                if endpoint not in SIN_RESPALDO:
                    self.redis.set(
                        _clave_respaldo(key),
                        serializado,
                        ex=RESPALDO_TTLS.get(endpoint, RESPALDO_TTL),
                    )
            except redis.RedisError:
                pass
        return result

    def _respaldo(self, endpoint, key, error, redis_available):
        """La última respuesta guardada, si TMDB no está disponible; si no, None."""
        if (
            not redis_available
            or endpoint in SIN_RESPALDO
            or not _tmdb_no_disponible(error)
        ):
            return None
        try:
            raw = self.redis.get(_clave_respaldo(key))
            datos = json.loads(raw) if raw is not None else None
        except (redis.RedisError, TypeError, ValueError):
            return None
        if datos is not None and self._toca_avisar(endpoint):
            logger.warning(
                "TMDB no disponible (%s: %s); se sirve el respaldo de %s",
                type(error).__name__,
                error,
                endpoint,
            )
        return datos

    def _toca_avisar(self, endpoint):
        """¿Ya pasaron 5 minutos desde el último aviso de respaldo de este endpoint?"""
        try:
            return bool(
                self.redis.set(
                    f"tmdb:respaldo-aviso:{endpoint}",
                    1,
                    nx=True,
                    ex=AVISO_RESPALDO_SEGUNDOS,
                )
            )
        except redis.RedisError:
            return True

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
        hasta_fecha=None,
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
        if hasta_fecha is not None:
            params["hasta_fecha"] = hasta_fecha
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
                hasta_fecha,
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

    def get_watch_providers(self, id_tmdb, tipo):
        params = {"id_tmdb": id_tmdb, "tipo": tipo}
        return self._cached_call(
            "watch_providers",
            params,
            lambda: self.client.get_watch_providers(id_tmdb, tipo),
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
