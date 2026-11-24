"""Buscar (C-06): combina `discover` y `search` de TMDB según lo pedido.

TMDB no tiene una consulta que haga todo (verificado el 14/10/2026): su
búsqueda por nombre acepta el año pero ignora género y nota, y `discover`
acepta todos los filtros pero no texto. Este módulo elige, por cada tipo, la
llamada que corresponde, y en «Todo» alterna películas y series.

| Texto | Por tipo                                                         |
| ----- | ---------------------------------------------------------------- |
| no    | `discover`, por popularidad; «Todo» alterna películas y series   |
| sí    | los primeros 100 de `search`, filtrados y ordenados por puntaje  |
| persona | su filmografía (`combined_credits`), filtrada en memoria       |

El orden (`orden`, 24/11/2026) es una opción más: `popular` (el de siempre),
`fecha-desc`, `fecha-asc`, `nota-desc`, `nota-asc` y `votos-desc`. Sin texto y
con un solo tipo lo hace TMDB (`sort_by` de `discover`). Con texto o persona se
ordena en memoria. «Todo» sin texto y con un orden distinto de `popular` no
puede alternar páginas de dos listas ordenadas por separado: lee las primeras
100 de cada tipo, las junta y las ordena (hasta 200 resultados).

Con texto, el orden de TMDB es de relevancia y deja arriba títulos con 0 votos
(«the office»: tres películas sin votos antes que la serie con 5579). Se ordena
por el mayor entre los votos y la popularidad por 100: arriba lo consagrado o lo
muy esperado, al fondo lo desconocido (pedido del usuario, 14/10/2026).

El diseño completo está en `openspec/changes/search-catalogo/design.md`.
"""

import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from math import ceil

from django.utils import timezone

from catalogo.exceptions import PersonaNoEncontrada, TMDBNotFound
from catalogo.presupuesto import con_contexto

POR_PAGINA = 20
# «Los primeros 100» (decisión del usuario, 14/10/2026): 5 páginas de TMDB.
PAGINAS_VENTANA = 5
# TMDB rechaza pedir una página mayor a 500 aunque informe más.
MAX_PAGINAS = 500
# Escala de la popularidad de TMDB frente a los votos en el orden con texto: una
# popularidad de 100 (un estreno con mucho ruido) compite con 10 000 votos.
# Con 100, Avengers: Doomsday (0 votos, popularidad 108) queda 5.º en
# «avengers» y Dune: Part Three, 5.º en «dune» (14/10/2026).
PESO_POPULARIDAD = 100
# Votos mínimos sin texto y para filtrar por nota: sin él, «Menos de 5» se
# llena de títulos sin votos. Mismo umbral que las series del año del Home (C-05).
MIN_VOTOS_NOTA = 50
# Al ordenar por nota el mínimo sube a 200: con 50, «Mejor calificados» se
# llena de títulos de nicho con 9,5 de nota y 60 votos (las listas «Top rated»
# de TMDB usan un umbral alto). Lo que todavía no estrena sigue sin mínimo.
MIN_VOTOS_ORDEN_NOTA = 200

# Corte de relevancia (Gonza, 13/11/2026): con texto, un título se muestra si
# tiene al menos 5 votos o al menos 5 de popularidad. Medido el 13/11/2026:
# «chihiro» pasa de 13 títulos a 3 y «the office» de 158 a 35, y la popularidad
# conserva los estrenos sin votos (Dune: Part Three, The Batman: Part II). Son
# constantes a propósito: con las dos en 0 no se oculta nada (el rollback).
MIN_VOTOS_RELEVANTE = 5
MIN_POPULARIDAD_RELEVANTE = 5
# Los campos con el nombre de un título: el traducido y el original.
CAMPOS_TITULO = ("title", "name", "original_title", "original_name")

# `nota` → (mínimo, máximo) de `vote_average`. «Menos de 5» es un techo.
NOTAS = {
    "9+": (9, None),
    "8+": (8, None),
    "7+": (7, None),
    "6+": (6, None),
    "5+": (5, None),
    "m5": (None, 4.99),
}

