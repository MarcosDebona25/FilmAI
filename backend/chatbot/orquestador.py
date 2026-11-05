"""El corazón del chatbot: el ida y vuelta entre el modelo y las tools.

Conecta las piezas: arma lo que recibe el modelo, corre las tools que pide y entrega
los eventos de `eventos.py`. No guarda nada: eso, el candado y el tiempo máximo del
turno son de la vista. Mapa completo: `backend/chatbot/README.md`.

Lo usan: la vista del chat (PR 5) y `manage.py chatear`.
Usa: `llm.py`, `prompts.py`, `contexto.py`, `anonimizar.py` y `tools/`.

Lo async es solo este archivo y `llm.py`. Todo lo que toca la base o TMDB es código
común, y se llama con `await en_hilo(...)`.
"""

import json
import logging

from chatbot.anonimizar import CONVERSACION, anonimizar
from chatbot.contexto import armar_perfil
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.llm import Vuelta, crear_proveedor
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.prompts import armar_sistema
from chatbot.puente import en_hilo
from chatbot.tools import ESQUEMAS, ContextoTurno, ejecutar

logger = logging.getLogger(__name__)

# Rondas de tools permitidas. Hay una llamada más, para la respuesta final.
_MAX_VUELTAS_CON_TOOLS = 4
_MENSAJES_DE_HISTORIAL = 10
_TOOL_DE_TARJETAS = "mostrar_tarjetas"
_ROLES = {TipoAutor.USUARIO: "user", TipoAutor.CHATBOT: "assistant"}


def _historial(chat, usuario):
    """Los últimos mensajes, de más viejo a más nuevo y anonimizados."""
    ultimos = Mensaje.objects.filter(chat=chat).order_by("-fecha_hora", "-id")[
        :_MENSAJES_DE_HISTORIAL
    ]
    return [
        {
            "role": _ROLES[mensaje.autor],
            "content": anonimizar(mensaje.texto, usuario, CONVERSACION),
        }
        for mensaje in reversed(ultimos)
    ]


def _preparar(chat, texto, idioma):
    """Todo lo que el turno lee de la base, en un solo viaje al hilo.

    Vuelve a leer el chat con su usuario: pedir `chat.usuario` desde código async
    consultaría la base sin pasar por el puente, y Django lo prohíbe.
    """
    chat = Chat.objects.select_related("usuario").get(pk=chat.pk)
    usuario = chat.usuario
    sistema = armar_sistema(
        armar_perfil(usuario), chat.contexto.get("ya_recomendados", []), idioma
    )
    mensajes = [
        {"role": "system", "content": sistema},
        *_historial(chat, usuario),
        {"role": "user", "content": anonimizar(texto, usuario, CONVERSACION)},
    ]
    return ContextoTurno.para(usuario, idioma), mensajes


def _argumentos_de(llamada):
    """Los argumentos como diccionario, o `None` si el modelo los mandó mal."""
    try:
        argumentos = json.loads(llamada.argumentos or "{}")
    except ValueError:
        return None
    return argumentos if isinstance(argumentos, dict) else None


def _correr_tools(ctx, llamadas):
    """Corre las tools de una vuelta, en orden, y arma los mensajes de resultado."""
    resultados = []
    for llamada in llamadas:
        argumentos = _argumentos_de(llamada)
        if argumentos is None:
            # Pasa si el modelo se quedó sin tokens en medio de los argumentos.
            resultado = {"error": "tool_failed"}
        else:
            resultado = ejecutar(ctx, llamada.nombre, argumentos)
        resultados.append(
            {
                "role": "tool",
                "tool_call_id": llamada.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            }
        )
    return resultados


def _mensaje_del_asistente(vuelta):
    """Lo que dijo el modelo en esta vuelta, en el formato que espera de vuelta."""
    mensaje = {
        "role": "assistant",
        "content": vuelta.texto,
        "tool_calls": [
            {
                "id": llamada.id,
                "type": "function",
                "function": {"name": llamada.nombre, "arguments": llamada.argumentos},
            }
            for llamada in vuelta.llamadas
        ],
    }
    # Con thinking, DeepSeek pide que el razonamiento vuelva en las rondas de tools.
    if vuelta.razonamiento:
        mensaje["reasoning_content"] = vuelta.razonamiento
    return mensaje


def _solo_tarjetas(vuelta):
    return all(llamada.nombre == _TOOL_DE_TARJETAS for llamada in vuelta.llamadas)


async def responder(chat, texto, idioma, *, proveedor=None):
    """Responde un mensaje, entregando eventos a medida que ocurren.

    Cumple las reglas de `eventos.py`. Es un generador async: cada `yield` le pasa
    un evento a la vista y sigue desde ahí cuando la vista pide el próximo.
    `proveedor` es para los tests; sin él, se usa el configurado.
    """
    try:
        proveedor = proveedor or crear_proveedor()
    except Exception as error:
        # Pasa con un `LLM_PROVIDER` que no existe. La causa queda en el log.
        logger.exception("El proveedor está mal configurado")
        raise ErrorDelTurno("El proveedor está mal configurado") from error
    ctx, mensajes = await en_hilo(_preparar, chat, texto, idioma)
    partes = []

    for numero_de_vuelta in range(_MAX_VUELTAS_CON_TOOLS + 1):
        vuelta = None
        # Sin esto, el texto de dos vueltas saldría pegado: «…despacio.¿Querés…».
        separar = bool(partes)
        try:
            async for item in proveedor.escribir(mensajes, ESQUEMAS):
                if isinstance(item, Vuelta):
                    vuelta = item
                    continue
                if separar:
                    separar = False
                    partes.append("\n\n")
                    yield Texto("\n\n")
                partes.append(item)
                yield Texto(item)
        except Exception as error:
            # `Exception` no incluye `CancelledError`: si el usuario cancela, la
            # cancelación tiene que llegar a la vista.
            logger.exception("El proveedor falló")
            raise ErrorDelTurno("El proveedor falló") from error

        if not vuelta.llamadas:
            break
        if numero_de_vuelta == _MAX_VUELTAS_CON_TOOLS:
            raise ErrorDelTurno("Se pasó del tope de vueltas con tools")

        if not _solo_tarjetas(vuelta):
            yield Estado("searching")
        resultados = await en_hilo(_correr_tools, ctx, vuelta.llamadas)
        if vuelta.texto and _solo_tarjetas(vuelta):
            # Ya respondió y eligió tarjetas: otra llamada solo la repetiría.
            break
        mensajes.append(_mensaje_del_asistente(vuelta))
        mensajes.extend(resultados)

    respuesta = "".join(partes)
    if not respuesta.strip():
        raise ErrorDelTurno("El modelo no escribió nada")
    yield Resultado(respuesta, ctx.tarjetas)
