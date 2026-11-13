"""El juez de tarjetas: un segundo llamado al modelo que decide qué títulos mostrar.

A veces el modelo recomienda en el texto pero no llama a `mostrar_tarjetas` (pasó en
~2 de 27 turnos del set dorado). Antes, el orquestador lo adivinaba con expresiones
regulares (negrita, pistas de «serie» o «película», plegado de acentos). Ahora se le
pregunta a un modelo, que entiende qué es una recomendación y qué es una referencia
(«si te gustó Hereditary»). Es una sola llamada, sin tools, que devuelve un JSON.

Lo usa: `orquestador.py`.
Usa: `anonimizar.py`, `llm.py` (el mismo proveedor del turno) y `tools/personales.py`.
"""

import asyncio
import json
import logging
import re

from chatbot.anonimizar import CONVERSACION, anonimizar
from chatbot.tools.personales import _TOPE_TARJETAS, mostrar_tarjetas

logger = logging.getLogger(__name__)

# Tope propio del juez. El turno entero tiene 25 s en la vista (`LLM_TIMEOUT_SECONDS`):
# el juez corre al final, así que no debe comerse todo el margen.
_TIMEOUT_SEGUNDOS = 6

_SISTEMA = (
    "Sos un clasificador. Recibís la pregunta de un usuario, la respuesta de un "
    "asistente de cine y una lista de títulos candidatos, cada uno con un número `n`. "
    "Devolvé los `n` de los títulos que el asistente RECOMENDÓ o presentó como "
    "sugerencia para ver. No incluyas los que solo nombra como referencia de lo que "
    "el usuario ya conoce o le gustó, ni palabras sueltas que coinciden con un "
    "título. Si hay un título de película y otro de serie con el mismo nombre, "
    "elegí el que el asistente quiso decir. Máximo 3, en el orden en que aparecen en "
    'la respuesta. Respondé SOLO un JSON, sin texto extra: {"ids": [n, n]}. '
    'Si no recomendó ninguno: {"ids": []}.'
)


def _candidatos(ctx):
    """Los títulos de búsquedas para recomendar, en el orden en que se buscaron.

    `ctx.encontrados` es un `dict`: Python recuerda el orden de inserción (en Java
    sería un `LinkedHashMap`). `ctx.recomendables` es un `set`, sin orden: solo filtra.
    Devuelve `{n: clave}`, con `n` el id de TMDB que ve el modelo.
    """
    return {
        titulo["id_tmdb"]: clave
        for clave, titulo in ctx.encontrados.items()
        if clave in ctx.recomendables
    }


def _mensajes(ctx, pregunta, respuesta):
    lista = [
        {
            "n": titulo["id_tmdb"],
            "titulo": titulo["titulo"],
            "anio": titulo.get("anio"),
            "tipo": titulo["tipo"],
        }
        for clave, titulo in ctx.encontrados.items()
        if clave in ctx.recomendables
    ]
    # Lo que sale de nuestro backend hacia el modelo pasa por `anonimizar`, igual que
    # el historial del chat.
    pedido = (
        f"Pregunta del usuario:\n{anonimizar(pregunta, ctx.usuario, CONVERSACION)}\n\n"
        f"Respuesta del asistente:\n{anonimizar(respuesta, ctx.usuario, CONVERSACION)}\n\n"
        f"Candidatos:\n{json.dumps(lista, ensure_ascii=False)}"
    )
    return [
        {"role": "system", "content": _SISTEMA},
        {"role": "user", "content": pedido},
    ]


def _leer_ids(texto):
    """Los ids del JSON del modelo. Tolera un bloque ```json ... ``` alrededor.

    Busca el primer `{...}` del texto con una expresión regular (`re.DOTALL` hace que
    el punto abarque saltos de línea). Si no hay JSON, o no tiene la forma esperada,
    lanza `ValueError`; quien llama lo captura.
    """
    encontrado = re.search(r"\{.*\}", texto, re.DOTALL)
    if not encontrado:
        raise ValueError("el juez no devolvió un JSON")
    ids = json.loads(encontrado.group()).get("ids")
    if not isinstance(ids, list):
        raise ValueError("el JSON del juez no trae una lista `ids`")
    return ids


async def _preguntar(proveedor, mensajes):
    """Una llamada sin tools: junta los pedazos de texto y devuelve el total."""
    texto = []
    async with asyncio.timeout(_TIMEOUT_SEGUNDOS):
        async for item in proveedor.escribir(mensajes, []):
            if isinstance(item, str):
                texto.append(item)
    return "".join(texto)


async def juzgar_tarjetas(proveedor, ctx, pregunta, respuesta):
    """Suma a `ctx.tarjetas` los títulos que el juez dice que se recomendaron.

    Corre solo si el modelo no mostró tarjetas, hubo una búsqueda para recomendar y
    la respuesta tiene texto. Nunca falla el turno: ante cualquier problema deja las
    tarjetas como estaban y escribe un WARNING.
    """
    candidatos = _candidatos(ctx)
    if ctx.tarjetas or not candidatos or not respuesta.strip():
        return
    try:
        crudo = await _preguntar(proveedor, _mensajes(ctx, pregunta, respuesta))
        ids = _leer_ids(crudo)
    except Exception:
        # `Exception` no incluye `CancelledError`: si el usuario cancela, sigue.
        # (`TimeoutError` sí es una `Exception`, así que también cae acá.)
        logger.warning("El juez de tarjetas falló; sin tarjetas", exc_info=True)
        return
    # Solo ids de los candidatos; `mostrar_tarjetas` ignora repetidos y pone el tope.
    pedidas = [
        {"id_tmdb": candidatos[n][0], "tipo": candidatos[n][1]}
        for n in ids
        # `isinstance(n, int)`: el modelo podría mandar «22» como texto o un `null`.
        if isinstance(n, int) and n in candidatos
    ]
    mostrar_tarjetas(ctx, pedidas[:_TOPE_TARJETAS])
    logger.info("El juez eligió %d tarjetas (de %d ids)", len(ctx.tarjetas), len(ids))