# `orden` → `sort_by` de `discover` por tipo. Fecha usa un campo distinto en
# películas y en series (como `_DISCOVER_DATE_PARAM` del cliente).
ORDENES = {
    "popular": {"movie": "popularity.desc", "tv": "popularity.desc"},
    "fecha-desc": {
        "movie": "primary_release_date.desc",
        "tv": "first_air_date.desc",
    },
    "fecha-asc": {"movie": "primary_release_date.asc", "tv": "first_air_date.asc"},
    "nota-desc": {"movie": "vote_average.desc", "tv": "vote_average.desc"},
    "nota-asc": {"movie": "vote_average.asc", "tv": "vote_average.asc"},
    "votos-desc": {"movie": "vote_count.desc", "tv": "vote_count.desc"},
}
ORDEN_POR_DEFECTO = "popular"
ORDENES_POR_NOTA = ("nota-desc", "nota-asc")

# Géneros de TMDB (listas verificadas el 14/10/2026). Películas y series
# comparten 8 ids; estos de películas tienen su par en series con otro id.
GENERO_EN_SERIES = {28: 10759, 12: 10759, 878: 10765, 14: 10765, 10752: 10768}
# Solo de películas, sin par en series: en «Todo» dejan vacío el lado series.
SOLO_PELICULAS = {27, 36, 53, 10402, 10749, 10770}
# Solo de series (los pares de arriba y los que no tienen par en películas).
SOLO_SERIES = {10759, 10762, 10763, 10764, 10765, 10766, 10767, 10768}
# Programas diarios que dominan la popularidad de `discover/tv` (Barbara
# Karlich - Talk, Watch What Happens Live…; 14/10/2026). La grilla sin texto ni
# género los deja afuera; elegirlos como género los trae.
NEWS_Y_TALK = "10763,10767"
# Los de series sin par en películas: se suman a la lista de «Todo».
SERIES_SIN_PAR = [10762, 10763, 10764, 10766, 10767]


def tiene_poster(item):
    """Si el título tiene póster: lo único que lo deja salir en el descubrimiento.

    Decisión del 21/11/2026: sin póster, la tarjeta se ve rota. Esos títulos
    siguen en la base y se encuentran por nombre (búsqueda con texto) y por su
    ficha; solo quedan fuera de las listas que no pidió nadie (Home, Buscar sin
    texto, recomendados). `None` y `""` cuentan como sin póster.
    """
    # Una persona (Tendencias en «all») no tiene póster, tiene foto: no es un
    # título y no se toca.
    return item.get("media_type") == "person" or bool(item.get("poster_path"))


def con_poster(datos):
    """Una copia del listado de TMDB sin los títulos sin póster.

    No toca `total_pages` ni `total_results` (TMDB no dice cuántos de los demás
    tampoco tienen) y no rellena: una página puede traer 1 o 2 ítems menos de
    los 20 y se pide la siguiente igual. Es una copia porque el listado puede
    ser el mismo objeto que guarda la caché.
    """
    return {
        **datos,
        "results": [i for i in datos.get("results") or [] if tiene_poster(i)],
    }


_VACIO = {"page": 1, "total_pages": 0, "total_results": 0, "results": []}


