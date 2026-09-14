"""Traducción entre el vocabulario de TMDB y el del dominio (C-04a).

TMDB dice `movie`/`tv`; el dominio dice `pelicula`/`serie` (`TipoProduccion`).
Esta es la ÚNICA conversión permitida: persistir un valor crudo de TMDB en la
columna `tipo` deja filas que las consultas del dominio no encuentran, y el
problema no se manifiesta hasta mucho después (decisión 08/09/2026).

Las vistas siguen aceptando `movie`/`tv` en los query params, porque es el
vocabulario público de la API; la traducción ocurre al cruzar hacia el modelo.
"""

from catalogo.models import TipoProduccion

_TMDB_A_DOMINIO = {
    "movie": TipoProduccion.PELICULA,
    "tv": TipoProduccion.SERIE,
}

_DOMINIO_A_TMDB = {dominio: tmdb for tmdb, dominio in _TMDB_A_DOMINIO.items()}


def tmdb_a_dominio(tipo_tmdb):
    """`"movie"` → `TipoProduccion.PELICULA`, `"tv"` → `TipoProduccion.SERIE`.

    Lanza `ValueError` ante cualquier otro valor, incluido `"all"`: es un
    filtro válido de discovery (C-03) pero no un tipo de producción, así que
    no hay nada que materializar con él.
    """
    try:
        return _TMDB_A_DOMINIO[tipo_tmdb]
    except (KeyError, TypeError):
        validos = ", ".join(sorted(_TMDB_A_DOMINIO))
        raise ValueError(
            f"Tipo de TMDB no soportado: {tipo_tmdb!r}. Válidos: {validos}."
        ) from None


def dominio_a_tmdb(tipo_dominio):
    """Inversa de `tmdb_a_dominio`, para construir llamadas a la API de TMDB."""
    try:
        return _DOMINIO_A_TMDB[tipo_dominio]
    except (KeyError, TypeError):
        validos = ", ".join(sorted(_DOMINIO_A_TMDB))
        raise ValueError(
            f"Tipo de dominio no soportado: {tipo_dominio!r}. Válidos: {validos}."
        ) from None
