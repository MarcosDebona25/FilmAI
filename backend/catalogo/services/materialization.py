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

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from catalogo.exceptions import TMDBError
from catalogo.models import (
    ProduccionAudiovisual,
    ProduccionEmbedding,
    ProduccionTraduccion,
)
from catalogo.services.adapter import tmdb_a_dominio
from catalogo.services.tmdb import get_catalog_service
from catalogo.tasks import generar_embedding, materializar_produccion

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


def materializar(id_tmdb, tipo_tmdb, forzar=False):
    """Garantiza que la producción exista en la base con su embedding encolado.

    Recibe el vocabulario de TMDB (`"movie"` / `"tv"`) porque es lo que traen
    las vistas; la traducción al dominio ocurre en la primera línea.

    Es idempotente: llamarla mil veces sobre la misma producción deja una sola
    fila, un solo embedding y una sola tarea encolada.

    `forzar=True` vuelve a pedir el detalle a TMDB aunque la fila cuente como
    completa. Es la puerta por la que la sync diaria (C-04b) refresca lo que
    TMDB reporta como cambiado, sin abrir un segundo camino de escritura ni
    tener que borrar `fecha_enriquecimiento` para provocar el refresco.
    """
    tipo = tmdb_a_dominio(tipo_tmdb)
    produccion = _obtener_o_crear(id_tmdb, tipo)

    if forzar or _necesita_enriquecimiento(produccion):
        _enriquecer(produccion, id_tmdb, tipo_tmdb)

    _encolar_embedding(produccion)
    return produccion


def materializar_en_segundo_plano(id_tmdb, tipo_tmdb):
    """Variante de las vistas de detalle: quien abre la ficha no espera a TMDB.

    Si la fila ya está completa no hay nada caro que hacer y no se encola nada:
    encolar en cada visita llenaría la cola de trabajo repetido (el mismo
    criterio que `_encolar_embedding`). Si no existe o le falta el detalle —la
    primera visita, o la red de seguridad de 90 días—, `materializar()` corre
    en el worker de Celery.

    Medido el 14/10/2026: la primera visita tardaba entre 1 y 1,6 s en
    responder. ~0,5 s eran la llamada a TMDB de la propia vista y el resto, el
    enriquecimiento (detalle canónico, créditos, keywords y traducción).
    Calificar o agregar a una lista no dependen de esto: materializan por su
    cuenta antes de escribir.
    """
    produccion = _buscar_produccion(id_tmdb, tmdb_a_dominio(tipo_tmdb))
    if produccion is not None and not _necesita_enriquecimiento(produccion):
        return
    materializar_produccion.delay(id_tmdb, tipo_tmdb)


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
    return produccion.fecha_enriquecimiento < _umbral_de_frescura()


def _umbral_de_frescura():
    """Instante antes del cual una fila enriquecida cuenta como vencida."""
    return timezone.now() - timedelta(days=_DIAS_RED_DE_SEGURIDAD)


def claves_frescas():
    """`{(id_tmdb, tipo)}` de las filas que `materializar()` no volvería a enriquecer.

    Para quien recorre miles de candidatos —el seed de C-04c— es la diferencia
    entre una consulta al arrancar y una por ítem, y evita invocar
    `materializar()` solo para descubrir que no había nada que hacer. Usa el
    mismo umbral que `_necesita_enriquecimiento`, a propósito: si las dos
    definiciones divergieran, el seed saltearía filas que la materialización
    sí refrescaría, o al revés. Las filas con `fecha_enriquecimiento` NULL
    quedan afuera solas (el `>=` no matchea NULL), que es lo correcto: nunca
    se enriquecieron y hay que mandarlas.
    """
    return set(
        ProduccionAudiovisual.objects.filter(
            fecha_enriquecimiento__gte=_umbral_de_frescura()
        ).values_list("id_tmdb", "tipo")
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
    guardar_traducciones(produccion, id_tmdb, tipo_tmdb)
    # Los valores que vinieron de TMDB son los del JSON, no los de la columna:
    # `fecha_lanzamiento` queda como el string "1999-10-15" hasta que alguien
    # relee la fila. Quien serialice lo que devolvemos se lleva ese string —le
    # pasaba al POST de ítems de L-01, que moría con `'str' object has no
    # attribute 'year'` al agregar a una lista una producción que no estuviera
    # ya en la base. Una consulta más, al lado de las tres llamadas HTTP que
    # esta función acaba de hacer, y quien nos llama recibe tipos de verdad.
    produccion.refresh_from_db()


def idiomas_traducidos():
    """Idiomas de aplicación que se guardan aparte del canónico (inglés)."""
    return [
        idioma
        for idioma in settings.IDIOMAS_SOPORTADOS
        if idioma != settings.IDIOMA_POR_DEFECTO
    ]


def guardar_traducciones(produccion, id_tmdb, tipo_tmdb):
    """Guarda título, sinopsis y póster en cada idioma no canónico.

    Un fallo acá no invalida el enriquecimiento canónico, que ya quedó
    guardado: se registra y sigue. `rellenar_traducciones` y la sincronización
    nocturna completan lo que haya quedado pendiente.
    """
    es_pelicula = tipo_tmdb == "movie"
    for idioma in idiomas_traducidos():
        try:
            servicio = get_catalog_service(settings.IDIOMAS_TMDB[idioma])
            detalle = (
                servicio.get_movie_detail(id_tmdb)
                if es_pelicula
                else servicio.get_tv_detail(id_tmdb)
            )
        except TMDBError:
            logger.exception(
                "No se pudo traer la traducción %s de (%s, %s)",
                idioma,
                id_tmdb,
                tipo_tmdb,
            )
            continue
        titulo = (detalle.get("title") if es_pelicula else detalle.get("name")) or ""
        ProduccionTraduccion.objects.update_or_create(
            produccion=produccion,
            idioma=idioma,
            defaults={
                "titulo": titulo[:100],
                "sinopsis": (detalle.get("overview") or "")[:2000],
                "poster": detalle.get("poster_path") or "",
            },
        )


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
        "generos_ids": [
            genero["id"]
            for genero in (detalle.get("genres") or [])
            if isinstance(genero.get("id"), int)
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
