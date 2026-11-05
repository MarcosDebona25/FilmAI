"""Lo que comparten las tools durante un turno y cómo se presenta cada título.

Un turno es una pregunta del usuario y su respuesta, no toda la conversación.

Lo usan: `busqueda.py` y `personales.py`, que devuelven sus resultados con
`publicar()`, y el orquestador (PR 3), que crea el `ContextoTurno`.
Usa: `vistos()` para saber qué ya vio el usuario y `texto_localizado()` para el idioma.
"""

from dataclasses import dataclass, field

from catalogo.services.recomendado import TIPO_TMDB, vistos
from catalogo.services.traducciones import texto_localizado

TOPE_RESULTADOS = 10
_LARGO_SINOPSIS = 300


# `@dataclass` escribe solo el `__init__` a partir de los campos de abajo: sirve
# para clases que únicamente guardan datos.
@dataclass
class ContextoTurno:
    """Estado de un turno. No viene del modelo: él no puede cambiar el usuario.

    Se crea con cada mensaje y se descarta al responder. Las tools reciben este
    objeto como `ctx`: es lo que comparten entre ellas durante el turno.
    """

    usuario: object
    idioma: str
    vistas: set
    # Lo que devolvió alguna tool en este turno, lo único que puede ser tarjeta.
    # `field(default_factory=...)` crea un dict o una lista nuevos para cada objeto.
    # Con `= {}` todos los turnos compartirían el mismo, de todos los usuarios.
    encontrados: dict = field(default_factory=dict)
    tarjetas: list = field(default_factory=list)

    # `@classmethod`: se llama sobre la clase, sin tener un objeto todavía:
    # `ContextoTurno.para(usuario, "es")`. Es un constructor con un paso extra.
    # `cls` es la clase, como `self` es el objeto: `cls(...)` crea el objeto.
    @classmethod
    def para(cls, usuario, idioma):
        """Crea el contexto de un turno y lee una sola vez qué ya vio el usuario."""
        return cls(usuario=usuario, idioma=idioma, vistas=vistos(usuario))


# El `*` obliga a pasar los argumentos por nombre: con tantos, evita confundirlos.
def titulo(*, id_tmdb, tipo, nombre, anio, generos, duracion, nota, sinopsis, poster):
    """Un título tal como lo manejan las tools, venga de TMDB o de nuestra base."""
    return {
        "id_tmdb": id_tmdb,
        "tipo": tipo,
        "titulo": nombre,
        "anio": anio,
        "generos": generos,
        "duracion": duracion,
        "nota_tmdb": round(nota, 1) if nota else None,
        "sinopsis_corta": (sinopsis or "")[:_LARGO_SINOPSIS],
        "poster": poster or None,
    }


def desde_produccion(produccion, idioma):
    """Un título a partir de una fila de la base, en el idioma del turno."""
    fecha = produccion.fecha_lanzamiento
    return titulo(
        id_tmdb=produccion.id_tmdb,
        tipo=TIPO_TMDB[produccion.tipo],
        nombre=texto_localizado(produccion, "titulo", idioma),
        anio=fecha.year if fecha else None,
        generos=produccion.generos,
        duracion=produccion.duracion,
        nota=produccion.calificacion_promedio,
        sinopsis=texto_localizado(produccion, "sinopsis", idioma),
        poster=texto_localizado(produccion, "poster", idioma),
    )


def publicar(ctx, titulos, *, sacar_vistas=True, tope=TOPE_RESULTADOS):
    """Deja lo que el modelo puede ver y anota esos títulos en el turno.

    El póster queda solo en lo anotado: al modelo no le sirve y gasta tokens.
    """
    publicados, repetidos = [], set()
    for item in titulos:
        clave = (item["id_tmdb"], item["tipo"])
        if clave in repetidos or (sacar_vistas and clave in ctx.vistas):
            continue
        repetidos.add(clave)
        ctx.encontrados[clave] = {
            "id_tmdb": item["id_tmdb"],
            "tipo": item["tipo"],
            "titulo": item["titulo"],
            "poster": item["poster"],
            "anio": item["anio"],
        }
        publicados.append({k: v for k, v in item.items() if k != "poster"})
        if len(publicados) == tope:
            break
    return publicados