def explorar(
    servicio,
    *,
    q=None,
    tipo="all",
    genero=None,
    anio=None,
    nota=None,
    page=1,
    a_estrenar=False,
    decada=None,
    persona=None,
    rol=None,
    orden=ORDEN_POR_DEFECTO,
):
    """Una página de Buscar, con la forma de los listados de TMDB.

    Cada ítem lleva `media_type` aunque se pida un solo tipo, para que el
    frontend los normalice igual que las filas del Home.
    """
    tipos = ("movie", "tv") if tipo == "all" else (tipo,)
    # «A estrenar», una década o un año: es la misma opción del selector, así
    # que el período se resuelve acá a un rango de fechas.
    if a_estrenar:
        desde, hasta = (hoy() + timedelta(days=1)).isoformat(), None
    elif decada is not None:
        desde, hasta = f"{decada}-01-01", f"{decada + 9}-12-31"
    else:
        desde = hasta = None
    # Lo anunciado todavía no tiene votos (2027: 946 películas en TMDB y
    # ninguna con 50, 14/10/2026): sin nota, va sin mínimo. Una nota sin votos
    # no dice nada, así que con nota el mínimo se mantiene.
    futuro = a_estrenar or (anio is not None and anio > anio_actual())
    # «Más nuevos» sin un período futuro elegido: arriba lo ya estrenado, no lo
    # anunciado para 2030. Con un rango de fechas elegido ya hay tope.
    tope = None
    if orden == "fecha-desc" and not futuro and hasta is None:
        tope = hoy().isoformat()
    filtros = {
        "q": q,
        "genero": genero,
        "anio": None if desde else anio,
        "nota": nota,
        "page": page,
        "desde": desde,
        "hasta": hasta,
        "sin_minimo": futuro and nota is None,
        "orden": orden,
    }
    if persona is not None:
        # `rol` sin persona no hace nada: es una opción de este filtro.
        return _con_persona(
            servicio,
            tipos,
            persona,
            rol,
            genero=genero,
            tope=tope,
            **_sin_genero(filtros),
        )
    if q:
        return _con_texto(
            servicio, tipos, genero=genero, tope=tope, **_sin_genero(filtros)
        )
    del filtros["q"]
    # Con TMDB ordenando, el tope es un filtro de `discover` más.
    filtros["hasta"] = tope or filtros["hasta"]
    if len(tipos) == 2 and orden != ORDEN_POR_DEFECTO:
        return _ventana_discover(
            servicio, tipos, genero=genero, tope=tope, **_sin_genero(filtros)
        )
    if len(tipos) == 1:
        lados = [_lado(servicio, tipos[0], genero=genero, **_sin_genero(filtros))]
    else:
        # Los dos tipos a la vez: en la ventana cada uno pide hasta 5 páginas.
        with ThreadPoolExecutor(max_workers=2) as hilos:
            lados = list(
                hilos.map(
                    con_contexto(
                        lambda t: _lado(
                            servicio,
                            t,
                            genero=_genero_para(t, genero),
                            **_sin_genero(filtros),
                        )
                    ),
                    tipos,
                )
            )
    return {
        "page": page,
        "total_pages": min(max(lado["total_pages"] for lado in lados), MAX_PAGINAS),
        "total_results": sum(lado["total_results"] for lado in lados),
        "results": _alternar(*(lado["results"] for lado in lados)),
    }


def normalizar(texto):
    """Minúsculas, sin tildes y con los espacios colapsados: «CHIHIRÓ » → «chihiro».

    `NFKD` separa cada letra de su tilde («ó» pasa a «o» más un acento suelto) y
    se descartan los acentos sueltos (categoría `Mn`, de «marca sin espacio»).
    En Java sería `Normalizer.normalize(texto, Form.NFD)` y un `replaceAll`.
    """
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().split())


def es_relevante(item, q=None):
    """Si un título se muestra en una búsqueda con texto (o con persona).

    Pasa con 5 votos o con 5 de popularidad. Excepción: el título que se llama
    exactamente como el texto (traducido u original, sin tildes ni mayúsculas):
    quien escribe el nombre completo quiere ese título, tenga los votos que
    tenga. `video`, la sinopsis y `adult` no cuentan como señal (Gonza, 13/11/2026).
    """
    if (item.get("vote_count") or 0) >= MIN_VOTOS_RELEVANTE:
        return True
    if (item.get("popularity") or 0) >= MIN_POPULARIDAD_RELEVANTE:
        return True
    if not q:
        return False
    buscado = normalizar(q)
    return any(normalizar(item.get(campo)) == buscado for campo in CAMPOS_TITULO)


def con_corte(items, q=None):
    """Los relevantes; si no pasa ninguno, todos (mejor eso que una página vacía)."""
    relevantes = [item for item in items if es_relevante(item, q)]
    return relevantes or items


def generos_de_todo(peliculas, series):
    """Lista de géneros de «Todo»: los de películas y los de series sin par."""
    por_id = {genero["id"]: genero for genero in series}
    return list(peliculas) + [por_id[i] for i in SERIES_SIN_PAR if i in por_id]


def hoy():
    """En una función para que los tests fijen la fecha (zona de Argentina)."""
    return timezone.localdate()


def anio_actual():
    return hoy().year


def _sin_genero(filtros):
    return {clave: valor for clave, valor in filtros.items() if clave != "genero"}


def _genero_para(tipo, genero):
    """El id del género para un tipo en «Todo»; `False` si ese lado no aplica."""
    if genero is None:
        return None
    if tipo == "movie":
        return False if genero in SOLO_SERIES else genero
    if genero in SOLO_PELICULAS:
        return False
    return GENERO_EN_SERIES.get(genero, genero)


