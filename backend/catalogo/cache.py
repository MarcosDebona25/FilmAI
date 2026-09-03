import json
from hashlib import sha256

import redis
from django.conf import settings

ENDPOINT_TTLS = {
    "trending": 6 * 3600,
    "now_playing": 6 * 3600,
    "discover": 6 * 3600,
    "search": 1 * 3600,
    "movie_detail": 24 * 3600,
    "tv_detail": 24 * 3600,
    "keywords": 24 * 3600,
}


def _build_key(endpoint, params):
    canonical = json.dumps(params, sort_keys=True, default=str)
    params_hash = sha256(canonical.encode()).hexdigest()[:16]
    return f"tmdb:{endpoint}:{params_hash}"


class TMDBClientCache:
    def __init__(self, client, redis_client):
        self.client = client
        self.redis = redis_client

    def _cached_call(self, endpoint, params, producer):
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

    def discover(self, tipo, genero=None, anio=None, min_rating=None, page=1):
        params = {
            "tipo": tipo,
            "genero": genero,
            "anio": anio,
            "min_rating": min_rating,
            "page": page,
        }
        return self._cached_call(
            "discover",
            params,
            lambda: self.client.discover(tipo, genero, anio, min_rating, page),
        )

    def search(self, query, tipo, page=1):
        params = {"query": query, "tipo": tipo, "page": page}
        return self._cached_call(
            "search", params, lambda: self.client.search(query, tipo, page)
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


def get_redis():
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
