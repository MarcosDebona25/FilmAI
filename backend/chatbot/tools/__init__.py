"""Las tools del chatbot: lo que el modelo puede pedir que el backend ejecute.

Son funciones síncronas `(ctx, **argumentos)`. El orquestador las corre con
`ejecutar()`, que nunca lanza: una tool que falla es información para el modelo,
no el fin del turno (09/10/2026).
"""

import logging

from chatbot.tools import busqueda, personales
from chatbot.tools.esquemas import ESQUEMAS
from chatbot.tools.turno import ContextoTurno

__all__ = ["ESQUEMAS", "FUNCIONES", "ContextoTurno", "ejecutar"]

logger = logging.getLogger(__name__)

FUNCIONES = {
    "buscar_por_titulo": busqueda.buscar_por_titulo,
    "descubrir": busqueda.descubrir,
    "similares_a": busqueda.similares_a,
    "buscar_por_persona": busqueda.buscar_por_persona,
    "detalle": busqueda.detalle,
    "buscar_semantico": busqueda.semantico,
    "mis_listas": personales.mis_listas,
    "mostrar_tarjetas": personales.mostrar_tarjetas,
}


def ejecutar(ctx, nombre, argumentos):
    """Corre una tool. Si no existe o falla, devuelve `tool_failed`."""
    try:
        return FUNCIONES[nombre](ctx, **argumentos)
    except Exception:
        # Amplio a propósito: TMDB, Ollama, el tope de llamadas o argumentos mal
        # armados por el modelo. Nada de eso debe cortar el turno.
        logger.exception("La tool %s falló", nombre)
        return {"error": "tool_failed"}
