"""Búsqueda por significado sobre el catálogo local (B-06).

Sirve para lo que `discover` de TMDB no puede expresar, como «algo melancólico
sobre viajes en el tiempo». Convierte la consulta en vector, busca los vectores
más parecidos en pgvector y recién después aplica los filtros en SQL.
"""

import logging
import time

from django.core.cache import cache
from django.db import connection, transaction
from pgvector.django import CosineDistance

from catalogo.models import EstadoEmbedding, ProduccionAudiovisual, ProduccionEmbedding
from catalogo.services.embeddings import (
    PRESUPUESTO_CARGA,
    PRESUPUESTO_CHAT,
    EmbeddingProviderError,
    generar_vector,
    modelo_cargado,
)
from catalogo.services.recomendado import TIPO_DOMINIO, TIPO_TMDB
from catalogo.tasks import calentar_modelo

logger = logging.getLogger(__name__)

# Se traen más de los que se devuelven porque los filtros y `excluir` descartan.
_CANDIDATOS = 50
_MAXIMO_RESULTADOS = 10

# Cuántos candidatos mira el índice HNSW. El valor por defecto de pgvector es
# 40: con él, pedir 50 devolvería 40 o menos sin avisar.
_EF_SEARCH = 100


# Abrir y cerrar el panel no debe llenar la cola: una carga por minuto alcanza.
_CLAVE_CARGA = "chatbot:carga_modelo"
_SEGUNDOS_ENTRE_CARGAS = 60


def pedir_carga_del_modelo():
    """Encola la carga del modelo. Nunca lanza: es una ayuda, no un requisito."""
    try:
        if not cache.add(_CLAVE_CARGA, True, _SEGUNDOS_ENTRE_CARGAS):
            return
        try:
            calentar_modelo.delay()
        except Exception:
            # Sin esto, un broker caído frenaría los reintentos durante un minuto.
            cache.delete(_CLAVE_CARGA)
            raise
    except Exception:
        # Amplio a propósito: si Redis falla, el chat sigue funcionando.
        logger.exception("No se pudo encolar la carga del modelo")


def _vector_de(consulta):
    """Embebe la consulta, esperando la carga del modelo si hace falta."""
    cargado = modelo_cargado()
    inicio = time.perf_counter()
    try:
        return generar_vector(
            consulta, **(PRESUPUESTO_CHAT if cargado else PRESUPUESTO_CARGA)
        )
    except EmbeddingProviderError:
        # Al cortar, Ollama abandona la carga: otra conexión tiene que seguirla.
        if not cargado:
            pedir_carga_del_modelo()
        raise
    finally:
        milisegundos = (time.perf_counter() - inicio) * 1000
        logger.info("buscar_semantico: cargado=%s vector_ms=%d", cargado, milisegundos)


def _ids_mas_cercanos(vector):
    """Ids de las producciones `ready` más cercanas, de la mejor a la peor."""
    cercanos = (
        ProduccionEmbedding.objects.filter(estado=EstadoEmbedding.READY)
        .order_by(CosineDistance("vector", vector))
        .values_list("produccion_id", flat=True)[:_CANDIDATOS]
    )
    # `SET LOCAL` dura hasta el fin de la transacción: la conexión no queda
    # con este valor para quien la use después.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL hnsw.ef_search = {_EF_SEARCH}")
        return list(cercanos)


def buscar_semantico(
    consulta,
    *,
    generos=None,
    tipo=None,
    anio_desde=None,
    anio_hasta=None,
    nota_minima=None,
    duracion_max=None,
    excluir=(),
):
    """Devuelve hasta 10 producciones parecidas a `consulta`, las mejores primero.

    `generos` usa los nombres en inglés de `ProduccionAudiovisual.generos`, y
    alcanza con que coincida uno. Un título sin el dato que pide un filtro (por
    ejemplo, una serie sin `duracion`) queda afuera. `excluir` recibe pares
    `(id_tmdb, tipo)`. Tanto ahí como en `tipo`, el tipo es el de TMDB (`movie`
    o `tv`), como en `vistos()` y las tarjetas, no el valor guardado en el modelo.

    Si Ollama falla, propaga `EmbeddingProviderError`: quien llama decide qué
    hacer, y nunca recibe un resultado a medias.
    """
    ids = _ids_mas_cercanos(_vector_de(consulta))

    producciones = ProduccionAudiovisual.objects.filter(pk__in=ids)
    if generos:
        producciones = producciones.filter(generos__overlap=generos)
    if tipo:
        producciones = producciones.filter(tipo=TIPO_DOMINIO[tipo])
    if anio_desde is not None:
        producciones = producciones.filter(fecha_lanzamiento__year__gte=anio_desde)
    if anio_hasta is not None:
        producciones = producciones.filter(fecha_lanzamiento__year__lte=anio_hasta)
    if nota_minima is not None:
        producciones = producciones.filter(calificacion_promedio__gte=nota_minima)
    if duracion_max is not None:
        producciones = producciones.filter(duracion__lte=duracion_max)

    excluidas = set(excluir)
    posicion = {id_: puesto for puesto, id_ in enumerate(ids)}
    ordenadas = sorted(producciones, key=lambda p: posicion[p.pk])
    return [p for p in ordenadas if (p.id_tmdb, TIPO_TMDB[p.tipo]) not in excluidas][
        :_MAXIMO_RESULTADOS
    ]
