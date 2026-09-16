"""Materialización on-demand del catálogo (C-04a).

Cuando alguien abre el detalle de una producción, además de devolverle la
respuesta de TMDB la guardamos en nuestra base y encolamos su embedding
(CU-021: toda producción que se abre queda materializada). Es la única puerta
de escritura de `ProduccionAudiovisual` en el código actual.

`materializar()` lanza si algo sale mal, a propósito: la política de fallo la
decide quien llama. Las vistas de detalle la envuelven para que un problema
acá nunca rompa el passthrough de TMDB (contrato de C-03), pero el backfill
masivo de C-04b sí va a querer enterarse de los errores.
"""

import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from catalogo.models import ProduccionAudiovisual, ProduccionEmbedding
from catalogo.services.adapter import tmdb_a_dominio
from catalogo.services.tmdb import get_catalog_service
from catalogo.tasks import generar_embedding

logger = logging.getLogger(__name__)

# TMDB devuelve el reparto ordenado por `order` (el billing de los créditos):
# los diez primeros son los que un usuario reconoce y los que aportan señal
# real al embedding. El resto es ruido que además engordaría el texto canónico.
_MAX_REPARTO = 10

# Red de seguridad, NO el mecanismo principal de refresco: lo que cambió de
# verdad lo dice la lista de cambios de TMDB (C-04b, fase 2). Esta ventana solo
# garantiza que nada quede sin refrescar para siempre si esa lista se pierde.
# Es una estimación de bajo riesgo: equivocarse cuesta unos refrescos de más.
_DIAS_RED_DE_SEGURIDAD = 90


def materializar(id_tmdb, tipo_tmdb):
    """Garantiza que la producción exista en la base con su embedding encolado.

    Recibe el vocabulario de TMDB (`"movie"` / `"tv"`) porque es lo que traen
    las vistas; la traducción al dominio ocurre en la primera línea.

    Es idempotente: llamarla mil veces sobre la misma producción deja una sola
    fila, un solo embedding y una sola tarea encolada.
    """
    tipo = tmdb_a_dominio(tipo_tmdb)
    produccion = _obtener_o_crear(id_tmdb, tipo)

    if _necesita_enriquecimiento(produccion):
        _enriquecer(produccion, id_tmdb, tipo_tmdb)

    _encolar_embedding(produccion)
    return produccion


def _buscar_produccion(id_tmdb, tipo):
    """Único lugar donde vive la consulta por la clave natural (id_tmdb, tipo)."""
    return ProduccionAudiovisual.objects.filter(id_tmdb=id_tmdb, tipo=tipo).first()


def _obtener_o_crear(id_tmdb, tipo):
    """Devuelve la fila de la producción, creándola vacía si todavía no existe.

    Dos requests simultáneos sobre la misma producción pueden ver ambos que no
    existe y ambos intentar el INSERT: `uq_produccion_tmdb_tipo` deja pasar uno
    solo y el otro recibe `IntegrityError`. Ese perdedor no debe fallar, sino
    usar la fila del ganador.

    El INSERT va dentro de `transaction.atomic()` porque en PostgreSQL un error
    aborta la transacción completa: sin ese savepoint, la consulta de rescate
    también fallaría ("current transaction is aborted").
    """
    existente = _buscar_produccion(id_tmdb, tipo)
    if existente is not None:
        return existente

    try:
        with transaction.atomic():
            return ProduccionAudiovisual.objects.create(
                id_tmdb=id_tmdb, tipo=tipo, titulo=""
            )
    except IntegrityError:
        ganadora = _buscar_produccion(id_tmdb, tipo)
        if ganadora is None:
            # La fila sigue sin aparecer: el error no venía de la carrera.
            # Disfrazarlo de "ya existía" escondería un bug real.
            raise
        logger.info("materializar: otro request creó (%s, %s) primero", id_tmdb, tipo)
        return ganadora


def _necesita_enriquecimiento(produccion):
    """Decide si hay que traer el detalle de TMDB para esta fila.

    Reemplaza el criterio de C-04a (`not titulo`), que dejó de servir cuando
    C-04b empezó a crear filas desde listados: un ítem de listado trae título
    pero no géneros, reparto, créditos ni keywords, y con el criterio viejo
    contaba como completo para siempre. Ahora el hecho se registra en vez de
    deducirse: `fecha_enriquecimiento` dice cuándo se trajo el detalle.

    Acá NO se decide si la fila quedó desactualizada. Eso lo responde TMDB por
    su lista de cambios (`/movie/changes`, `/tv/changes`) y la sync lo fuerza
    con `forzar=True`. La ventana de abajo es solo una red de seguridad por si
    esa lista se pierde —la sync no corrió una noche, la API falló—, no el
    mecanismo principal.
    """
    if produccion.fecha_enriquecimiento is None:
        return True
    return timezone.now() - produccion.fecha_enriquecimiento > timedelta(
        days=_DIAS_RED_DE_SEGURIDAD
    )


def _enriquecer(produccion, id_tmdb, tipo_tmdb):
    """Trae detalle, créditos y keywords de TMDB y los vuelca en la fila.

    Las tres llamadas salen FUERA de cualquier transacción (decisión
    25/08/2026): son de red, pueden tardar segundos y no deben mantener tomada
    una conexión de Postgres ni bloquear a otro request. Las tres están
    cacheadas en Redis por 24 h, así que solo la primera visita las paga.
    """
    servicio = get_catalog_service()
    if tipo_tmdb == "movie":
        detalle = servicio.get_movie_detail(id_tmdb)
    else:
        detalle = servicio.get_tv_detail(id_tmdb)
    credits = servicio.get_credits(id_tmdb, tipo_tmdb)
    keywords = servicio.get_keywords(id_tmdb, tipo_tmdb)

    for campo, valor in _mapear(detalle, credits, keywords, tipo_tmdb).items():
        setattr(produccion, campo, valor)
    # En el mismo save() que los datos: si la escritura falla, tampoco queda
    # anotado que se enriqueció.
    produccion.fecha_enriquecimiento = timezone.now()
    produccion.save()


