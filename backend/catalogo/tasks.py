"""Tareas asincrónicas del catálogo (C-04a, C-04b).

Celery garantiza entrega "al menos una vez": la misma tarea puede llegar dos
veces (reinicio del worker) o a dos workers en paralelo. Toda la lógica de
abajo existe para que eso no derive en trabajo duplicado ni en filas
inconsistentes.
"""

import logging

from celery import shared_task
from django.conf import settings

from catalogo.models import EstadoEmbedding, ProduccionAudiovisual, ProduccionEmbedding
from catalogo.services.adapter import tmdb_a_dominio
from catalogo.services.embeddings import (
    MODEL_VERSION,
    calcular_source_hash,
    construir_texto_canonico,
    generar_vector,
)
from catalogo.services.tmdb import get_catalog_service

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


# Qué recorre cada corrida nocturna y cómo se sabe el tipo de cada ítem:
# (nombre, cómo pedirla, tipo fijo — o None si cada ítem trae `media_type`).
# Son cuatro páginas de ~20 ítems: suficiente para captar novedades sin
# convertir la sync en un rastreo de todo TMDB, que es trabajo del seed (C-04c).
# Solo `trending/all` mezcla tipos (y puede traer `person`); en las otras tres
# fuentes el tipo lo dicta el endpoint. Verificado contra la API el 17/09/2026.
_FUENTES = (
    ("trending", lambda s: s.get_trending("all", "week", 1), None),
    ("now_playing", lambda s: s.get_now_playing(1), "movie"),
    ("discover_movie", lambda s: s.discover("movie", page=1), "movie"),
    ("discover_tv", lambda s: s.discover("tv", page=1), "tv"),
)


# Tope defensivo del paginador de `/changes`. La lista real anda entre 74 y
# 98 páginas por tipo según el día (medido 15/09 y 17/09/2026), así que 200
# deja margen sin permitir que un día raro convierta la sync en un rastreo sin
# fin. Lo que quede afuera lo cubre la red de seguridad de 90 días.
_MAX_PAGINAS_CAMBIOS = 200


def _ids_cambiados(servicio, tipo_tmdb):
    """IDs que TMDB reporta como modificados en las últimas 24 h."""
    ids, pagina = set(), 1
    while pagina <= _MAX_PAGINAS_CAMBIOS:
        payload = servicio.get_changes(tipo_tmdb, pagina)
        ids.update(item["id"] for item in payload.get("results") or [] if "id" in item)
        if pagina >= payload.get("total_pages", 1):
            break
        pagina += 1
    return ids


