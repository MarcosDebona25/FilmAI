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
import math
import random
from dataclasses import asdict, dataclass
from itertools import zip_longest
from typing import NamedTuple

import numpy as np
from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import Avg, Count
from pgvector.django import CosineDistance

from catalogo.exceptions import TMDBError, TMDBNotFound
from catalogo.models import (
    KEYWORD_SOFTCORE,
    EstadoEmbedding,
    ProduccionAudiovisual,
    ProduccionEmbedding,
    TipoProduccion,
)
from catalogo.presupuesto import tope_de_llamadas
from catalogo.services.fallback import MARCA
from catalogo.services.materialization import materializar_listado_en_segundo_plano
from catalogo.services.recomendado import TIPO_TMDB
from catalogo.services.traducciones import campos_en_ingles, texto_localizado

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
# 3 semillas por 2 llamadas (el idioma pedido y el respaldo en inglés),
# reintentos incluidos.
MAX_LLAMADAS_TMDB = 6

# Hasta qué distancia coseno un vecino cuenta como «cercano» (design §4). Un
# título típico tiene 50 o más vecinos por debajo; uno de nicho tiene pocos, y
# ahí es justo cuando conviene que TMDB complete.
DISTANCIA_MAXIMA = 0.40
# Con menos cercanos que esto se le pide relleno a TMDB.
MINIMO_CERCANOS = 20
# Seis páginas de «Ver otras», con margen para lo que saca «Vistas».
TAMANO_POOL = 60
TAMANO_PAGINA = 10

