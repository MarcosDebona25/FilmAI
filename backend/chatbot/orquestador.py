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
from chatbot.idioma import detectar_idioma
from chatbot.juez import juzgar_tarjetas
from chatbot.llm import Vuelta, crear_proveedor
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.prompts import armar_sistema
from chatbot.puente import en_hilo
from chatbot.tools import ESQUEMAS, ContextoTurno, ejecutar

logger = logging.getLogger(__name__)

# Rondas de tools permitidas. Hay una llamada más, para la respuesta final.
_MAX_VUELTAS_CON_TOOLS = 4
# Lo que se le dice al modelo en la última llamada, que va sin tools (ver
# `_ultima_llamada`). Va como mensaje `system`: es una orden del backend, no algo
# que haya dicho el usuario.
_AVISO_DE_ULTIMA_LLAMADA = (
    "Ya no podés buscar. Respondé al usuario con lo que ya encontraste, sin pedir "
    "más herramientas."
)
_MENSAJES_DE_HISTORIAL = 10
# Cuánto texto de una vuelta se retiene antes de mandarlo. Un preámbulo («I'll
# look that up.») es corto: si la vuelta termina antes de este largo y pidió
# buscar, se descarta. Una respuesta de verdad lo pasa enseguida y sigue en vivo.
_LARGO_DE_PREAMBULO = 200
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
    # La prosa sigue al idioma del mensaje; las tools y las tarjetas, al del turno.
    sistema = armar_sistema(
        armar_perfil(usuario),
        chat.contexto.get("ya_recomendados", []),
        detectar_idioma(texto) or idioma,
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


def _con_separador(pedazos, separar):
    """Los pedazos de texto, con «\\n\\n» adelante si hay texto de otra vuelta."""
    return ["\n\n", *pedazos] if separar else list(pedazos)


def _solo_tarjetas(vuelta):
    return all(llamada.nombre == _TOOL_DE_TARJETAS for llamada in vuelta.llamadas)


def _con_tarjetas(vuelta):
    return any(llamada.nombre == _TOOL_DE_TARJETAS for llamada in vuelta.llamadas)


async def _ultima_llamada(proveedor, mensajes, partes, motivo):
    """Una llamada más, sin tools, para que el modelo responda con lo que ya tiene.

    Antes, pasarse del tope de vueltas o terminar sin texto era un error para el
    usuario (5 de 32 turnos del set dorado, 12/11/2026). Ahora se le pide al modelo
    que cierre: como no recibe tools, solo puede escribir. Si esta llamada también
    falla o vuelve vacía, ahí sí es un `ErrorDelTurno`.

    Entrega el texto en vivo y lo suma a `partes`. Si ya había texto de otras
    vueltas, lo nuevo va separado con un «\n\n» y lo anterior no se repite.
    """
    logger.warning("Última llamada sin tools: %s", motivo)
    mensajes.append({"role": "system", "content": _AVISO_DE_ULTIMA_LLAMADA})
    separar = bool("".join(partes).strip())
    escrito = False
    try:
        async for item in proveedor.escribir(mensajes, []):
            # Si el modelo pidiera tools igual, la `Vuelta` final se ignora: solo
            # importa el texto que salió.
            if isinstance(item, Vuelta) or not item:
                continue
            if separar:
                partes.append("\n\n")
                yield Texto("\n\n")
                separar = False
            escrito = escrito or bool(item.strip())
            partes.append(item)
            yield Texto(item)
    except Exception as error:
        logger.exception("La última llamada falló")
        raise ErrorDelTurno("La última llamada falló") from error
    if not escrito:
        raise ErrorDelTurno("La última llamada no escribió nada")


async def responder(chat, texto, idioma, *, proveedor=None):
    """Responde un mensaje, entregando eventos a medida que ocurren.

    Cumple las reglas de `eventos.py`. Es un generador async: cada `yield` le pasa
    un evento a la vista y sigue desde ahí cuando la vista pide el próximo.
    `proveedor` es para los tests; sin él, se usa el configurado.
    """
    try:
        proveedor = proveedor or crear_proveedor()
        ctx, mensajes = await en_hilo(_preparar, chat, texto, idioma)
    except Exception as error:
        # Un `LLM_PROVIDER` que no existe, la base caída o un `contexto` mal armado.
        logger.exception("No se pudo preparar el turno")
        raise ErrorDelTurno("No se pudo preparar el turno") from error
    partes = []

    for _ in range(_MAX_VUELTAS_CON_TOOLS + 1):
        vuelta = None
        # Sin esto, el texto de dos vueltas saldría pegado: «…despacio.¿Querés…».
        separar = bool(partes)
        # Lo que todavía no salió al front, por si resulta ser un preámbulo.
        retenido, en_vivo = [], False
        try:
            async for item in proveedor.escribir(mensajes, ESQUEMAS):
                if isinstance(item, Vuelta):
                    vuelta = item
                    continue
                retenido.append(item)
                if not en_vivo and len("".join(retenido)) <= _LARGO_DE_PREAMBULO:
                    continue
                en_vivo = True
                for pedazo in _con_separador(retenido, separar):
                    partes.append(pedazo)
                    yield Texto(pedazo)
                separar, retenido = False, []
        except Exception as error:
            # `Exception` no incluye `CancelledError`: si el usuario cancela, la
            # cancelación tiene que llegar a la vista.
            logger.exception("El proveedor falló")
            raise ErrorDelTurno("El proveedor falló") from error

        # Texto corto y una búsqueda: era un «ya busco», y la respuesta viene después.
        # Se descarta solo del front; el modelo lo sigue viendo en `mensajes`. Si la
        # vuelta también muestra tarjetas, el texto las acompaña y no se descarta.
        es_preambulo = vuelta.llamadas and not _con_tarjetas(vuelta)
        if retenido and not es_preambulo:
            for pedazo in _con_separador(retenido, separar):
                partes.append(pedazo)
                yield Texto(pedazo)

        if not vuelta.llamadas:
            break
        # Ya respondió y eligió tarjetas: otra llamada solo la repetiría. Por eso
        # esta vuelta cierra el turno, aunque sea la última permitida.
        cierra_el_turno = bool(vuelta.texto) and _solo_tarjetas(vuelta)

        if not _solo_tarjetas(vuelta):
            yield Estado("searching")
        resultados = await en_hilo(_correr_tools, ctx, vuelta.llamadas)
        if cierra_el_turno:
            break
        mensajes.append(_mensaje_del_asistente(vuelta))
        mensajes.extend(resultados)
    else:
        # `for ... else`: el `else` corre solo si el ciclo terminó sin `break` (en
        # Java no hay equivalente). Acá: la última vuelta permitida todavía pedía
        # tools, así que el modelo no llegó a responder.
        motivo = "se pasó del tope de vueltas con tools"
        async for evento in _ultima_llamada(proveedor, mensajes, partes, motivo):
            yield evento

    if not "".join(partes).strip():
        # El turno terminó sin una sola palabra para el usuario.
        async for evento in _ultima_llamada(
            proveedor, mensajes, partes, "el modelo no escribió nada"
        ):
            yield evento

    respuesta = "".join(partes)
    # Si recomendó en el texto sin mostrar tarjetas, el juez decide cuáles (ver
    # `juez.py`). Solo corre si hace falta y nunca rompe el turno.
    await juzgar_tarjetas(proveedor, ctx, texto, respuesta)
    yield Resultado(respuesta, ctx.tarjetas)