def _con_texto(
    servicio, tipos, *, q, genero, anio, nota, page, desde, hasta, orden, tope, **_
):
    """Con texto: los primeros 100 de cada tipo, juntos y ordenados por puntaje."""

    def coincidencias(tipo):
        genero_tipo = genero if len(tipos) == 1 else _genero_para(tipo, genero)
        if genero_tipo is False:
            # TMDB no tiene ese género para este tipo: no hay nada que pedir.
            return []
        return _ventana(
            servicio,
            tipo,
            q=q,
            genero=genero_tipo,
            anio=anio,
            nota=nota,
            desde=desde,
            hasta=hasta,
        )

    # Los dos tipos a la vez: cada uno pide hasta 5 páginas.
    with ThreadPoolExecutor(max_workers=len(tipos)) as hilos:
        listas = list(hilos.map(con_contexto(coincidencias), tipos))
    # El corte va después de los filtros y antes de contar y paginar: así los
    # totales y el scroll infinito cuentan solo lo que se muestra.
    # `sorted` es estable: en un empate queda el orden de relevancia de TMDB.
    todos = sorted(
        con_corte([item for lista in listas for item in lista], q),
        key=_clave_orden(orden, tope),
    )
    por_pagina = POR_PAGINA * len(tipos)
    inicio = (page - 1) * por_pagina
    return {
        "page": page,
        "total_pages": ceil(len(todos) / por_pagina),
        "total_results": len(todos),
        "results": todos[inicio : inicio + por_pagina],
    }


# Géneros de series que son programas de entrevistas o noticias (en TMDB son
# ids de series, no de películas): quedan fuera de la filmografía como actor.
GENEROS_NEWS_Y_TALK = {10763, 10767}
# `job` de TMDB que cuenta como «director» en cada tipo. En series son los
# creadores (como «Created by» de la ficha), no los directores de episodios:
# Vince Gilligan dirigió 2 de «The X-Files» y no la creó (Q-1 de la propuesta).
JOB_DIRECTOR = {"movie": "Director", "tv": "Creator"}


def _con_persona(
    servicio,
    tipos,
    persona,
    rol,
    *,
    q,
    genero,
    anio,
    nota,
    page,
    desde,
    hasta,
    orden,
    tope,
    **_,
):
    """Lo que hizo una persona, con los mismos filtros y orden que una búsqueda.

    `discover` con `with_people` no sirve (TMDB lo ignora en series) y la
    búsqueda por texto no entiende de personas, así que se lee la filmografía
    entera (`combined_credits`, cacheada 24 h) y se filtra en memoria: la
    primera vez son 2 llamadas (créditos y detalle) y después ninguna, para
    cualquier página o combinación de filtros.
    """
    detalle, creditos = _persona_y_creditos(servicio, persona)
    # Un año es un rango de fechas de ese año: la filmografía no pasa por TMDB.
    if anio is not None and desde is None:
        desde, hasta = f"{anio}-01-01", f"{anio}-12-31"
    buscado = normalizar(q)
    items = []
    for item in _filmografia(creditos, rol):
        tipo = item["media_type"]
        genero_tipo = genero if len(tipos) == 1 else _genero_para(tipo, genero)
        if (
            tipo in tipos
            and genero_tipo is not False
            and _pasa(item, genero_tipo, nota, desde, hasta)
            and (not buscado or _contiene(item, buscado))
        ):
            items.append(item)
    todos = sorted(con_corte(items, q), key=_clave_orden(orden, tope))
    por_pagina = POR_PAGINA * len(tipos)
    inicio = (page - 1) * por_pagina
    return {
        "page": page,
        "total_pages": ceil(len(todos) / por_pagina),
        "total_results": len(todos),
        "results": todos[inicio : inicio + por_pagina],
        "persona": {
            "id": persona,
            "name": detalle.get("name") or "",
            "rol": rol,
            "gender": detalle.get("gender"),
            "profile_path": detalle.get("profile_path"),
        },
    }


def _persona_y_creditos(servicio, persona):
    """El detalle y la filmografía de TMDB, en paralelo (los dos se cachean 24 h)."""
    with ThreadPoolExecutor(max_workers=2) as hilos:
        pedidos = [
            hilos.submit(con_contexto(lambda: servicio.get_person_detail(persona))),
            hilos.submit(con_contexto(lambda: servicio.get_person_credits(persona))),
        ]
        try:
            detalle, creditos = (pedido.result() for pedido in pedidos)
        except TMDBNotFound:
            # Un id que TMDB no conoce no es «el recurso no existe» a secas:
            # tiene su propio código para que la página ofrezca limpiar el filtro.
            raise PersonaNoEncontrada from None
    return detalle, creditos


