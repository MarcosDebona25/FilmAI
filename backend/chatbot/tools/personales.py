"""Tools que leen datos del usuario del turno o eligen qué mostrarle.

Las llama: `ejecutar()` de `tools/__init__.py`.
Usan: los modelos de `listas`, `anonimizar()` y lo anotado en `ContextoTurno`.
"""

from chatbot.anonimizar import ESTRICTO, anonimizar
from chatbot.tools.turno import desde_produccion, publicar
from listas.models import ClaveLista, Lista, Tiene

_TOPE_TARJETAS = 3
_TOPE_ITEMS_DE_LISTA = 30


def _nombre_visible(lista, usuario):
    """El nombre de una lista sin datos personales: lo escribió el usuario."""
    return anonimizar(lista.nombre, usuario, ESTRICTO)


def _buscar_lista(usuario, referencia):
    """Encuentra una lista del usuario por clave (`vistas`) o por id (`"69"`).

    Devuelve `None` si no existe o no es suya.
    """
    # Siempre filtrado por el usuario del turno: un `id` ajeno no existe para él.
    listas = Lista.objects.filter(usuario=usuario)
    if referencia in ClaveLista.values:
        return listas.filter(clave=referencia).first()
    if str(referencia).isdigit():
        return listas.filter(pk=int(referencia)).first()
    return None


def mis_listas(ctx, lista=None):
    """Sin `lista`, las listas del usuario; con ella, lo que hay adentro."""
    if lista is None:
        listas = Lista.objects.filter(usuario=ctx.usuario)
        return {
            "listas": [
                {"id": item.pk, "nombre": _nombre_visible(item, ctx.usuario)}
                for item in listas
            ]
        }

    encontrada = _buscar_lista(ctx.usuario, lista)
    if encontrada is None:
        return {"error": "not_found"}
    filas = (
        Tiene.objects.filter(lista=encontrada)
        .select_related("produccion")
        .prefetch_related("produccion__traducciones")
        .order_by("-fecha_agregado", "-pk")[:_TOPE_ITEMS_DE_LISTA]
    )
    titulos = [desde_produccion(fila.produccion, ctx.idioma) for fila in filas]
    return {
        "lista": _nombre_visible(encontrada, ctx.usuario),
        "resultados": publicar(
            ctx, titulos, sacar_vistas=False, tope=_TOPE_ITEMS_DE_LISTA
        ),
    }


def _clave_de(pedida):
    """Convierte lo que mandó el modelo en `(id_tmdb, tipo)`, o `None` si vino mal armado."""
    try:
        return (int(pedida["id_tmdb"]), pedida["tipo"])
    except (KeyError, TypeError, ValueError):
        return None


def mostrar_tarjetas(ctx, tarjetas):
    """Suma tarjetas al turno. Lo que no vale se descarta en silencio.

    Solo pasan títulos que una tool devolvió en este turno: así el modelo no
    puede mostrar uno inventado, y las vistas quedan afuera.
    """
    elegidas = {(t["id_tmdb"], t["tipo"]) for t in ctx.tarjetas}
    for pedida in tarjetas:
        clave = _clave_de(pedida)
        if len(ctx.tarjetas) == _TOPE_TARJETAS:
            break
        if clave in ctx.encontrados and clave not in ctx.vistas | elegidas:
            ctx.tarjetas.append(ctx.encontrados[clave])
            elegidas.add(clave)
    return {"tarjetas": ctx.tarjetas}
