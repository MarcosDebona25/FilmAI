"""Tools que buscan títulos en TMDB y en nuestro catálogo.

Las llama: `ejecutar()` de `tools/__init__.py`, con el nombre que pide el modelo.
Usan: `catalogo/services/` (TMDB y `semantica.py`) y `publicar()` de `turno.py`.
"""

from django.conf import settings

from catalogo.services.fallback import servicio_localizado
from catalogo.services.semantica import buscar_semantico
from catalogo.services.tmdb import get_catalog_service
from chatbot.tools.turno import desde_produccion, publicar, titulo

# Sin esto, una nota alta puede ser un título con un solo voto.
_VOTOS_MINIMOS = 50

# TMDB nombra distinto algunos géneros de películas y de series.
_EQUIVALENTES = {
    "Action": ["Action & Adventure"],
    "Adventure": ["Action & Adventure"],
    "Action & Adventure": ["Action", "Adventure"],
    "Science Fiction": ["Sci-Fi & Fantasy"],
    "Fantasy": ["Sci-Fi & Fantasy"],
    "Sci-Fi & Fantasy": ["Science Fiction", "Fantasy"],
    "War": ["War & Politics"],
    "War & Politics": ["War"],
}


def _servicio(ctx):
    """El catálogo de TMDB en el idioma del turno, con respaldo en inglés."""
    return servicio_localizado(settings.IDIOMAS_TMDB[ctx.idioma], get_catalog_service)


def _servicio_en_ingles():
    """El catálogo en inglés: los géneros se comparan por su nombre en inglés."""
    return get_catalog_service(settings.IDIOMAS_TMDB[settings.IDIOMA_POR_DEFECTO])


def _tipos(tipo):
    """Qué tipos buscar: el pedido o, si no pidió ninguno, películas y series."""
    return [tipo] if tipo else ["movie", "tv"]


def _ampliar(generos):
    """Suma a cada género su equivalente, sin repetir: `Fantasy` trae `Sci-Fi & Fantasy`."""
    ampliados = list(generos or [])
    for genero in generos or []:
        ampliados += _EQUIVALENTES.get(genero, [])
    return list(dict.fromkeys(ampliados))


def _nombres_de_generos(servicio, tipo):
    """Un diccionario de id a nombre: TMDB manda ids y el modelo necesita nombres."""
    return {g["id"]: g["name"] for g in servicio.get_genres(tipo)["genres"]}


def _ids_de_generos(generos, tipo):
    """Convierte nombres de géneros en los ids de ese tipo, que es lo que pide TMDB.

    Un género que no existe en el tipo no aparece en el resultado.
    """
    por_nombre = {
        nombre: id_genero
        for id_genero, nombre in _nombres_de_generos(
            _servicio_en_ingles(), tipo
        ).items()
    }
    return [por_nombre[g] for g in _ampliar(generos) if g in por_nombre]


def _desde_tmdb(item, tipo, generos):
    """Un título a partir de un ítem de TMDB; las series usan otros campos."""
    fecha = item.get("release_date") or item.get("first_air_date") or ""
    nombres = [g["name"] for g in item.get("genres") or []]
    return titulo(
        id_tmdb=item["id"],
        tipo=tipo,
        nombre=item.get("title") or item.get("name") or "",
        anio=int(fecha[:4]) if fecha[:4].isdigit() else None,
        generos=nombres
        or [generos[i] for i in item.get("genre_ids") or [] if i in generos],
        duracion=item.get("runtime"),
        nota=item.get("vote_average"),
        sinopsis=item.get("overview"),
        poster=item.get("poster_path"),
    )


def _publicar_de_tmdb(ctx, servicio, por_tipo, orden=None, sacar_vistas=True):
    """Junta los resultados de películas y series y los entrega al modelo.

    `por_tipo` es `{"movie": [...], "tv": [...]}`. `orden` es el campo de TMDB por el
    que se mezclan; sin él, queda el orden en que llegaron.
    """
    generos = {tipo: _nombres_de_generos(servicio, tipo) for tipo in por_tipo}
    mezclados = [
        (item, tipo) for tipo, items in por_tipo.items() for item in items or []
    ]
    if orden:
        mezclados.sort(key=lambda par: par[0].get(orden) or 0, reverse=True)
    return publicar(
        ctx,
        [_desde_tmdb(item, tipo, generos[tipo]) for item, tipo in mezclados],
        sacar_vistas=sacar_vistas,
    )


