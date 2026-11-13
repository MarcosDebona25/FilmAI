"""Motor de «títulos parecidos»: lo comparten la ficha y las sugerencias de una lista.

Diseño: `openspec/changes/recomendaciones-similares/design.md`. Los dos usos
hacen los mismos tres pasos:

1. **Semillas → vector.** Cada título del catálogo tiene un *embedding*: 1 024
   números que resumen de qué trata (B-06). Promediando los de las semillas
   sale el *centroide*: un vector «en el medio» de todas, que representa al
   conjunto. En la ficha la semilla es un solo título.
2. **Vector → pool.** pgvector trae los títulos cuyo vector apunta más parecido
   al centroide (distancia coseno). Si hay pocos cerca, TMDB completa.
3. **Pool → página.** El pool (hasta 60 títulos) se guarda en la caché ya
   mezclado; cada página es un corte de ese pool.

Este módulo no sabe de listas, usuarios ni HTTP: las vistas deciden las
semillas, la clave de caché y qué se le saca a cada usuario («Vistas»).
"""

import logging
from itertools import zip_longest
from typing import NamedTuple

import numpy as np
from django.db import connection, transaction
from django.db.models import Avg, Count
from pgvector.django import CosineDistance

from catalogo.exceptions import TMDBError, TMDBNotFound
from catalogo.models import EstadoEmbedding, ProduccionEmbedding, TipoProduccion
from catalogo.presupuesto import tope_de_llamadas
from catalogo.services.fallback import MARCA

logger = logging.getLogger(__name__)

# Cuánto pesa, como mínimo, el nombre de la lista en el vector (D-1).
PESO_MINIMO_DEL_NOMBRE = 0.15

# Cuántos candidatos mira el índice HNSW antes de devolver. El valor por
# defecto de pgvector es 40: con él, pedir 100 devolvería 40 o menos sin avisar
# (la misma trampa que resolvió B-06 en `semantica.py`).
_EF_SEARCH = 100
_LIMITE_CANDIDATOS = 100

# Relleno con TMDB `/recommendations` (design §5): de cuántas semillas se piden
# recomendaciones y el piso de calidad de lo que vuelve (D-5).
SEMILLAS_TMDB = 3
MIN_VOTOS_TMDB = 10
# 3 semillas × (el idioma pedido + el respaldo en inglés), reintentos incluidos.
MAX_LLAMADAS_TMDB = 6


class Candidato(NamedTuple):
    """Un vecino del vector semilla.

    `NamedTuple` es una tupla con nombres: se usa como `candidato.distancia` y
    no se puede modificar. Lo más parecido en Java es un `record`.
    """

    pk: int
    id_tmdb: int
    tipo: str  # el del dominio: `pelicula` o `serie`
    distancia: float


def _normalizar(vector):
    """El mismo vector, pero midiendo 1 (norma L2). `None` si mide cero.

    La distancia coseno compara hacia dónde apuntan dos vectores, no cuánto
    miden. Normalizar antes de mezclar hace que cada parte pese lo que dice su
    peso y no lo que mide.
    """
    vector = np.asarray(vector, dtype=np.float64)
    norma = np.linalg.norm(vector)
    if norma == 0:
        return None
    return vector / norma


def peso_del_nombre(cantidad_de_titulos):
    """Cuánto pesa el nombre de la lista según cuántos títulos tienen vector (D-1).

    Con un título el nombre es la mitad de la intención (0.50); con dos, un
    tercio; desde seis, 0.15: los títulos hablan y el nombre solo inclina.
    """
    return max(PESO_MINIMO_DEL_NOMBRE, 1 / (cantidad_de_titulos + 1))


