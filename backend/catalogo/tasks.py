"""Tareas asincrónicas del catálogo (C-04a).

Celery garantiza entrega "al menos una vez": la misma tarea puede llegar dos
veces (reinicio del worker) o a dos workers en paralelo. Toda la lógica de
abajo existe para que eso no derive en trabajo duplicado ni en filas
inconsistentes.
"""

import logging

from celery import shared_task

from catalogo.models import EstadoEmbedding, ProduccionEmbedding
from catalogo.services.embeddings import (
    MODEL_VERSION,
    calcular_source_hash,
    construir_texto_canonico,
    generar_vector,
)

logger = logging.getLogger(__name__)

# Estados desde los que una fila puede tomarse para procesar. `processing`
# queda afuera (ya la agarró alguien) y `ready` también: un vector utilizable
# no se degrada a `failed` por un proveedor caído. Refrescar los `ready` cuyo
# texto cambió es trabajo del backfill de C-04b, que los vuelve a `pending`.
_RECLAMABLES = (EstadoEmbedding.PENDING, EstadoEmbedding.FAILED)


@shared_task(name="catalogo.generar_embedding")
def generar_embedding(produccion_id):
    """Genera el vector semántico de una producción ya materializada.

    Nunca lanza: si el proveedor falla, la fila queda en `failed` y el
    backfill la recupera después. Propagar la excepción haría que Celery
    reintentara en loop y, sobre todo, no aportaría nada: la producción sigue
    visible en el catálogo aunque su embedding no exista.
    """
    embedding = (
        ProduccionEmbedding.objects.select_related("produccion")
        .filter(produccion_id=produccion_id)
        .first()
    )
    if embedding is None:
        # Puede pasar si la producción se borró entre el encolado y el consumo.
        logger.warning(
            "generar_embedding: no hay embedding para produccion_id=%s", produccion_id
        )
        return

    texto = construir_texto_canonico(embedding.produccion)
    source_hash = calcular_source_hash(texto)

    # Defensa 1: si el vector guardado corresponde a este mismo texto y modelo,
    # no hay nada que recalcular.
    if (
        embedding.estado == EstadoEmbedding.READY
        and embedding.source_hash == source_hash
        and embedding.model_version == MODEL_VERSION
    ):
        return

    # Defensa 2: reclamar la fila. Un UPDATE condicional es atómico en la base,
    # así que de dos workers simultáneos exactamente uno recibe 1 fila y el
    # otro 0, sin locks explícitos.
    reclamadas = ProduccionEmbedding.objects.filter(
        produccion_id=produccion_id, estado__in=_RECLAMABLES
    ).update(estado=EstadoEmbedding.PROCESSING)
    if reclamadas == 0:
        return

    # Defensa 3: la llamada al proveedor queda FUERA de cualquier transacción.
    # Puede tardar segundos y no debe mantener ocupada una conexión ni bloquear
    # a nadie (decisión 08/09/2026).
    try:
        vector = generar_vector(texto)
        if vector is None:
            raise ValueError("El proveedor de embeddings devolvió None")
    except Exception:
        # Amplio a propósito: es el límite con un sistema externo. Cualquier
        # fallo debe terminar en `failed`, nunca tumbar al worker ni dejar la
        # fila trabada en `processing`.
        logger.exception(
            "generar_embedding: el proveedor falló para produccion_id=%s",
            produccion_id,
        )
        ProduccionEmbedding.objects.filter(produccion_id=produccion_id).update(
            estado=EstadoEmbedding.FAILED
        )
        return

    ProduccionEmbedding.objects.filter(produccion_id=produccion_id).update(
        vector=vector,
        estado=EstadoEmbedding.READY,
        source_hash=source_hash,
        model_version=MODEL_VERSION,
    )


@shared_task(name="catalogo.sync_catalogo_diaria")
def sync_catalogo_diaria():
    """Sincronización nocturna del catálogo (C-04b). Ver CELERY_BEAT_SCHEDULE."""
    # Cuerpo mínimo para verificar que beat dispara: la lógica llega en 2.7.
    logger.info("sync_catalogo_diaria: corrida iniciada")
