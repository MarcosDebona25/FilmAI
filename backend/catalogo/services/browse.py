"""Buscar (C-06): combina `discover` y `search` de TMDB según lo pedido.

TMDB no tiene una consulta que haga todo (verificado el 14/10/2026): su
búsqueda por nombre acepta el año pero ignora género y nota, y `discover`
acepta todos los filtros pero no texto. Este módulo elige, por cada tipo, la
llamada que corresponde, y en «Todo» alterna películas y series.

| Texto | Por tipo                                                         |
| ----- | ---------------------------------------------------------------- |
| no    | `discover`, por popularidad; «Todo» alterna películas y series   |
| sí    | los primeros 100 de `search`, filtrados y ordenados por puntaje  |

Con texto, el orden de TMDB es de relevancia y deja arriba títulos con 0 votos
(«the office»: tres películas sin votos antes que la serie con 5579). Se ordena
por el mayor entre los votos y la popularidad por 100: arriba lo consagrado o lo
muy esperado, al fondo lo desconocido (pedido del usuario, 14/10/2026).

El diseño completo está en `openspec/changes/search-catalogo/design.md`.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from math import ceil

from django.utils import timezone

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

# `nota` → (mínimo, máximo) de `vote_average`. «Menos de 5» es un techo.
NOTAS = {
    "9+": (9, None),
    "8+": (8, None),
    "7+": (7, None),
    "6+": (6, None),
    "5+": (5, None),
    "m5": (None, 4.99),
}

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
    filtros = {
        "q": q,
        "genero": genero,
        "anio": None if desde else anio,
        "nota": nota,
        "page": page,
        "desde": desde,
        "hasta": hasta,
        "sin_minimo": futuro and nota is None,
    }
    if q:
        return _con_texto(servicio, tipos, genero=genero, **_sin_genero(filtros))
    del filtros["q"]
    if len(tipos) == 1:
        lados = [_lado(servicio, tipos[0], genero=genero, **_sin_genero(filtros))]
    else:
        # Los dos tipos a la vez: en la ventana cada uno pide hasta 5 páginas.
        with ThreadPoolExecutor(max_workers=2) as hilos:
            lados = list(
                hilos.map(
                    lambda t: _lado(
                        servicio,
                        t,
                        genero=_genero_para(t, genero),
                        **_sin_genero(filtros),
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


def _con_texto(servicio, tipos, *, q, genero, anio, nota, page, desde, hasta, **_):
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
        listas = list(hilos.map(coincidencias, tipos))
    # `sorted` es estable: en un empate queda el orden de relevancia de TMDB.
    todos = sorted(
        (item for lista in listas for item in lista), key=_puntaje, reverse=True
    )
    por_pagina = POR_PAGINA * len(tipos)
    inicio = (page - 1) * por_pagina
    return {
        "page": page,
        "total_pages": ceil(len(todos) / por_pagina),
        "total_results": len(todos),
        "results": todos[inicio : inicio + por_pagina],
    }


def _puntaje(item):
    """Lo consagrado (votos) o lo muy esperado (popularidad de ahora) va arriba."""
    return max(
        item.get("vote_count") or 0, (item.get("popularity") or 0) * PESO_POPULARIDAD
    )


def _lado(servicio, tipo, *, genero, anio, nota, page, desde, hasta, sin_minimo):
    """Sin texto: una página de `discover` de un tipo, con `media_type` puesto."""
    if genero is False:
        # TMDB no tiene ese género para este tipo: no hay nada que pedir.
        return _VACIO
    minimo, maximo = NOTAS.get(nota, (None, None))
    datos = servicio.discover(
        tipo,
        genero,
        anio,
        minimo,
        page,
        sort_by="popularity.desc",
        # Siempre con mínimo de votos: sin él, los primeros puestos se
        # llenan de títulos sin votos y «Menos de 5» de títulos sin nota.
        min_votos=None if sin_minimo else MIN_VOTOS_NOTA,
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
        "results": datos.get("results") or [],
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
                lambda n: servicio.search(q, tipo, n, anio=anio), range(2, ultima + 1)
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
