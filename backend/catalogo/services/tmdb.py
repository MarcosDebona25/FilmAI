from functools import lru_cache

from django.conf import settings

from catalogo.cache import TMDBClientCache, get_redis
from catalogo.client import TMDBClient, crear_http_client


@lru_cache(maxsize=1)
def _http_compartido():
    """Un solo pool de conexiones hacia TMDB para todos los idiomas.

    Antes el inglés (respaldo) y el idioma pedido tenían cada uno su
    `httpx.Client`, y la ficha abría dos conexiones TLS (~300 ms cada una).
    """
    return crear_http_client()


@lru_cache(maxsize=2)
def _servicio_por_idioma(idioma) -> TMDBClientCache:
    http = _http_compartido()
    cliente = (
        TMDBClient(http_client=http)
        if idioma == settings.IDIOMAS_TMDB[settings.IDIOMA_POR_DEFECTO]
        else TMDBClient(idioma=idioma, http_client=http)
    )
    return TMDBClientCache(cliente, get_redis())


def get_catalog_service(idioma=None) -> TMDBClientCache:
    """Normaliza la llamada sin argumentos para compartir el mismo cliente EN."""
    if idioma is None:
        idioma = settings.IDIOMAS_TMDB[settings.IDIOMA_POR_DEFECTO]
    return _servicio_por_idioma(idioma)


# Conserva la operación pública de limpieza usada por los tests existentes.
def _limpiar():
    _servicio_por_idioma.cache_clear()
    _http_compartido.cache_clear()


get_catalog_service.cache_clear = _limpiar
