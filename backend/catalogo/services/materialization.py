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
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from catalogo.exceptions import TMDBError, TMDBNotFound
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

# Un título de un listado se encola como mucho una vez en esta ventana. El
# Home lo abren muchas personas y cada visita trae los mismos 20: sin esto,
# con TMDB caído la cola se llenaría de tareas repetidas que fallan.
_VENTANA_ENCOLADO_SEGUNDOS = 10 * 60


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
    produccion, creada = _obtener_o_crear(id_tmdb, tipo)

    if forzar or _necesita_enriquecimiento(produccion):
        try:
            _enriquecer(produccion, id_tmdb, tipo_tmdb)
        except TMDBNotFound:
            # También el cascarón que dejó un fallo transitorio anterior: sin
            # título y sin enriquecer, no puede tener calificaciones ni listas.
            if creada or not produccion.titulo:
                _descartar_cascaron(produccion)
            raise

    _encolar_embedding(produccion)
    return produccion


def _descartar_cascaron(produccion):
    """Borra la fila vacía de un id que TMDB no conoce (auditoría F7).

    Sin esto, calificar o agregar a una lista un id inexistente respondía 404
    (Not Found) pero dejaba una fila vacía por cada id probado. Se borra la
    fila que creó esta misma llamada o un cascarón sin título que dejó un fallo
    anterior; nunca una fila con datos, que puede tener calificaciones y listas
    colgando (CASCADE). El filtro por `fecha_enriquecimiento` cubre la carrera
    con otro pedido que sí la haya enriquecido mientras tanto. Ante un fallo
    transitorio (TMDB caído) la fila se conserva: el id puede existir y la
    próxima visita la vuelve a encolar.
    """
    # `titulo=""` es una defensa explícita: hoy el título y la fecha se guardan
    # en el mismo save(), pero el borrado no tiene que depender de eso.
    ProduccionAudiovisual.objects.filter(
        pk=produccion.pk, fecha_enriquecimiento__isnull=True, titulo=""
    ).delete()


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


def materializar_listado_en_segundo_plano(items, tipo_tmdb=None):
    """Encola la materialización de lo que muestra un listado (C-04a, 16/10/2026).

    Docs 02 y 03: lo que exponen tendencias, estrenos, discover y Buscar queda
    en nuestro catálogo, no solo lo que se abre en la ficha. Así crece el
    espacio de búsqueda del chatbot sin esperar a la sync nocturna.

    `tipo_tmdb` es el tipo del listado; en los que mezclan (tendencias de
    «Todo», Buscar con «Todo») lo dice cada ítem en `media_type`, y las
    personas se descartan. Una sola consulta separa lo que ya está fresco; lo
    demás va a Celery, cada título como mucho una vez cada 10 minutos. Las
    llamadas a TMDB de la tarea pasan por la caché de Redis: repetirla cuesta
    poco.
    """
    candidatos = set()
    for item in items or []:
        tipo = item.get("media_type") or tipo_tmdb
        id_tmdb = item.get("id")
        if tipo in ("movie", "tv") and isinstance(id_tmdb, int):
            candidatos.add((id_tmdb, tipo))
    if not candidatos:
        return

    frescas = set(
        ProduccionAudiovisual.objects.filter(
            id_tmdb__in={id_tmdb for id_tmdb, _ in candidatos},
            fecha_enriquecimiento__gte=_umbral_de_frescura(),
        ).values_list("id_tmdb", "tipo")
    )
    for id_tmdb, tipo in sorted(candidatos):
        if (id_tmdb, tmdb_a_dominio(tipo)) in frescas:
            continue
        marca = f"materializar:{tipo}:{id_tmdb}"
        if not cache.add(marca, 1, timeout=_VENTANA_ENCOLADO_SEGUNDOS):
            continue
        try:
            materializar_produccion.delay(id_tmdb, tipo)
        except Exception:
            # Si no se pudo encolar, la marca no puede bloquear el próximo
            # intento durante 10 minutos: se borra y el error sigue su camino.
            cache.delete(marca)
            raise


def _buscar_produccion(id_tmdb, tipo):
    """Único lugar donde vive la consulta por la clave natural (id_tmdb, tipo)."""
    return ProduccionAudiovisual.objects.filter(id_tmdb=id_tmdb, tipo=tipo).first()


def _obtener_o_crear(id_tmdb, tipo, *, reintento=False):
    """`(fila, creada)`: la fila de la producción, creándola vacía si no existe.

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
        return existente, False

    try:
        with transaction.atomic():
            nueva = ProduccionAudiovisual.objects.create(
                id_tmdb=id_tmdb, tipo=tipo, titulo=""
            )
            return nueva, True
    except IntegrityError:
        ganadora = _buscar_produccion(id_tmdb, tipo)
        if ganadora is None:
            if not reintento:
                # La ganadora pudo borrarse entre el choque y esta consulta: otro
                # pedido la creó para un id que TMDB no conoce y la descartó
                # (F7). Un solo reintento cubre esa carrera.
                return _obtener_o_crear(id_tmdb, tipo, reintento=True)
            # Dos choques seguidos sin fila: el error no venía de la carrera.
            # Disfrazarlo de "ya existía" escondería un bug real.
            raise
        logger.info("materializar: otro request creó (%s, %s) primero", id_tmdb, tipo)
        return ganadora, False


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

    valores = _recortar(_mapear(detalle, credits, keywords, tipo_tmdb))
    for campo, valor in valores.items():
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
                "poster": (detalle.get("poster_path") or "")[:250],
            },
        )


def _recortar(valores):
    """Recorta cada texto de TMDB al `max_length` de su columna.

    Los límites se leen del modelo, no se repiten acá: si cambia un
    `max_length`, esto lo sigue solo. Sin recorte, un título o un nombre más
    largo que la columna haría fallar el `save()` con `DataError` y se perdería
    todo el enriquecimiento de la producción.
    """
    recortados = dict(valores)
    for campo, valor in valores.items():
        columna = ProduccionAudiovisual._meta.get_field(campo)
        if isinstance(valor, str) and columna.max_length:
            recortados[campo] = valor[: columna.max_length]
        elif isinstance(valor, list) and getattr(
            getattr(columna, "base_field", None), "max_length", None
        ):
            tope = columna.base_field.max_length
            recortados[campo] = [x[:tope] if isinstance(x, str) else x for x in valor]
    return recortados


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
