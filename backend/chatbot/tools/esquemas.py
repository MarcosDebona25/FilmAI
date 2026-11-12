"""Lo que el modelo sabe de cada tool: nombre, para qué sirve y qué recibe.

Ninguna recibe un usuario: sale del contexto del turno, no de lo que pida el modelo.

Lo usa: el orquestador (PR 3), que se lo manda al modelo en cada llamada. El modelo
lee estas descripciones para decidir qué tool pedir.
"""

from catalogo.models import ID_TMDB_MAXIMO

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
# Topes de lo que el modelo puede mandar. `maxLength` limita los textos; `minimum` y
# `maximum`, los números (como `@Size` y `@Min`/`@Max` de Bean Validation en Java).
# `ejecutar()` los revisa antes de correr la tool. El `id_tmdb` llega hasta el máximo
# de un `integer` de Postgres, el mismo tope que usan las demás entradas con un id.
_ID = {"type": "integer", "minimum": 1, "maximum": ID_TMDB_MAXIMO}
# El cine nace en 1888; 2100 deja margen sin dejar pasar cualquier número.
_ANIO = {"type": "integer", "minimum": 1800, "maximum": 2100}
_TITULO = {"type": "string", "maxLength": 200}
# Igual que el mensaje del usuario: 500 caracteres.
_CONSULTA = {"type": "string", "maxLength": 500}
_NOMBRE = {"type": "string", "maxLength": 100}
# Una clave («favoritos») o el id de una lista: nunca pasa de unas pocas letras.
_LISTA = {"type": "string", "maxLength": 20}
_FILTROS = {
    "generos": {
        "type": "array",
        "items": {"type": "string", "enum": GENEROS},
        "description": "Alcanza con que el título tenga uno.",
    },
    "tipo": _TIPO,
    "anio_desde": _ANIO,
    "anio_hasta": _ANIO,
    "nota_minima": {"type": "number", "description": "Nota de TMDB, de 0 a 10."},
    "duracion_max": {
        "type": "integer",
        "minimum": 1,
        "maximum": 1000,
        "description": "Minutos. Solo es confiable en películas.",
    },
}


def _esquema(nombre, descripcion, propiedades, requeridas=()):
    """Arma una tool en el formato que espera la API compatible con OpenAI.

    `additionalProperties: False` le indica al modelo que no invente otros argumentos.
    """
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
        "Busca películas y series por su nombre. Un resultado con `vista: true` ya "
        "lo vio el usuario: no lo recomiendes, salvo que lo haya pedido.",
        {"titulo": _TITULO, "tipo": _TIPO, "anio": _ANIO},
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
            "nombre": _NOMBRE,
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
        {"consulta": _CONSULTA, **_FILTROS},
        ["consulta"],
    ),
    _esquema(
        "mis_listas",
        "Sin `lista`, devuelve las listas del usuario. Con `lista`, lo que hay "
        "adentro: `vistas`, `pendientes`, `favoritos` o el `id` de una personalizada.",
        {"lista": _LISTA},
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