def buscar_por_titulo(ctx, titulo, tipo=None, anio=None):
    """Tool: busca por nombre, en películas y series si no se pide un tipo.

    No saca las vistas: es una consulta directa. «Algo como Moon» necesita
    encontrar Moon aunque ya se haya visto.
    """
    servicio = _servicio(ctx)
    por_tipo = {
        t: servicio.search(titulo, t, anio=anio).get("results") for t in _tipos(tipo)
    }
    return {
        "resultados": _publicar_de_tmdb(
            ctx, servicio, por_tipo, "popularity", sacar_vistas=False
        )
    }


def descubrir(
    ctx,
    generos=None,
    tipo=None,
    anio_desde=None,
    anio_hasta=None,
    nota_minima=None,
    duracion_max=None,
):
    """Tool: busca por datos concretos, como género, año, nota o duración.

    Hace una búsqueda por tipo y las mezcla por popularidad.
    """
    servicio = _servicio(ctx)
    # TMDB casi no tiene la duración de las series: sin un tipo pedido, un
    # límite de duración significa películas.
    tipos = ["movie"] if duracion_max and not tipo else _tipos(tipo)
    por_tipo = {}
    for t in tipos:
        ids = _ids_de_generos(generos, t)
        if generos and not ids:
            # Ese género no existe en este tipo: buscar sin él traería cualquier cosa.
            continue
        por_tipo[t] = servicio.discover(
            t,
            genero="|".join(str(i) for i in ids) or None,
            anio_desde=anio_desde,
            anio_hasta=anio_hasta,
            min_rating=nota_minima,
            min_votos=_VOTOS_MINIMOS if nota_minima else None,
            duracion_max=duracion_max if t == "movie" else None,
        ).get("results")
    return {"resultados": _publicar_de_tmdb(ctx, servicio, por_tipo, "popularity")}


def similares_a(ctx, id_tmdb, tipo):
    """Tool: títulos parecidos a uno, con las recomendaciones de TMDB."""
    servicio = _servicio(ctx)
    # Sin ordenar: TMDB ya las trae de la más parecida a la menos parecida.
    items = servicio.get_recommendations(id_tmdb, tipo).get("results")
    return {"resultados": _publicar_de_tmdb(ctx, servicio, {tipo: items})}


def buscar_por_persona(ctx, nombre, rol=None):
    """Tool: lo más votado de un actor o director.

    Primero busca a la persona y después sus créditos. Toma el primer resultado de
    TMDB, y devuelve `persona` para que el modelo sepa a quién encontró. Un `rol`
    elige actuación o dirección; sin él, cuentan las dos. Si tuvo varios puestos en un
    título, `publicar()` saca los repetidos.
    """
    servicio = _servicio(ctx)
    personas = servicio.search_person(nombre).get("results") or []
    if not personas:
        return {"persona": None, "resultados": []}

    creditos = servicio.get_person_credits(personas[0]["id"])
    items = []
    if rol != "director":
        items += creditos.get("cast") or []
    if rol != "actor":
        items += [c for c in creditos.get("crew") or [] if c.get("job") == "Director"]

    por_tipo = {"movie": [], "tv": []}
    for item in items:
        if item.get("media_type") in por_tipo:
            por_tipo[item["media_type"]].append(item)
    return {
        "persona": personas[0].get("name"),
        "resultados": _publicar_de_tmdb(ctx, servicio, por_tipo, "vote_count"),
    }


def detalle(ctx, id_tmdb, tipo):
    """Tool: los datos de un título, con la duración, que los listados no traen."""
    servicio = _servicio(ctx)
    metodo = servicio.get_movie_detail if tipo == "movie" else servicio.get_tv_detail
    # No saca las vistas: el usuario puede preguntar por algo que ya vio.
    return publicar(ctx, [_desde_tmdb(metodo(id_tmdb), tipo, {})], sacar_vistas=False)[
        0
    ]


def semantico(
    ctx,
    consulta,
    generos=None,
    tipo=None,
    anio_desde=None,
    anio_hasta=None,
    nota_minima=None,
    duracion_max=None,
):
    """Tool: busca por significado en el catálogo local (B-06).

    Si Ollama falla, `buscar_semantico` lanza un error y `ejecutar()` lo convierte en
    `tool_failed`. Saca las vistas pasándolas en `excluir`.
    """
    producciones = buscar_semantico(
        consulta,
        generos=_ampliar(generos),
        tipo=tipo,
        anio_desde=anio_desde,
        anio_hasta=anio_hasta,
        nota_minima=nota_minima,
        duracion_max=duracion_max,
        excluir=ctx.vistas,
    )
    return {
        "resultados": publicar(
            ctx, [desde_produccion(p, ctx.idioma) for p in producciones]
        )
    }