def _centroide(produccion_ids):
    """Promedio de los vectores `ready` de las semillas y cuántas lo tenían.

    El promedio lo calcula Postgres (`avg(vector)`): viaja un solo vector en
    vez de uno por título. Medido el 13/11/2026 con 1 000 semillas: 14 ms en
    SQL contra 273 ms trayéndolos a Python.
    """
    if not produccion_ids:
        return None, 0
    # `aggregate` devuelve un diccionario con una fila de totales, como un
    # `SELECT avg(...), count(*)` sin `GROUP BY`.
    totales = ProduccionEmbedding.objects.filter(
        produccion_id__in=produccion_ids, estado=EstadoEmbedding.READY
    ).aggregate(promedio=Avg("vector"), cantidad=Count("pk"))
    if not totales["cantidad"]:
        return None, 0
    return _normalizar(totales["promedio"]), totales["cantidad"]


def _mezclar_nombre(centroide, vector_nombre, peso):
    """`normalizar((1 − w) · centroide + w · nombre)`, con los dos ya normalizados."""
    nombre = _normalizar(vector_nombre)
    if nombre is None:
        return centroide
    return _normalizar((1 - peso) * centroide + peso * nombre)


def vector_semilla(produccion_ids, *, vector_nombre=None, peso_nombre=None):
    """El vector que representa a las semillas, o `None` si ninguna tiene vector.

    Las semillas sin vector `ready` (recién agregadas, embedding pendiente) se
    saltean. Con `vector_nombre`, el nombre de la lista entra con el peso de
    `peso_del_nombre` (o con `peso_nombre`, si se pasa uno). Sin ningún título
    con vector no hay búsqueda local, aunque haya nombre.
    """
    centroide, cantidad = _centroide(produccion_ids)
    if centroide is None or vector_nombre is None:
        return centroide
    if peso_nombre is None:
        peso_nombre = peso_del_nombre(cantidad)
    return _mezclar_nombre(centroide, vector_nombre, peso_nombre)


def candidatos(vector, *, excluir_ids, tipos=None, limite=_LIMITE_CANDIDATOS):
    """Los `limite` títulos más cercanos a `vector`, del más cercano al más lejano.

    `excluir_ids` son las semillas (pk de `ProduccionAudiovisual`): un título
    no se sugiere a sí mismo ni a lo que ya está en la lista. `tipos` usa los
    valores del dominio (`TipoProduccion`); sin él vienen películas y series.
    Solo entran títulos con póster y con nota de TMDB (D-5): una tarjeta sin
    póster se ve rota, y `> 0` deja afuera también los `NULL`.
    """
    cercanos = (
        ProduccionEmbedding.objects.filter(
            estado=EstadoEmbedding.READY,
            produccion__tipo__in=tipos or TipoProduccion.values,
            produccion__calificacion_promedio__gt=0,
        )
        .exclude(produccion__poster="")
        .exclude(produccion_id__in=list(excluir_ids))
        # `annotate` agrega una columna calculada a cada fila: acá, la
        # distancia coseno (`<=>` en pgvector) entre su vector y el pedido.
        .annotate(distancia=CosineDistance("vector", vector))
        .order_by("distancia")
        .values_list(
            "produccion_id", "produccion__id_tmdb", "produccion__tipo", "distancia"
        )[:limite]
    )
    # Los dos `SET LOCAL` y el `SELECT` van en UNA transacción: `SET LOCAL` dura
    # hasta que termina, y sin `atomic()` Django confirma cada `execute` por
    # separado, así que los ajustes no llegarían a la consulta.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL hnsw.ef_search = {_EF_SEARCH}")
            # El índice HNSW junta `ef_search` vecinos y RECIÉN DESPUÉS aplica el
            # `WHERE`. Si esos vecinos son justo los excluidos (una lista de 1 000
            # títulos parecidos), devuelve menos de lo pedido, o nada, sin avisar.
            # Con `iterative_scan` sigue buscando hasta juntar `limite` filas;
            # `relaxed_order` permite que salgan apenas desordenadas, y el
            # `ORDER BY` de arriba las vuelve a ordenar.
            cursor.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
        # Un queryset es perezoso: la consulta sale recién acá, al recorrerlo.
        return [Candidato(*fila) for fila in cercanos]


