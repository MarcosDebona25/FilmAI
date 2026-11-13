"""Tools que leen datos del usuario del turno.

Las llama: `ejecutar()` de `tools/__init__.py`.
Usan: los modelos de `listas`, `anonimizar()` y lo anotado en `ContextoTurno`.
"""

from chatbot.anonimizar import ESTRICTO, anonimizar
from chatbot.tools.turno import desde_produccion, publicar
from listas.models import ClaveLista, Lista, Tiene

_TOPE_ITEMS_DE_LISTA = 30


def _nombre_visible(lista, usuario):
    """El nombre de una lista sin datos personales: lo escribió el usuario."""
    return anonimizar(lista.nombre, usuario, ESTRICTO)


def _buscar_lista(usuario, referencia):
    """Encuentra una lista del usuario por clave (`vistas`) o por id (`"69"`).

    Devuelve `None` si no existe o no es suya.
    """
    # Siempre filtrado por el usuario del turno: un `id` ajeno no existe para él. Y
    # solo las activas, como las vistas de `listas`: una dada de baja no existe.
    listas = Lista.objects.filter(usuario=usuario, activa=True)
    if referencia in ClaveLista.values:
        return listas.filter(clave=referencia).first()
    if str(referencia).isdigit():
        return listas.filter(pk=int(referencia)).first()
    return None


def mis_listas(ctx, lista=None):
    """Sin `lista`, las listas del usuario; con ella, lo que hay adentro."""
    if lista is None:
        listas = Lista.objects.filter(usuario=ctx.usuario, activa=True)
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
        # Sin lápidas: un título que TMDB ya no tiene no se ofrece (#180).
        Tiene.objects.filter(lista=encontrada, produccion__disponible_en_tmdb=True)
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