@shared_task(name="catalogo.sync_catalogo_diaria")
def sync_catalogo_diaria():
    """Sync nocturna del catálogo (C-04b): refresco + descubrimiento.

    Dos pasadas con trabajos distintos:

    1. Refresco: cruza los IDs que ya tenemos con los que TMDB reporta como
       modificados en las últimas 24 h y re-enriquece esa intersección con
       `forzar=True`. Es lo que mantiene la copia honesta cuando se estrena un
       título, se agrega una temporada o cambia una calificación.
    2. Descubrimiento: recorre los listados y materializa cada ítem SIN que
       ningún usuario lo haya abierto. Es lo que rompe el arranque en frío: la
       búsqueda semántica busca entre las filas de nuestra base, y sin esto la
       base solo tendría lo que alguien ya miró.

    El refresco va primero a propósito: una película en cartelera se edita
    activamente en TMDB, así que suele estar en la lista de cambios. Si el
    descubrimiento la enriqueciera primero, el refresco la volvería a
    enriquecer segundos después. Al revés, el refresco solo toca filas que
    existían antes de esta noche y el descubrimiento saltea las frescas.

    Ninguna pasada escribe por su cuenta: todo pasa por `materializar()`, el
    único camino de escritura del catálogo. Un ítem de listado no alcanza para
    llenar una fila (no trae géneros con nombre, créditos ni keywords), y así
    tampoco hay que duplicar el mapeo ni traducir `genre_ids`.

    Los fallos tienen dos niveles:
    - Por tipo: si `/changes` falla entero (ej. TMDB caído), se saltea el
      refresco de ese tipo y sigue el resto. La red de seguridad de 90 días
      cubre lo que quede sin refrescar.
    - Por ítem: si un `materializar()` falla (ej. timeout en un ítem
      específico), se cuenta como error y sigue con el siguiente. Misma
      política que las vistas de detalle.

    Devuelve y loguea las estadísticas de la corrida. `actualizadas` cuenta
    las que ya existían antes de la corrida; si se refrescaron o no lo decide
    `materializar()` según `fecha_enriquecimiento`.
    """
    # Import local a propósito: materialization.py importa `generar_embedding`
    # de este módulo, así que importarlo arriba sería un ciclo.
    from catalogo.services.materialization import materializar

    servicio = get_catalog_service()
    # Una sola consulta para saber qué tenemos, en vez de una por ítem. Sirve a
    # las dos pasadas: el refresco cruza contra este conjunto, y el
    # descubrimiento lo usa para distinguir nuevas de existentes (agregando lo
    # creado, así una producción que aparece en dos fuentes cuenta una vez).
    existentes = set(ProduccionAudiovisual.objects.values_list("id_tmdb", "tipo"))
    estadisticas = {
        "nuevas": 0,  # descubrimiento: ítems nuevos materializados
        "actualizadas": 0,  # descubrimiento: ítems existentes re-materializados
        "refrescadas": 0,  # refresco: ítems re-enriquecidos con forzar=True
        "omitidas": 0,
        "errores": 0,
    }

    # --- Pasada 1: refresco ---------------------------------------------
    for tipo_tmdb in ("movie", "tv"):
        tipo = tmdb_a_dominio(tipo_tmdb)
        try:
            cambiados = _ids_cambiados(servicio, tipo_tmdb)
        except Exception:
            logger.exception("sync_catalogo_diaria: falló /%s/changes", tipo_tmdb)
            estadisticas["errores"] += 1
            continue
        # La intersección se hace en Python, no en SQL: meter ~10.000 IDs en
        # un `id_tmdb__in` armaría una consulta enorme sin ganar nada, y dos
        # sets de ese tamaño se cruzan al instante.
        nuestros = {id_tmdb for id_tmdb, t in existentes if t == tipo}
        for id_tmdb in sorted(nuestros & cambiados):
            try:
                materializar(id_tmdb, tipo_tmdb, forzar=True)
            except Exception:
                logger.exception(
                    "sync_catalogo_diaria: falló el refresco de (%s, %s)",
                    id_tmdb,
                    tipo_tmdb,
                )
                estadisticas["errores"] += 1
                continue
            estadisticas["refrescadas"] += 1

    # --- Pasada 2: descubrimiento ----------------------------------------
    for nombre, pedir, tipo_fijo in _FUENTES:
        for item in pedir(servicio).get("results") or []:
            id_tmdb = item.get("id")
            tipo_tmdb = tipo_fijo or item.get("media_type")
            try:
                tipo = tmdb_a_dominio(tipo_tmdb)
            except ValueError:
                # `person` u otro tipo que no es una producción.
                estadisticas["omitidas"] += 1
                continue

            try:
                materializar(id_tmdb, tipo_tmdb)
            except Exception:
                # Amplio a propósito: es el límite con TMDB y con la base.
                logger.exception(
                    "sync_catalogo_diaria: falló (%s, %s) desde %s",
                    id_tmdb,
                    tipo_tmdb,
                    nombre,
                )
                estadisticas["errores"] += 1
                continue

            if (id_tmdb, tipo) in existentes:
                estadisticas["actualizadas"] += 1
            else:
                estadisticas["nuevas"] += 1
                existentes.add((id_tmdb, tipo))

    logger.info("sync_catalogo_diaria: %s", estadisticas)
    return estadisticas


