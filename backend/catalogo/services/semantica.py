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

from catalogo.models import (
    KEYWORD_SOFTCORE,
    EstadoEmbedding,
    ProduccionAudiovisual,
    ProduccionEmbedding,
)
from catalogo.services.embeddings import (
    PRESUPUESTO_CARGA,
    PRESUPUESTO_CHAT,
    EmbeddingProviderError,
    generar_vector,
    modelo_cargado,
)
from catalogo.services.recomendado import TIPO_DOMINIO, TIPO_TMDB
from catalogo.tasks import CLAVE_CARGA_MODELO, calentar_modelo

logger = logging.getLogger(__name__)

# Se traen más de los que se devuelven porque los filtros y `excluir` descartan.
_CANDIDATOS = 50
_MAXIMO_RESULTADOS = 10

# Cuántos candidatos mira el índice HNSW. El valor por defecto de pgvector es
# 40: con él, pedir 50 devolvería 40 o menos sin avisar.
_EF_SEARCH = 100


# Una carga por minuto alcanza: `calentar_modelo` espera hasta 60 s.
_SEGUNDOS_ENTRE_CARGAS = 60


def pedir_carga_del_modelo():
    """Encola la carga del modelo. Nunca lanza: es una ayuda, no un requisito."""
    try:
        if not cache.add(CLAVE_CARGA_MODELO, True, _SEGUNDOS_ENTRE_CARGAS):
            return
        try:
            # Vence: sin worker, un pedido viejo no sirve y solo llenaría la cola.
            calentar_modelo.apply_async(expires=_SEGUNDOS_ENTRE_CARGAS)
        except Exception:
            # Sin esto, un broker caído frenaría los reintentos durante un minuto.
            cache.delete(CLAVE_CARGA_MODELO)
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
        # El softcore se saca ANTES de cortar a los más cercanos: si se sacara después,
        # una consulta cercana al erotismo dejaría pocos resultados o ninguno.
        .exclude(produccion__keywords__contains=[KEYWORD_SOFTCORE])
        .order_by(CosineDistance("vector", vector))
        .values_list("produccion_id", flat=True)[:_CANDIDATOS]
    )
    # `SET LOCAL` dura hasta el fin de la transacción: la conexión no queda
    # con este valor para quien la use después.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL hnsw.ef_search = {_EF_SEARCH}")
        return list(cercanos)


# Cómo guarda C-04a el keyword de TMDB 818: por su nombre, en inglés.
KEYWORD_BASADA_EN_LIBRO = "based on novel or book"


def buscar_semantico(
    consulta,
    *,
    generos=None,
    tipo=None,
    anio_desde=None,
    anio_hasta=None,
    nota_minima=None,
    duracion_max=None,
    basada_en_libro=False,
    excluir=(),
):
    """Devuelve hasta 10 producciones parecidas a `consulta`, las mejores primero.

    `basada_en_libro` deja los títulos cuyos `keywords` incluyen el de TMDB «based on
    novel or book». `generos` usa los nombres en inglés de `ProduccionAudiovisual.generos`, y
    alcanza con que coincida uno. Un título sin el dato que pide un filtro (por
    ejemplo, una serie sin `duracion`) queda afuera. `excluir` recibe pares
    `(id_tmdb, tipo)`. Tanto ahí como en `tipo`, el tipo es el de TMDB (`movie`
    o `tv`), como en `vistos()` y las tarjetas, no el valor guardado en el modelo.

    Si Ollama falla, propaga `EmbeddingProviderError`: quien llama decide qué
    hacer, y nunca recibe un resultado a medias.
    """
    ids = _ids_mas_cercanos(_vector_de(consulta))

    # `disponible_en_tmdb`: una lápida pierde su embedding al nacer, pero uno en
    # vuelo no puede devolver un título sin contenido (#180).
    producciones = ProduccionAudiovisual.objects.filter(
        pk__in=ids, disponible_en_tmdb=True
    )
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
    if basada_en_libro:
        # `contains` sobre un ArrayField es el `@>` de Postgres: «el array incluye».
        producciones = producciones.filter(keywords__contains=[KEYWORD_BASADA_EN_LIBRO])

    excluidas = set(excluir)
    posicion = {id_: puesto for puesto, id_ in enumerate(ids)}
    ordenadas = sorted(producciones, key=lambda p: posicion[p.pk])
    return [p for p in ordenadas if (p.id_tmdb, TIPO_TMDB[p.tipo]) not in excluidas][
        :_MAXIMO_RESULTADOS
    ]
