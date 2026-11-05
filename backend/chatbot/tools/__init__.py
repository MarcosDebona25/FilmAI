"""Las tools del chatbot: lo que el modelo puede pedir que el backend ejecute.

Son funciones síncronas `(ctx, **argumentos)`. El orquestador las corre con
`ejecutar()`, que nunca lanza: una tool que falla es información para el modelo,
no el fin del turno (09/10/2026).

Este archivo es la puerta del paquete `chatbot.tools`: desde afuera se importa
de acá, sin saber cómo está organizado adentro. Python corre un `__init__.py`
al importar su carpeta; no tiene relación con el `__init__` de una clase.

Lo usa: el orquestador (PR 3); hoy, solo los tests.
Usa: `busqueda.py` y `personales.py` (las tools), `esquemas.py` y `turno.py`.
Mapa completo: `backend/chatbot/README.md`.
"""

import logging

from chatbot.tools import busqueda, personales
from chatbot.tools.esquemas import ESQUEMAS
from chatbot.tools.turno import ContextoTurno

# Lo que este paquete ofrece hacia afuera.
__all__ = ["ESQUEMAS", "FUNCIONES", "ContextoTurno", "ejecutar"]

# Registra mensajes con nivel y nombre de módulo: es un `print` configurable.
logger = logging.getLogger(__name__)

# Nombre de la tool, como la pide el modelo, y la función que la resuelve.
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
        # `**` abre el diccionario: {"id_tmdb": 5} pasa como `id_tmdb=5`. Así esta
        # función sirve para todas las tools sin saber qué recibe cada una.
        return FUNCIONES[nombre](ctx, **argumentos)
    except Exception:
        # Amplio a propósito: TMDB, Ollama, el tope de llamadas o argumentos mal
        # armados por el modelo. Nada de eso debe cortar el turno.
        logger.exception("La tool %s falló", nombre)
        return {"error": "tool_failed"}