@shared_task(name="catalogo.backfill_embeddings")
def backfill_embeddings(limite=None):
    """Recupera el trabajo de embeddings que quedó sin completar (C-04b).

    `materializar()` encola el embedding UNA sola vez: cuando crea la fila.
    En las visitas siguientes `get_or_create` devuelve `creado=False` y no
    encola nada. Así que una fila que quedó en `pending` porque el broker
    estaba caído, o en `failed` porque el proveedor falló, no la reintenta
    NADIE. Esta tarea es lo que la rescata.

    Recorre dos poblaciones, en orden y compartiendo el mismo tope:

    1. `pending` y `failed` — trabajo que nunca se completó. Se resuelve en
       SQL: hay un índice por `estado`.
    2. `ready` desactualizados — el texto canónico cambió (la sync refrescó la
       producción) o cambió `MODEL_VERSION`. El hash hay que recalcularlo fila
       por fila en Python; la versión del modelo no, pero se comparan juntas
       para recorrer la tabla una sola vez.

    `processing` queda afuera a propósito: alguien la está procesando ahora.

    No calcula el vector, lo REENCOLA. `generar_embedding` ya es dueña del
    reclamo atómico `pending→processing`; repetir esa lógica acá sería una
    segunda fuente de verdad para la idempotencia.

    Ambos recorridos van por `fecha_actualizacion` ascendente: la más vieja
    primero. Como el campo es `auto_now`, procesar una fila la manda al final
    de la fila, y así ninguna queda sin revisarse nunca por quedar siempre
    detrás del tope.

    Si el proveedor falla al regenerar un `ready` desactualizado, la fila
    queda en `failed` conservando el vector viejo: deja de usarse en la
    búsqueda por una noche, y la corrida siguiente la reintenta porque
    `failed` sí es reclamable.

    Limitación conocida: una fila trabada en `processing` (el worker murió a
    mitad) no la recupera nadie. Hace falta un lease con vencimiento, que se
    puede agregar cuando exista el proveedor real (B-06) y las tareas tarden
    de verdad.
    """
    if limite is None:
        limite = settings.CELERY_BACKFILL_LIMIT

    estadisticas = {"reencolados": 0, "desactualizados": 0}

    sin_completar = list(
        ProduccionEmbedding.objects.filter(estado__in=_RECLAMABLES)
        .order_by("fecha_actualizacion")
        .values_list("produccion_id", flat=True)[:limite]
    )
    for produccion_id in sin_completar:
        generar_embedding.delay(produccion_id)
    estadisticas["reencolados"] = len(sin_completar)

    restante = limite - len(sin_completar)
    if restante <= 0:
        logger.info("backfill_embeddings: %s", estadisticas)
        return estadisticas

    listos = (
        ProduccionEmbedding.objects.filter(estado=EstadoEmbedding.READY)
        .select_related("produccion")
        .order_by("fecha_actualizacion")
    )
    for embedding in listos.iterator():
        texto = construir_texto_canonico(embedding.produccion)
        if (
            embedding.model_version == MODEL_VERSION
            and embedding.source_hash == calcular_source_hash(texto)
        ):
            continue
        # Devolverla a `pending` ANTES de encolar, y no solo por prolijidad:
        # `generar_embedding` reclama con `estado__in=_RECLAMABLES`, que no
        # incluye `ready`. Sin esto la tarea llega al worker, no reclama nada y
        # vuelve sin hacer nada — el vector viejo se quedaría para siempre.
        # Antes de encolar, además, para que si el proceso muere en el medio la
        # fila quede reclamable por la próxima corrida.
        ProduccionEmbedding.objects.filter(pk=embedding.pk).update(
            estado=EstadoEmbedding.PENDING
        )
        generar_embedding.delay(embedding.produccion_id)
        estadisticas["desactualizados"] += 1
        if estadisticas["desactualizados"] >= restante:
            break

    estadisticas["reencolados"] += estadisticas["desactualizados"]
    logger.info("backfill_embeddings: %s", estadisticas)
    return estadisticas
