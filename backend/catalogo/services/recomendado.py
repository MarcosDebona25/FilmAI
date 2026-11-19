"""«Recomendado para ti» del Home (C-05, doc 04 §3.3).

Parte de lo que el usuario calificó con 7 o más: por tipo, los 3 géneros más
repetidos. Con ellos pide a TMDB lo más popular de esos géneros (unidos con OR,
con un mínimo de votos) y saca lo que el usuario ya tiene en «Vistas» o en
«Pendientes» (decisión del 13/11/2026: lo anotado para ver tampoco se sugiere).

No sabe de HTTP ni de idiomas: la vista le pasa el servicio de TMDB ya
localizado y una función que traduce ids de género a nombres.
"""

from collections import Counter
from itertools import zip_longest

from catalogo.models import Calificacion, TipoProduccion
from listas.models import ClaveLista, Tiene

NOTA_MINIMA = 7
CANTIDAD_GENEROS = 3
# Verificado el 13/10/2026: sin mínimo, 9 de 20 películas tenían menos de 100
# votos y aparecía contenido adulto que TMDB no marca como tal.
MIN_VOTOS = 100
MAXIMO = 15

# El modelo guarda «pelicula»/«serie»; TMDB y la API usan movie/tv.
TIPO_DOMINIO = {"movie": TipoProduccion.PELICULA, "tv": TipoProduccion.SERIE}
TIPO_TMDB = {dominio: tmdb for tmdb, dominio in TIPO_DOMINIO.items()}

VACIO = {"generos": [], "results": []}


def generos_favoritos(usuario, tipo):
    """Los ids de género más repetidos, con su cuenta: `[(18, 3), (53, 2)]`.

    Las calificaciones llegan de la más reciente a la más vieja (el orden del
    modelo es `-fecha, -id`) y `Counter.most_common` deja los empates en el
    orden en que aparecieron: un empate lo gana el género más reciente.
    """
    listas_de_ids = Calificacion.objects.filter(
        usuario=usuario,
        activa=True,
        valor__gte=NOTA_MINIMA,
        produccion__tipo=TIPO_DOMINIO[tipo],
    ).values_list("produccion__generos_ids", flat=True)
    cuenta = Counter()
    for ids in listas_de_ids:
        cuenta.update(ids)
    return cuenta.most_common(CANTIDAD_GENEROS)


def _pares_de(usuario, claves):
    """Pares `(id_tmdb, tipo de TMDB)` de lo que el usuario tiene en esas listas."""
    filas = Tiene.objects.filter(
        lista__usuario=usuario, lista__clave__in=claves
    ).values_list("produccion__id_tmdb", "produccion__tipo")
    return {(id_tmdb, TIPO_TMDB[tipo]) for id_tmdb, tipo in filas}


def vistos(usuario):
    """Pares `(id_tmdb, tipo de TMDB)` de lo que el usuario ya conoce: «Vistas» y «Viendo».

    «Viendo» (PR 4, 15/11/2026) cuenta como conocido: lo que está mirando no se
    le recomienda, igual que lo ya visto. Es el único helper que usan el Inicio,
    las sugerencias de lista, «More like» de la ficha y el chatbot, así que
    sumarlo acá lo excluye de todos.

    Va el par y no solo el id porque TMDB numera películas y series por
    separado: la película 108978 y la serie 108978 son dos cosas distintas.
    """
    return _pares_de(usuario, (ClaveLista.VISTAS, ClaveLista.VIENDO))


def en_viendo(usuario):
    """Pares de lo que el usuario está mirando ahora (la parte «Viendo» de `vistos`).

    El chatbot los distingue de lo ya visto: «ya la viste» sería falso.
    """
    return _pares_de(usuario, (ClaveLista.VIENDO,))


def pendientes(usuario):
    """Pares `(id_tmdb, tipo de TMDB)` de la lista «Pendientes» (mismo formato que `vistos`)."""
    filas = Tiene.objects.filter(
        lista__usuario=usuario, lista__clave=ClaveLista.PENDIENTES
    ).values_list("produccion__id_tmdb", "produccion__tipo")
    return {(id_tmdb, TIPO_TMDB[tipo]) for id_tmdb, tipo in filas}


def _de_un_tipo(servicio, tipo, generos, excluir):
    datos = servicio.discover(
        tipo,
        genero="|".join(str(genero) for genero, _ in generos),
        sort_by="popularity.desc",
        min_votos=MIN_VOTOS,
    )
    resultados = [
        {**item, "media_type": tipo}
        for item in datos.get("results") or []
        if (item.get("id"), tipo) not in excluir
    ]
    return resultados[:MAXIMO]


def _alternar(*listas):
    """Película, serie, película…; cuando una se acaba, sigue la otra."""
    mezcla = [
        item for grupo in zip_longest(*listas) for item in grupo if item is not None
    ]
    return mezcla[:MAXIMO]


def recomendar(usuario, tipo, servicio, nombres_de_generos):
    """Arma la respuesta de `GET /api/catalogo/recommended/`.

    `tipo` es `all`, `movie` o `tv`. `servicio` responde `discover` como
    `TMDBClientCache`. `nombres_de_generos(tipo)` devuelve `{id: nombre}` en el
    idioma del pedido.
    """
    tipos = ("movie", "tv") if tipo == "all" else (tipo,)
    favoritos = {t: generos_favoritos(usuario, t) for t in tipos}
    tipos = [t for t in tipos if favoritos[t]]
    if not tipos:
        # Sin calificaciones de 7 o más no hay de dónde partir: ni se llama a TMDB.
        return VACIO

    # `|` es la unión de conjuntos (como `addAll` en Java).
    excluir = vistos(usuario) | pendientes(usuario)
    resultados = _alternar(
        *(_de_un_tipo(servicio, t, favoritos[t], excluir) for t in tipos)
    )

    # En `all` se suman las cuentas de los dos tipos; Drama (18) y Crimen (80)
    # tienen el mismo id en películas y en series.
    cuenta = Counter()
    nombres = {}
    for t in tipos:
        cuenta.update(dict(favoritos[t]))
        nombres.update(nombres_de_generos(t))
    generos = [
        nombres[genero]
        for genero, _ in cuenta.most_common(CANTIDAD_GENEROS)
        if genero in nombres
    ]
    return {"generos": generos, "results": resultados}
