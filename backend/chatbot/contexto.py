"""El perfil del usuario que recibe el modelo, leído de la base en cada mensaje.

Lo usa: `prompts.py` (PR 3), que lo pone en las instrucciones del modelo.
Usa: los modelos `Calificacion` y `Tiene`, y `anonimizar()` para las reseñas.
"""

from catalogo.models import Calificacion
from chatbot.anonimizar import ESTRICTO, anonimizar
from listas.models import ClaveLista, Tiene

_NOTA_MINIMA_GUSTO = 7
_NOTA_MAXIMA_DISGUSTO = 4
_TOPE_GUSTOS = 15
_TOPE_RESTO = 10
_LARGO_EXTRACTO = 160


def _extracto(texto, usuario):
    """Una reseña lista para el perfil: anonimizada, en una línea y recortada."""
    # Se anonimiza antes de recortar: un corte en el medio de un nombre dejaría
    # un pedazo que ya no se reconoce. Sin saltos de línea, para que una reseña
    # no pueda parecer otra sección del perfil.
    limpio = " ".join(anonimizar(texto, usuario, ESTRICTO).split())
    if len(limpio) <= _LARGO_EXTRACTO:
        return limpio
    return limpio[: _LARGO_EXTRACTO - 1] + "…"


def _gustos(usuario):
    """Lo mejor calificado, con un extracto de la reseña si tiene."""
    calificaciones = (
        Calificacion.objects.filter(
            usuario=usuario,
            activa=True,
            valor__gte=_NOTA_MINIMA_GUSTO,
            produccion__disponible_en_tmdb=True,
        )
        .select_related("produccion", "resena")
        .order_by("-valor", "-fecha", "-pk")[:_TOPE_GUSTOS]
    )
    items = []
    for calificacion in calificaciones:
        detalle = str(calificacion.valor)
        resena = getattr(calificacion, "resena", None)
        if resena is not None and resena.activa:
            detalle += f", «{_extracto(resena.texto, usuario)}»"
        items.append(f"{calificacion.produccion.titulo} ({detalle})")
    return items


def _disgustos(usuario):
    """Lo peor calificado: le dice al modelo qué evitar."""
    calificaciones = (
        Calificacion.objects.filter(
            usuario=usuario,
            activa=True,
            valor__lte=_NOTA_MAXIMA_DISGUSTO,
            produccion__disponible_en_tmdb=True,
        )
        .select_related("produccion")
        .order_by("valor", "-fecha", "-pk")[:_TOPE_RESTO]
    )
    return [f"{c.produccion.titulo} ({c.valor})" for c in calificaciones]


def _de_la_lista(usuario, clave):
    """Los títulos más recientes de una lista predeterminada."""
    return list(
        Tiene.objects.filter(
            lista__usuario=usuario,
            lista__clave=clave,
            produccion__disponible_en_tmdb=True,
        )
        .order_by("-fecha_agregado", "-pk")
        .values_list("produccion__titulo", flat=True)[:_TOPE_RESTO]
    )


def armar_perfil(usuario):
    """Texto plano con lo que le gustó, lo que no, lo último visto y sus favoritos.

    Sin identificadores: no lleva nombre ni correo, y las reseñas salen
    anonimizadas. Los títulos son catálogo y van tal cual.
    """
    secciones = (
        (f"Le gustó (nota ≥ {_NOTA_MINIMA_GUSTO})", _gustos(usuario)),
        (f"No le gustó (nota ≤ {_NOTA_MAXIMA_DISGUSTO})", _disgustos(usuario)),
        ("Últimas vistas", _de_la_lista(usuario, ClaveLista.VISTAS)),
        ("Favoritos", _de_la_lista(usuario, ClaveLista.FAVORITOS)),
    )
    return "\n".join(
        f"{titulo}: {', '.join(items)}" for titulo, items in secciones if items
    )
