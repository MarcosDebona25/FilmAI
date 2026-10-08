"""Completa con inglés los campos que TMDB devuelve vacíos en otro idioma.

TMDB no rellena con otro idioma: sin traducción, la sinopsis llega vacía
(docs/i18n/tmdb-verificacion-ot60.md). El respaldo se pide solo cuando hace
falta, pasa por la misma caché y nunca pisa un valor no vacío.
"""

from django.conf import settings

# Campos de texto que la interfaz muestra; `title` es de películas y `name` de series.
CAMPOS_TRADUCIBLES = ("title", "name", "overview")
# Lista de los campos que quedaron en inglés, para que la interfaz marque lang="en".
MARCA = "campos_en_ingles"


def _vacio(valor):
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _completar(destino, respaldo):
    """Copia del respaldo solo lo que falta; devuelve los campos completados."""
    completados = []
    for campo in CAMPOS_TRADUCIBLES:
        if (
            campo in destino
            and _vacio(destino[campo])
            and not _vacio(respaldo.get(campo))
        ):
            destino[campo] = respaldo[campo]
            completados.append(campo)
    return completados


def _incompleto(item):
    return any(campo in item and _vacio(item[campo]) for campo in CAMPOS_TRADUCIBLES)


def _clave(item):
    # `trending/all` mezcla películas y series: el id solo no identifica.
    return (item.get("media_type"), item.get("id"))


class CatalogoConRespaldo:
    """Envuelve el servicio del idioma pedido y uno en inglés como respaldo."""

    def __init__(self, servicio, respaldo):
        self._servicio = servicio
        self._respaldo = respaldo

    def __getattr__(self, nombre):
        # Keywords, créditos, cambios y géneros no necesitan combinación.
        return getattr(self._servicio, nombre)

    def _detalle(self, metodo, id_tmdb):
        datos = getattr(self._servicio, metodo)(id_tmdb)
        datos[MARCA] = []
        if _incompleto(datos):
            datos[MARCA] = _completar(datos, getattr(self._respaldo, metodo)(id_tmdb))
        return datos

    def get_movie_detail(self, id_tmdb):
        return self._detalle("get_movie_detail", id_tmdb)

    def get_tv_detail(self, id_tmdb):
        return self._detalle("get_tv_detail", id_tmdb)

    def _listado(self, metodo, *args, **kwargs):
        datos = getattr(self._servicio, metodo)(*args, **kwargs)
        resultados = datos.get("results") or []
        for item in resultados:
            item[MARCA] = []
        if any(_incompleto(item) for item in resultados):
            # La misma página en inglés, combinada por id: una sola llamada extra
            # (cacheada) en vez de un detalle por cada resultado.
            en_ingles = getattr(self._respaldo, metodo)(*args, **kwargs)
            por_clave = {_clave(item): item for item in en_ingles.get("results") or []}
            for item in resultados:
                respaldo = por_clave.get(_clave(item))
                if respaldo is not None and _incompleto(item):
                    item[MARCA] = _completar(item, respaldo)
        return datos

    def get_trending(self, *args, **kwargs):
        return self._listado("get_trending", *args, **kwargs)

    def get_now_playing(self, *args, **kwargs):
        return self._listado("get_now_playing", *args, **kwargs)

    def discover(self, *args, **kwargs):
        return self._listado("discover", *args, **kwargs)

    def search(self, *args, **kwargs):
        return self._listado("search", *args, **kwargs)


def servicio_localizado(idioma_tmdb, fabrica):
    """Servicio del idioma pedido; fuera del inglés, con respaldo campo por campo.

    `fabrica` es `get_catalog_service`: la recibe por parámetro para que la vista
    siga siendo el único punto que decide qué servicio se usa.
    """
    canonico = settings.IDIOMAS_TMDB[settings.IDIOMA_POR_DEFECTO]
    if idioma_tmdb == canonico:
        return fabrica(canonico)
    return CatalogoConRespaldo(fabrica(idioma_tmdb), fabrica(canonico))
