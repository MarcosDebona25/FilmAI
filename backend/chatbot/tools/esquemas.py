"""Lo que el modelo sabe de cada tool: nombre, para qué sirve y qué recibe.

Ninguna recibe un usuario: sale del contexto del turno, no de lo que pida el modelo.

Lo usa: el orquestador (PR 3), que se lo manda al modelo en cada llamada. El modelo
lee estas descripciones para decidir qué tool pedir.
"""

# Los nombres que usa TMDB en inglés, verificados contra la API el 05/11/2026.
GENEROS = [
    "Action",
    "Action & Adventure",
    "Adventure",
    "Animation",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Family",
    "Fantasy",
    "History",
    "Horror",
    "Kids",
    "Music",
    "Mystery",
    "News",
    "Reality",
    "Romance",
    "Sci-Fi & Fantasy",
    "Science Fiction",
    "Soap",
    "TV Movie",
    "Talk",
    "Thriller",
    "War",
    "War & Politics",
    "Western",
]

_TIPO = {"type": "string", "enum": ["movie", "tv"]}
_ID = {"type": "integer"}
_FILTROS = {
    "generos": {
        "type": "array",
        "items": {"type": "string", "enum": GENEROS},
        "description": "Alcanza con que el título tenga uno.",
    },
    "tipo": _TIPO,
    "anio_desde": {"type": "integer"},
    "anio_hasta": {"type": "integer"},
    "nota_minima": {"type": "number", "description": "Nota de TMDB, de 0 a 10."},
    "duracion_max": {
        "type": "integer",
        "description": "Minutos. Solo es confiable en películas.",
    },
}


def _esquema(nombre, descripcion, propiedades, requeridas=()):
    return {
        "type": "function",
        "function": {
            "name": nombre,
            "description": descripcion,
            "parameters": {
                "type": "object",
                "properties": propiedades,
                "required": list(requeridas),
                "additionalProperties": False,
            },
        },
    }


ESQUEMAS = [
    _esquema(
        "buscar_por_titulo",
        "Busca películas y series por su nombre.",
        {"titulo": {"type": "string"}, "tipo": _TIPO, "anio": {"type": "integer"}},
        ["titulo"],
    ),
    _esquema(
        "descubrir",
        "Busca títulos populares por datos concretos: género, año, nota o duración.",
        _FILTROS,
    ),
    _esquema(
        "similares_a",
        "Busca títulos parecidos a uno que devolvió otra tool.",
        {"id_tmdb": _ID, "tipo": _TIPO},
        ["id_tmdb", "tipo"],
    ),
    _esquema(
        "buscar_por_persona",
        "Busca los títulos más conocidos de un actor o director.",
        {
            "nombre": {"type": "string"},
            "rol": {"type": "string", "enum": ["actor", "director"]},
        },
        ["nombre"],
    ),
    _esquema(
        "detalle",
        "Trae los datos de un título que devolvió otra tool.",
        {"id_tmdb": _ID, "tipo": _TIPO},
        ["id_tmdb", "tipo"],
    ),
    _esquema(
        "buscar_semantico",
        "Busca por significado en el catálogo local, para pedidos que no son "
        "datos concretos: un tono, un tema o una sensación. Usá los filtros para "
        "lo que sí es un dato, como la duración o el género.",
        {"consulta": {"type": "string"}, **_FILTROS},
        ["consulta"],
    ),
    _esquema(
        "mis_listas",
        "Sin `lista`, devuelve las listas del usuario. Con `lista`, lo que hay "
        "adentro: `vistas`, `pendientes`, `favoritos` o el `id` de una personalizada.",
        {"lista": {"type": "string"}},
    ),
    _esquema(
        "mostrar_tarjetas",
        "Muestra hasta 3 títulos como tarjetas. Solo títulos que devolvió otra "
        "tool en este turno.",
        {
            "tarjetas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"id_tmdb": _ID, "tipo": _TIPO},
                    "required": ["id_tmdb", "tipo"],
                    "additionalProperties": False,
                },
            }
        },
        ["tarjetas"],
    ),
]