def _filmografia(creditos, rol):
    """Películas y series de la persona en ese rol, sin repetir.

    Una persona puede aparecer varias veces en el mismo título (dirigió y fue
    creadora de una serie): se queda la primera, por `(tipo, id)`.
    """
    candidatos = []
    if rol in (None, "actor"):
        candidatos += [
            item
            for item in creditos.get("cast") or []
            if not (
                item.get("media_type") == "tv"
                and GENEROS_NEWS_Y_TALK & set(item.get("genre_ids") or [])
            )
        ]
    if rol in (None, "director"):
        candidatos += [
            item
            for item in creditos.get("crew") or []
            if item.get("job") == JOB_DIRECTOR.get(item.get("media_type"))
        ]
    vistos = set()
    resultado = []
    for item in candidatos:
        clave = (item.get("media_type"), item.get("id"))
        if item.get("media_type") in ("movie", "tv") and clave not in vistos:
            vistos.add(clave)
            resultado.append(item)
    return resultado


def _contiene(item, buscado):
    """Si algún nombre del título (traducido u original) contiene el texto."""
    return any(buscado in normalizar(item.get(campo)) for campo in CAMPOS_TITULO)


def _puntaje(item):
    """Lo consagrado (votos) o lo muy esperado (popularidad de ahora) va arriba."""
    return max(
        item.get("vote_count") or 0, (item.get("popularity") or 0) * PESO_POPULARIDAD
    )


def _clave_orden(orden, tope=None):
    """Clave de `sorted` (de menor a mayor) para ordenar en memoria.

    El puntaje desempata siempre. Va al final lo que no tiene fecha (en los
    órdenes por fecha) o tiene menos de `MIN_VOTOS_ORDEN_NOTA` votos (en los
    órdenes por nota). `tope` (AAAA-MM-DD): con «Más nuevos», lo que estrena
    después va al final también, como lo anunciado que no se pidió.
    """
    if orden.startswith("fecha"):
        signo = -1 if orden == "fecha-desc" else 1

        def por_fecha(item):
            dia = _dia(item)
            fuera = dia is None or (tope is not None and _fecha(item) > tope)
            return (fuera, 0 if fuera else signo * dia, -_puntaje(item))

        return por_fecha
    if orden in ORDENES_POR_NOTA:
        signo = -1 if orden == "nota-desc" else 1

        def por_nota(item):
            pocos = (item.get("vote_count") or 0) < MIN_VOTOS_ORDEN_NOTA
            return (pocos, signo * (item.get("vote_average") or 0), -_puntaje(item))

        return por_nota
    if orden == "votos-desc":
        return lambda item: (-(item.get("vote_count") or 0), -_puntaje(item))
    return lambda item: -_puntaje(item)


def _fecha(item):
    return item.get("release_date") or item.get("first_air_date") or ""


def _dia(item):
    """La fecha del título como número de día, o `None` si no tiene o no se lee."""
    try:
        return date.fromisoformat(_fecha(item)[:10]).toordinal()
    except ValueError:
        return None


def _lado(
    servicio,
    tipo,
    *,
    genero,
    anio,
    nota,
    page,
    desde,
    hasta,
    sin_minimo,
    orden=ORDEN_POR_DEFECTO,
):
    """Sin texto: una página de `discover` de un tipo, con `media_type` puesto."""
    if genero is False:
        # TMDB no tiene ese género para este tipo: no hay nada que pedir.
        return _VACIO
    minimo, maximo = NOTAS.get(nota, (None, None))
    min_votos = MIN_VOTOS_ORDEN_NOTA if orden in ORDENES_POR_NOTA else MIN_VOTOS_NOTA
    datos = servicio.discover(
        tipo,
        genero,
        anio,
        minimo,
        page,
        sort_by=ORDENES[orden][tipo],
        # Siempre con mínimo de votos: sin él, los primeros puestos se
        # llenan de títulos sin votos y «Menos de 5» de títulos sin nota.
        min_votos=None if sin_minimo else min_votos,
        max_rating=maximo,
        sin_generos=NEWS_Y_TALK if tipo == "tv" and genero is None else None,
        desde_fecha=desde,
        hasta_fecha=hasta,
    )
    for item in datos.get("results") or []:
        item["media_type"] = tipo
    return {
        "total_pages": datos.get("total_pages") or 0,
        "total_results": datos.get("total_results") or 0,
        "results": con_poster(datos)["results"],
    }