# Cuánto vive un pool en la caché. El catálogo local cambia una vez por noche y
# TMDB guarda `/recommendations` 24 h. Uno incompleto (una semilla sin vector,
# TMDB caído, nombre sin embeber) dura poco para que se rearme pronto.
TTL_POOL = 24 * 3600
TTL_POOL_INCOMPLETO = 5 * 60


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
    """`normalizar((1 - w) · centroide + w · nombre)`, con los dos ya normalizados."""
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
    póster se ve rota, y `> 0` deja afuera también los `NULL`. Los `softcore` quedan
    afuera siempre (filtro de contenido adulto, 13/11/2026).
    """
    cercanos = (
        ProduccionEmbedding.objects.filter(
            estado=EstadoEmbedding.READY,
            produccion__tipo__in=tipos or TipoProduccion.values,
            produccion__calificacion_promedio__gt=0,
        )
        .exclude(produccion__poster="")
        # Erotismo que TMDB no marca `adult`: ver `KEYWORD_SOFTCORE`.
        .exclude(produccion__keywords__contains=[KEYWORD_SOFTCORE])
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


# `frozen=True` hace que los campos no se puedan reasignar después de crear el
# objeto, como los campos `final` de un `record` de Java.
@dataclass(frozen=True)
class Pool:
    """Los títulos parecidos a un conjunto de semillas, ya ordenados y mezclados.

    Es lo que se guarda en la caché, y nunca tiene nada del usuario: «Vistas»
    se saca al leerlo (`pagina`). Solo lleva tipos que JSON sabe escribir
    (listas, diccionarios, números, texto), porque la caché de Redis del
    proyecto serializa con JSON.

    Cada entrada de `entradas` es un diccionario con `origen`, `id_tmdb` y
    `tipo` (el de TMDB). Las del catálogo llevan además solo su `pk`: el título
    y el póster se leen de la base al armar la página, en el idioma del pedido.
    Las de TMDB ya son la tarjeta completa.
    """

    entradas: list
    nombre_usado: bool  # el nombre de la lista entró en el vector
    completo: bool  # False → se guarda por poco tiempo
    # Para el registro de cada pedido:
    semillas_con_vector: int
    cercanos: int  # locales por debajo de `DISTANCIA_MAXIMA`
    de_tmdb: int


def mezclar_con_pesos(entradas, semilla_azar):
    """Mezcla al azar, pero dándole más chances de salir primero a lo más cercano.

    `entradas` llega ordenado del mejor al peor. Un pool en ese orden exacto
    haría que «Ver otras» vaya siempre de bueno a malo, y que la misma lista
    muestre siempre las mismas diez.

    Método de Efraimidis y Spirakis: a cada entrada se le sortea un número `u`
    entre 0 y 1 y se la ordena por `u ** (1 / peso)`, de mayor a menor. Con
    peso alto esa clave queda cerca de 1 casi siempre; con peso bajo, se hunde.
    El peso baja con el puesto: `1 / (1 + puesto / 10)`.

    El sorteo sale de `random.Random(semilla)`: la misma semilla da siempre los
    mismos números. Como la semilla es la firma de la clave de caché, el orden
    se puede repetir (tests, dos pestañas) y cambia cuando cambia la lista.
    """
    # No es azar criptográfico ni hace falta: solo decide un orden de tarjetas.
    azar = random.Random(str(semilla_azar))
    con_clave = [
        # `1 / peso` es `1 + puesto / 10`.
        (azar.random() ** (1 + puesto / 10), puesto, entrada)
        for puesto, entrada in enumerate(entradas)
    ]
    # Se ordena por la clave; el puesto desempata sin comparar diccionarios.
    con_clave.sort(key=lambda terna: (-terna[0], terna[1]))
    return [entrada for _, _, entrada in con_clave]


def _entrada_local(candidato):
    return {
        "origen": "catalogo",
        "pk": candidato.pk,
        "id_tmdb": candidato.id_tmdb,
        "tipo": TIPO_TMDB[candidato.tipo],
    }


def armar_pool(
    produccion_ids,
    *,
    semillas_tmdb,
    servicio,
    semilla_azar,
    tipos=None,
    vector_nombre=None,
    nombre_omitido=False,
):
    """Arma el pool de parecidos a las semillas (design §2 a §6).

    - `produccion_ids`: pk de las semillas en el catálogo (vacío si el título
      de la ficha todavía no está).
    - `semillas_tmdb`: pares `(id_tmdb, tipo de TMDB)` para pedirle relleno a
      TMDB, la más importante primero (se usan 3 como mucho).
    - `servicio`: el `TMDBClientCache` del idioma del pedido.
    - `semilla_azar`: de dónde sale el orden de la mezcla (la firma de la clave).
    - `tipos`: tipos del dominio a traer; sin él, películas y series.
    - `vector_nombre`: el nombre de la lista ya embebido, si «dice algo».
    - `nombre_omitido`: había un nombre para usar y no se pudo embeber.

    Orden antes de mezclar: locales cercanos, TMDB, locales lejanos.
    """
    produccion_ids = list(dict.fromkeys(produccion_ids))
    centroide, con_vector = _centroide(produccion_ids)
    # Una semilla sin vector alcanza para que el pool dure poco: cuando su
    # embedding esté listo la firma de la lista no cambia, y un pool de 24 h
    # la ignoraría todo ese tiempo.
    completo = (
        bool(produccion_ids)
        and con_vector == len(produccion_ids)
        and not nombre_omitido
    )
    nombre_usado = centroide is not None and vector_nombre is not None
    vector = centroide
    if nombre_usado:
        vector = _mezclar_nombre(centroide, vector_nombre, peso_del_nombre(con_vector))

    vecinos = []
    if vector is not None:
        vecinos = candidatos(vector, excluir_ids=produccion_ids, tipos=tipos)
    cercanos = [vecino for vecino in vecinos if vecino.distancia <= DISTANCIA_MAXIMA]
    lejanos = vecinos[len(cercanos) :]

    tarjetas = []
    if len(cercanos) < MINIMO_CERCANOS and semillas_tmdb:
        ya_estan = {(vecino.id_tmdb, TIPO_TMDB[vecino.tipo]) for vecino in vecinos}
        ya_estan.update(
            (id_tmdb, TIPO_TMDB[tipo])
            for id_tmdb, tipo in ProduccionAudiovisual.objects.filter(
                pk__in=produccion_ids
            ).values_list("id_tmdb", "tipo")
        )
        relleno = relleno_tmdb(semillas_tmdb, servicio=servicio, excluir_pares=ya_estan)
        tarjetas = relleno.tarjetas
        completo = completo and relleno.completo

    entradas = [
        *(_entrada_local(vecino) for vecino in cercanos),
        *tarjetas,
        *(_entrada_local(vecino) for vecino in lejanos),
    ][:TAMANO_POOL]
    return Pool(
        entradas=mezclar_con_pesos(entradas, semilla_azar),
        nombre_usado=nombre_usado,
        completo=completo,
        semillas_con_vector=con_vector,
        cercanos=len(cercanos),
        de_tmdb=sum(1 for entrada in entradas if entrada["origen"] == "tmdb"),
    )


def pool_en_cache(clave, armar, *, ttl):
    """Devuelve `(pool, acierto)`: el pool guardado en `clave`, o uno recién armado.

    `armar` es una función sin argumentos que arma el pool; solo se llama si la
    caché no lo tiene. `ttl` recibe el pool y dice cuántos segundos guardarlo.
    Pasar funciones como argumento es lo que en Java se hace con un `Supplier`
    y una `Function`.
    """
    guardado = cache.get(clave)
    if guardado is not None:
        try:
            return Pool(**guardado), True
        except TypeError:
            # Guardado con otra forma (una versión anterior): se rearma.
            pass
    pool = armar()
    cache.set(clave, asdict(pool), ttl(pool))
    return pool, False


def _visibles(pool, excluir_pares):
    excluidos = set(excluir_pares)
    return [
        entrada
        for entrada in pool.entradas
        if (entrada["id_tmdb"], entrada["tipo"]) not in excluidos
    ]


def cantidad_de_paginas(pool, *, excluir_pares=(), tamano=TAMANO_PAGINA):
    """Cuántas páginas tiene el pool para este usuario, sin lo excluido."""
    return math.ceil(len(_visibles(pool, excluir_pares)) / tamano)


def _tarjeta_local(produccion, idioma):
    """La tarjeta de un título del catálogo, con la forma de un ítem de lista."""
    fecha = produccion.fecha_lanzamiento
    return {
        "id_tmdb": produccion.id_tmdb,
        "tipo": TIPO_TMDB[produccion.tipo],
        "titulo": texto_localizado(produccion, "titulo", idioma),
        "poster": texto_localizado(produccion, "poster", idioma),
        "anio": fecha.year if fecha else None,
        "calificacion_promedio": produccion.calificacion_promedio or None,
        "campos_en_ingles": campos_en_ingles(produccion, idioma),
        "origen": "catalogo",
    }


def pagina(pool, *, excluir_pares=(), numero=1, tamano=TAMANO_PAGINA, idioma=None):
    """Las tarjetas de la página `numero` del pool (la primera es la 1).

    `excluir_pares` son pares `(id_tmdb, tipo de TMDB)`, como los de `vistos()`:
    se sacan ANTES de cortar, así la página sigue llena. Pasada la última
    página devuelve una lista vacía. No recalcula nada: el pool ya viene
    ordenado, acá solo se leen de la base los títulos de esta página.
    """
    corte = _visibles(pool, excluir_pares)[(numero - 1) * tamano : numero * tamano]
    pks = [entrada["pk"] for entrada in corte if entrada["origen"] == "catalogo"]
    producciones = {}
    if pks:
        consulta = ProduccionAudiovisual.objects.filter(pk__in=pks)
        if idioma and idioma != settings.IDIOMA_POR_DEFECTO:
            # Trae las traducciones de todas en UNA consulta más, en vez de una
            # por tarjeta (el problema «N+1» de los ORM, igual que en JPA).
            consulta = consulta.prefetch_related("traducciones")
        producciones = {produccion.pk: produccion for produccion in consulta}

    tarjetas = []
    for entrada in corte:
        if entrada["origen"] != "catalogo":
            tarjetas.append(entrada)
        elif entrada["pk"] in producciones:
            # Si se borró después de armar el pool, simplemente no aparece.
            tarjetas.append(_tarjeta_local(producciones[entrada["pk"]], idioma))
    return tarjetas


def materializar_mostradas(tarjetas):
    """Encola la materialización de las tarjetas de TMDB que se mostraron.

    Como en cualquier listado (C-04a): entran al catálogo y reciben su vector,
    así el próximo pool ya las encuentra localmente. Nunca lanza: si la base o
    el broker fallan, la respuesta sale igual.
    """
    de_tmdb = [
        {"id": tarjeta["id_tmdb"], "media_type": tarjeta["tipo"]}
        for tarjeta in tarjetas
        if tarjeta["origen"] == "tmdb"
    ]
    if not de_tmdb:
        return
    try:
        materializar_listado_en_segundo_plano(de_tmdb)
    except Exception:
        # Amplio a propósito, como en `catalogo/views.py`: materializar es una
        # ayuda para la próxima vez, no parte de la respuesta.
        logger.exception("similares: no se pudo encolar la materialización")
