from functools import lru_cache

from django.conf import settings

from catalogo.cache import TMDBClientCache, get_redis
from catalogo.client import TMDBClient


@lru_cache(maxsize=2)
def _servicio_por_idioma(idioma) -> TMDBClientCache:
    cliente = (
        TMDBClient()
        if idioma == settings.IDIOMAS_TMDB[settings.IDIOMA_POR_DEFECTO]
        else TMDBClient(idioma=idioma)
    )
    return TMDBClientCache(cliente, get_redis())


def get_catalog_service(idioma=None) -> TMDBClientCache:
    """Normaliza la llamada sin argumentos para compartir el mismo cliente EN."""
    if idioma is None:
        idioma = settings.IDIOMAS_TMDB[settings.IDIOMA_POR_DEFECTO]
    return _servicio_por_idioma(idioma)


# Conserva la operación pública de limpieza usada por los tests existentes.
get_catalog_service.cache_clear = _servicio_por_idioma.cache_clear
