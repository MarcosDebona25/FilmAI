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

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

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


# Un validador por tool, armado una sola vez al importar el módulo. Revisa lo que
# manda el modelo contra el mismo esquema que el modelo recibió: tipos, valores
# permitidos (`enum`), obligatorios y que no sobre nada. En Java sería algo como
# Bean Validation (`@NotNull`, `@Pattern`) antes de entrar al método.
_VALIDADORES = {
    esquema["function"]["name"]: Draft202012Validator(esquema["function"]["parameters"])
    for esquema in ESQUEMAS
}


def _error_de_argumentos(validador, argumentos):
    """El primer problema de los argumentos, en una línea, o `None` si están bien.

    Va el nombre del campo adelante («generos.0: ...») para que el modelo sepa qué
    corregir. Para un `enum`, el mensaje de `jsonschema` ya trae los valores válidos.
    """
    # `best_match` elige, entre todos los errores, el más útil para mostrar.
    error = best_match(validador.iter_errors(argumentos))
    if error is None:
        return None
    campo = ".".join(str(parte) for parte in error.absolute_path) or "argumentos"
    return f"{campo}: {error.message}"


def ejecutar(ctx, nombre, argumentos):
    """Corre una tool. Si no existe o falla, devuelve `tool_failed`.

    Antes revisa los argumentos contra el esquema: si están mal, devuelve
    `invalid_arguments` con el detalle y no la corre. El modelo lo lee y corrige en
    la vuelta siguiente. Sin esto, un género en español dejaba vacía la búsqueda
    semántica y `descubrir` buscaba sin el filtro (set dorado, 08/11/2026).
    """
    validador = _VALIDADORES.get(nombre)
    if validador is not None and isinstance(argumentos, dict):
        # Un `null` en un opcional cuenta como no mandado: algunos modelos los
        # completan así, y las tools ya tienen `None` como valor por defecto.
        argumentos = {k: v for k, v in argumentos.items() if v is not None}
        detalle = _error_de_argumentos(validador, argumentos)
        if detalle is not None:
            logger.info("Argumentos inválidos para %s: %s", nombre, detalle)
            return {"error": "invalid_arguments", "detalle": detalle}
    try:
        # `**` abre el diccionario: {"id_tmdb": 5} pasa como `id_tmdb=5`. Así esta
        # función sirve para todas las tools sin saber qué recibe cada una.
        return FUNCIONES[nombre](ctx, **argumentos)
    except Exception:
        # Amplio a propósito: TMDB, Ollama, el tope de llamadas o argumentos mal
        # armados por el modelo. Nada de eso debe cortar el turno.
        logger.exception("La tool %s falló", nombre)
        return {"error": "tool_failed"}
