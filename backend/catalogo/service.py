from functools import lru_cache

from catalogo.cache import TMDBClientCache, get_redis
from catalogo.client import TMDBClient


@lru_cache(maxsize=1)
def get_catalog_service() -> TMDBClientCache:
def get_catalog_service():
    return TMDBClientCache(TMDBClient(), get_redis())