class Relleno(NamedTuple):
    """Lo que aportó TMDB y si se pudo pedir todo (`False`: falló o se cortó)."""

    tarjetas: list
    completo: bool


def _tarjeta_tmdb(item, tipo):
    """Un resultado de TMDB con la forma de un ítem de lista, o `None` si no sirve.

    Piso de calidad (D-5): sin contenido adulto, con 10 votos o más y con
    póster. TMDB llama `title`/`release_date` a lo de una película y
    `name`/`first_air_date` a lo de una serie.
    """
    campo_titulo = "title" if tipo == "movie" else "name"
    titulo = (item.get(campo_titulo) or "").strip()
    if (
        not isinstance(item.get("id"), int)
        or item.get("adult")
        or (item.get("vote_count") or 0) < MIN_VOTOS_TMDB
        or not item.get("poster_path")
        or not titulo
    ):
        return None
    fecha = item.get("release_date" if tipo == "movie" else "first_air_date") or ""
    return {
        "id_tmdb": item["id"],
        "tipo": tipo,
        "titulo": titulo,
        "poster": item["poster_path"],
        # La fecha llega como «2014-11-05»: los primeros 4 caracteres son el año.
        "anio": int(fecha[:4]) if fecha[:4].isdigit() else None,
        "calificacion_promedio": item.get("vote_average") or None,
        # `CatalogoConRespaldo` anota qué campos completó con el inglés.
        "campos_en_ingles": ["titulo"] if campo_titulo in item.get(MARCA, []) else [],
        "origen": "tmdb",
    }


def relleno_tmdb(semillas_tmdb, *, servicio, excluir_pares):
    """Recomendaciones de TMDB para hasta 3 semillas, intercaladas (design §5).

    `semillas_tmdb` y `excluir_pares` son pares `(id_tmdb, tipo de TMDB)`, como
    los de `vistos()`. `servicio` responde `get_recommendations` (el
    `TMDBClientCache` del idioma pedido: 24 h de caché, así que una semilla ya
    consultada no cuesta ninguna llamada).

    Nunca lanza por culpa de TMDB: que falte el relleno no es un error. Si TMDB
    falla o se acaban las 6 llamadas, devuelve lo que juntó con
    `completo=False`, y quien llama guarda ese pool por poco tiempo.
    """
    semillas = list(semillas_tmdb)[:SEMILLAS_TMDB]
    ya_estan = set(excluir_pares) | set(semillas)
    por_semilla = []
    completo = True
    # `with` abre el tope y lo cierra al salir del bloque, pase lo que pase:
    # es el `try-with-resources` de Java.
    with tope_de_llamadas(MAX_LLAMADAS_TMDB):
        for id_tmdb, tipo in semillas:
            try:
                datos = servicio.get_recommendations(id_tmdb, tipo)
            except TMDBNotFound:
                # TMDB no conoce esa semilla: insistir no cambia nada.
                continue
            except TMDBError:
                # Caído, lento o sin presupuesto: no se prueba con las demás,
                # cada intento fallido suma segundos de reintentos.
                logger.warning("similares: falló el relleno de TMDB", exc_info=True)
                completo = False
                break
            tarjetas = (
                _tarjeta_tmdb(item, tipo) for item in datos.get("results") or []
            )
            por_semilla.append([tarjeta for tarjeta in tarjetas if tarjeta])

    intercaladas = []
    # `zip_longest` arma vueltas: la primera de cada semilla, después la
    # segunda… y pone `None` donde a una semilla ya no le quedan.
    for vuelta in zip_longest(*por_semilla):
        for tarjeta in vuelta:
            if tarjeta is None:
                continue
            par = (tarjeta["id_tmdb"], tarjeta["tipo"])
            if par not in ya_estan:
                ya_estan.add(par)
                intercaladas.append(tarjeta)
    return Relleno(intercaladas, completo)