def _ventana_discover(servicio, tipos, *, genero, tope, page, orden, **filtros):
    """«Todo» sin texto con un orden: los primeros 100 de cada tipo, juntos.

    Dos listas que TMDB ordena por separado no se pueden alternar por página y
    quedar ordenadas en conjunto, así que se leen las páginas 1 a 5 de cada
    tipo, se juntan y se ordenan acá (hasta 200 resultados; decisión del
    24/11/2026). Son hasta 10 llamadas, dentro del tope por pedido, y cada
    página queda en la caché: el scroll no vuelve a llamar a TMDB.
    """

    def del_tipo(tipo):
        genero_tipo = _genero_para(tipo, genero)
        primera = _lado(
            servicio, tipo, genero=genero_tipo, page=1, orden=orden, **filtros
        )
        ultima = min(primera["total_pages"], PAGINAS_VENTANA)
        if ultima < 2:
            return primera["results"]
        with ThreadPoolExecutor(max_workers=PAGINAS_VENTANA - 1) as hilos:
            resto = hilos.map(
                con_contexto(
                    lambda n: _lado(
                        servicio,
                        tipo,
                        genero=genero_tipo,
                        page=n,
                        orden=orden,
                        **filtros,
                    )
                ),
                range(2, ultima + 1),
            )
            return primera["results"] + [i for lado in resto for i in lado["results"]]

    with ThreadPoolExecutor(max_workers=len(tipos)) as hilos:
        listas = list(hilos.map(con_contexto(del_tipo), tipos))
    # TMDB puede repetir un título entre páginas contiguas si el orden cambia.
    vistos = set()
    juntos = []
    for item in (i for lista in listas for i in lista):
        clave = (item["media_type"], item.get("id"))
        if clave not in vistos:
            vistos.add(clave)
            juntos.append(item)
    todos = sorted(juntos, key=_clave_orden(orden, tope))
    por_pagina = POR_PAGINA * len(tipos)
    inicio = (page - 1) * por_pagina
    return {
        "page": page,
        "total_pages": ceil(len(todos) / por_pagina),
        "total_results": len(todos),
        "results": todos[inicio : inicio + por_pagina],
    }


def _ventana(servicio, tipo, *, q, genero, anio, nota, desde=None, hasta=None):
    """Los primeros 100 de la búsqueda de TMDB que pasan los filtros.

    La página 1 dice cuántas hay; las demás (hasta la 5) salen en paralelo.
    `httpx.Client` y el cliente de Redis se pueden compartir entre hilos, y
    acá no se toca la base. Cada página queda en la caché por su cuenta: la
    misma búsqueda con otro filtro no vuelve a llamar a TMDB. Género, nota y
    fechas se filtran acá porque la búsqueda por nombre de TMDB no los admite.
    """
    primera = servicio.search(q, tipo, 1, anio=anio)
    ultima = min(primera.get("total_pages") or 1, PAGINAS_VENTANA)
    with ThreadPoolExecutor(max_workers=PAGINAS_VENTANA - 1) as hilos:
        resto = list(
            hilos.map(
                con_contexto(lambda n: servicio.search(q, tipo, n, anio=anio)),
                range(2, ultima + 1),
            )
        )
    items = [
        item for pagina in (primera, *resto) for item in pagina.get("results") or []
    ]
    elegidos = [item for item in items if _pasa(item, genero, nota, desde, hasta)]
    for item in elegidos:
        item["media_type"] = tipo
    return elegidos


def _pasa(item, genero, nota, desde=None, hasta=None):
    if genero is not None and genero not in (item.get("genre_ids") or []):
        return False
    if desde is not None or hasta is not None:
        # Sin fecha no se sabe cuándo es: queda afuera. AAAA-MM-DD se compara
        # como texto.
        fecha = item.get("release_date") or item.get("first_air_date") or ""
        if not fecha or (desde and fecha < desde) or (hasta and fecha > hasta):
            return False
    if nota is None:
        return True
    if (item.get("vote_count") or 0) < MIN_VOTOS_NOTA:
        return False
    minimo, maximo = NOTAS[nota]
    valor = item.get("vote_average") or 0
    return (minimo is None or valor >= minimo) and (maximo is None or valor <= maximo)


def _alternar(*listas):
    """Película, serie, película…; el resto de la más larga al final (como el Home)."""
    resultado = []
    for i in range(max((len(lista) for lista in listas), default=0)):
        resultado.extend(lista[i] for lista in listas if i < len(lista))
    return resultado