def _mapear(detalle, credits, keywords, tipo_tmdb):
    """Traduce las tres respuestas de TMDB a los campos del modelo.

    Función pura: ni base de datos ni red. El mapeo campo por campo está
    documentado en la tabla "TMDB Enrichment Mapping" del design.md.

    Todos los accesos usan `.get()` y `or`: TMDB omite claves enteras según el
    título (una película sin estrenar no trae `runtime`) y devuelve `null` o
    `""` indistintamente para lo que falta.
    """
    es_pelicula = tipo_tmdb == "movie"
    fecha = (
        detalle.get("release_date") if es_pelicula else detalle.get("first_air_date")
    )
    return {
        # Una película tiene `title`; una serie, `name`.
        "titulo": (detalle.get("title") if es_pelicula else detalle.get("name")) or "",
        # Ruta cruda de TMDB, igual que el passthrough de C-03: la URL del CDN
        # la arma el frontend.
        "poster": detalle.get("poster_path") or "",
        "sinopsis": detalle.get("overview") or "",
        # "" no es una fecha válida para un DateField: tiene que ser NULL.
        "fecha_lanzamiento": fecha or None,
        "reparto": [
            persona["name"]
            for persona in (credits.get("cast") or [])[:_MAX_REPARTO]
            if persona.get("name")
        ],
        "directores": _directores(detalle, credits, es_pelicula),
        "estatus": detalle.get("status") or "",
        "generos": [
            genero["name"]
            for genero in (detalle.get("genres") or [])
            if genero.get("name")
        ],
        "keywords": _extraer_keywords(keywords, tipo_tmdb),
        "calificacion_promedio": detalle.get("vote_average"),
        "cantidad_temporadas": (
            None if es_pelicula else detalle.get("number_of_seasons")
        ),
        "cantidad_episodios": (
            None if es_pelicula else detalle.get("number_of_episodes")
        ),
        "duracion": (
            detalle.get("runtime") if es_pelicula else _duracion_de_episodio(detalle)
        ),
    }


def _directores(detalle, credits, es_pelicula):
    """Quién firma la producción, que en TV no es lo mismo que en cine.

    En una película el director está en el crew con `job == "Director"`. En una
    serie ese rol NO existe a nivel serie: los directores son por episodio, así
    que TMDB no los incluye en `/tv/{id}/credits` y en su lugar publica
    `created_by`, el o los creadores. Verificado contra la API real
    (15/09/2026): el crew de Breaking Bad trae Executive Producer, Casting,
    Costume Design y demás, ningún Director.

    Sin esta distinción, el texto canónico de TODA serie llevaría la línea
    `Directors:` vacía y la búsqueda semántica no podría encontrarlas por su
    autor — que para una serie es justamente el dato que un usuario recuerda.
    """
    del_crew = [
        persona["name"]
        for persona in (credits.get("crew") or [])
        if persona.get("job") == "Director" and persona.get("name")
    ]
    if es_pelicula:
        return del_crew

    creadores = [
        persona["name"]
        for persona in (detalle.get("created_by") or [])
        if persona.get("name")
    ]
    # Algunas miniseries y documentales sí traen un Director en el crew: si no
    # hay creadores declarados, es mejor eso que nada.
    return creadores or del_crew


def _extraer_keywords(payload, tipo_tmdb):
    """Normaliza una rareza de TMDB: la misma lista bajo dos claves distintas.

    `/movie/{id}/keywords` la devuelve en `keywords` y `/tv/{id}/keywords` en
    `results`, por razones históricas de la API. Aislarlo acá evita que la
    diferencia se filtre al resto del enriquecimiento.
    """
    clave = "keywords" if tipo_tmdb == "movie" else "results"
    return [
        keyword["name"] for keyword in (payload.get(clave) or []) if keyword.get("name")
    ]


def _duracion_de_episodio(detalle):
    """Una serie no tiene `runtime`: TMDB da una lista de duraciones típicas."""
    duraciones = detalle.get("episode_run_time") or []
    return duraciones[0] if duraciones else None


def _encolar_embedding(produccion):
    """Crea el embedding en `pending` y encola la tarea, una sola vez.

    `get_or_create` resuelve solo la carrera de dos requests creando el
    embedding a la vez: internamente hace el mismo INSERT-con-savepoint y
    reintenta el `get` si choca contra el UNIQUE del `OneToOneField`.

    Solo se encola cuando la fila se acaba de crear. Reencolar en cada visita
    llenaría la cola de trabajo repetido; refrescar embeddings viejos o en
    `failed` es responsabilidad del backfill de C-04b.

    El encolado va dentro de `transaction.on_commit()`: `generar_embedding`
    corre en otro proceso, con otra conexión, y si el mensaje saliera antes del
    COMMIT el worker buscaría una fila que todavía no es visible, no la
    encontraría y se iría sin generar nada. Sin transacción abierta el callback
    se ejecuta al instante, así que hoy el comportamiento es idéntico; protege
    el día que algo envuelva la materialización en un `atomic()` —la sync por
    lotes de C-04b es candidata—. Además, si esa transacción termina en
    rollback, no se encola nada: la fila nunca existió.
    """
    _, creado = ProduccionEmbedding.objects.get_or_create(produccion=produccion)
    if creado:
        transaction.on_commit(lambda: generar_embedding.delay(produccion.id))
