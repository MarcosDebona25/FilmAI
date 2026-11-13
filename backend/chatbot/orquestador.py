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
import time

from django.conf import settings
from django.utils import timezone

from chatbot.anonimizar import CONVERSACION, anonimizar
from chatbot.contexto import armar_perfil
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.idioma import detectar_idioma
from chatbot.llm import Vuelta, crear_proveedor
from chatbot.marcadores import FiltroDeMarcadores, recomienda_sin_buscar
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.prompts import armar_sistema
from chatbot.puente import en_hilo
from chatbot.tools import ESQUEMAS, FUNCIONES, ContextoTurno, ejecutar

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
# La búsqueda forzada (ver `responder`) solo se intenta si el turno lleva menos de
# esta parte del tiempo máximo de la vista (`LLM_TIMEOUT_SECONDS`): otra llamada al
# modelo más las tools tiene que entrar en lo que queda.
_FRACCION_PARA_REINTENTAR = 0.4
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


def _ahora():
    """El reloj del turno. Aparte para poder fijarlo en los tests (como un `Clock`)."""
    return time.monotonic()


def _tarjetas_del_ultimo_mensaje(chat):
    """Las tarjetas del último mensaje del asistente, listas para ser candidatas.

    Salen de `Mensaje.tarjetas` (JSON guardado), así que se valida cada una: una
    mal armada se ignora en vez de romper el turno. Es lo que permite «¿y las
    tarjetas?» sin volver a buscar: esos títulos entran al turno con su `ref`.
    """
    ultimo = (
        Mensaje.objects.filter(chat=chat, autor=TipoAutor.CHATBOT)
        .order_by("-fecha_hora", "-id")
        .first()
    )
    validas = []
    for tarjeta in ultimo.tarjetas if ultimo else []:
        if (
            isinstance(tarjeta, dict)
            and isinstance(tarjeta.get("id_tmdb"), int)
            and tarjeta.get("tipo") in ("movie", "tv")
            and isinstance(tarjeta.get("titulo"), str)
            and tarjeta["titulo"].strip()
        ):
            validas.append(tarjeta)
    return validas


def _preparar(chat, texto, idioma):
    """Todo lo que el turno lee de la base, en un solo viaje al hilo.

    Vuelve a leer el chat con su usuario: pedir `chat.usuario` desde código async
    consultaría la base sin pasar por el puente, y Django lo prohíbe.
    """
    chat = Chat.objects.select_related("usuario").get(pk=chat.pk)
    usuario = chat.usuario
    ctx = ContextoTurno.para(usuario, idioma)
    # Las tarjetas del último mensaje son los primeros candidatos del turno (`ref`
    # 1, 2, …): las búsquedas de este turno siguen la numeración desde ahí.
    for tarjeta in _tarjetas_del_ultimo_mensaje(chat):
        # Las guardadas antes del 07/11/2026 no traen `nota_tmdb`: el contrato del
        # stream la pide siempre (puede ser `null`).
        ctx.encontrados[(tarjeta["id_tmdb"], tarjeta["tipo"])] = {
            "id_tmdb": tarjeta["id_tmdb"],
            "tipo": tarjeta["tipo"],
            "titulo": tarjeta["titulo"],
            "poster": tarjeta.get("poster"),
            "anio": tarjeta.get("anio"),
            "nota_tmdb": tarjeta.get("nota_tmdb"),
        }
    # La prosa sigue al idioma del mensaje; las tools y las tarjetas, al del turno.
    sistema = armar_sistema(
        armar_perfil(usuario),
        chat.contexto.get("ya_recomendados", []),
        detectar_idioma(texto) or idioma,
        hoy=timezone.localdate(),
        ultimas=list(ctx.candidatos().items()),
    )
    mensajes = [
        {"role": "system", "content": sistema},
        *_historial(chat, usuario),
        {"role": "user", "content": anonimizar(texto, usuario, CONVERSACION)},
    ]
    return ctx, mensajes


def _argumentos_de(llamada):
    """Los argumentos como diccionario, o `None` si el modelo los mandó mal."""
    try:
        argumentos = json.loads(llamada.argumentos or "{}")
    except ValueError:
        return None
    return argumentos if isinstance(argumentos, dict) else None


def _cantidad_de(resultado):
    """Cuántos resultados trajo una tool, para el log: un número o `"error"`.

    Las búsquedas devuelven `{"resultados": [...]}`: se cuenta la lista. Una tool que
    devuelve un solo dato (`detalle`) cuenta como 1. Solo se mira el tamaño, nunca el
    contenido.
    """
    if "error" in resultado:
        return "error"
    if isinstance(resultado.get("resultados"), list):
        return len(resultado["resultados"])
    return 1


def _correr_tools(ctx, llamadas):
    """Corre las tools de una vuelta, en orden.

    Devuelve dos listas: los mensajes de resultado para el modelo y, para el log,
    un `nombre(cantidad)` por tool. Una función puede devolver varios valores en
    Python (una tupla); en Java habría que armar una clase chica para eso.
    """
    resultados, resumen = [], []
    for llamada in llamadas:
        argumentos = _argumentos_de(llamada)
        if argumentos is None:
            # Pasa si el modelo se quedó sin tokens en medio de los argumentos.
            resultado = {"error": "tool_failed"}
        else:
            resultado = ejecutar(ctx, llamada.nombre, argumentos)
        # El nombre lo escribe el modelo: solo se loguea si es una tool real. Si no,
        # un nombre con saltos de línea podría forjar líneas falsas en el log.
        nombre = llamada.nombre if llamada.nombre in FUNCIONES else "desconocida"
        resumen.append(f"{nombre}({_cantidad_de(resultado)})")
        resultados.append(
            {
                "role": "tool",
                "tool_call_id": llamada.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            }
        )
    return resultados, resumen


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


async def _sacar(filtro, partes, pedazos):
    """Pasa los pedazos por el filtro de marcadores y entrega lo que ya se puede mostrar.

    Lo que sale (con los `[[n]]` ya cambiados por el título) se suma a `partes`, que
    es el texto final del turno, y se entrega como `Texto`. Un pedazo puede no
    entregar nada: el filtro retiene unos pocos caracteres que podrían ser el
    comienzo de un marcador. Es un generador async: el que lo llama lo recorre con
    `async for` y reenvía cada evento con su propio `yield`.
    """
    for pedazo in pedazos:
        saliente = filtro.alimentar(pedazo)
        if saliente:
            partes.append(saliente)
            yield Texto(saliente)


def _soltar(filtro, partes):
    """Lo que el filtro retenía al terminar un texto, como `Texto` (o `None` si nada).

    `cerrar()` ya devuelve texto final: no vuelve a pasar por `alimentar()`.
    """
    resto = filtro.cerrar()
    if not resto:
        return None
    partes.append(resto)
    return Texto(resto)


async def _ultima_llamada(proveedor, mensajes, partes, motivo, filtro):
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
            saliente = filtro.alimentar(item)
            if not saliente:
                continue
            if separar:
                partes.append("\n\n")
                yield Texto("\n\n")
                separar = False
            escrito = escrito or bool(saliente.strip())
            partes.append(saliente)
            yield Texto(saliente)
    except Exception as error:
        logger.exception("La última llamada falló")
        raise ErrorDelTurno("La última llamada falló") from error
    if resto := _soltar(filtro, partes):
        escrito = escrito or bool(resto.delta.strip())
        yield resto
    if not escrito:
        raise ErrorDelTurno("La última llamada no escribió nada")


def _registrar_turno(tools_pedidas, vueltas, ultima_sin_tools, ctx, filtro, reintento):
    """Una línea de INFO al cerrar el turno: cómo fue, no de qué se habló.

    Sirve para entender, mirando el log, por qué el modelo hizo lo que hizo (qué
    tools pidió y con cuántos resultados, si se quedó sin vueltas, cuántos marcadores
    `[[n]]` usó y cuántos no correspondían a ningún título, cuántas negritas escribió
    por su cuenta, si hubo búsqueda forzada). A propósito no lleva la pregunta ni la respuesta: son datos
    personales y los logs se guardan.
    """
    logger.info(
        "Turno: tools=%s vueltas=%d ultima_sin_tools=%s tarjetas=%s "
        "marcadores_validos=%d marcadores_invalidos=%d negritas_propias=%d "
        "reintento_forzado=%s",
        ",".join(tools_pedidas) or "ninguna",
        vueltas,
        "si" if ultima_sin_tools else "no",
        "marcadores" if ctx.tarjetas else "ninguna",
        filtro.validos,
        filtro.invalidos,
        filtro.negritas,
        "si" if reintento else "no",
    )


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
    # Cambia los `[[n]]` del modelo por el título y suma las tarjetas (marcadores.py).
    filtro = FiltroDeMarcadores(ctx)
    # Para la línea de diagnóstico del final (ver `_registrar_turno`).
    tools_pedidas, vueltas, ultima_sin_tools = [], 0, False
    # Búsqueda forzada: si el modelo recomienda sin haber buscado, la llamada se repite
    # una sola vez con `tool_choice="required"`. `reintento` dice que ya se decidió
    # hacerlo; `forzar_ahora`, que la próxima llamada es esa; `descartado`, el texto
    # del primer intento, por si la llamada forzada falla.
    inicio = _ahora()
    reintento = forzar_ahora = False
    descartado = None

    for _ in range(_MAX_VUELTAS_CON_TOOLS + 1):
        vueltas += 1
        vuelta = None
        # Sin esto, el texto de dos vueltas saldría pegado: «…despacio.¿Querés…».
        separar = bool(partes)
        # Mientras ninguna tool corrió, la vuelta se retiene entera: si resulta que
        # el modelo recomendó sin buscar, hay que poder descartarla sin que el
        # usuario haya leído nada. Después de una búsqueda se transmite en vivo.
        retener = not tools_pedidas
        # Lo que todavía no salió al front, por si resulta ser un preámbulo.
        retenido, en_vivo = [], False
        # `**{...}` abre el diccionario como argumentos con nombre; vacío, no pasa
        # ninguno (así un proveedor sin `tool_choice` sigue funcionando).
        extra = {"tool_choice": "required"} if forzar_ahora else {}
        forzar_ahora = False
        try:
            async for item in proveedor.escribir(mensajes, ESQUEMAS, **extra):
                if isinstance(item, Vuelta):
                    vuelta = item
                    continue
                retenido.append(item)
                if retener or (
                    not en_vivo and len("".join(retenido)) <= _LARGO_DE_PREAMBULO
                ):
                    continue
                en_vivo = True
                async for evento in _sacar(
                    filtro, partes, _con_separador(retenido, separar)
                ):
                    yield evento
                separar, retenido = False, []
        except Exception as error:
            # `Exception` no incluye `CancelledError`: si el usuario cancela, la
            # cancelación tiene que llegar a la vista.
            logger.exception("El proveedor falló")
            if not (extra and descartado):
                raise ErrorDelTurno("El proveedor falló") from error
            # La llamada forzada falló: se muestra el primer intento (sin los
            # marcadores inválidos), que es mejor que un error.
            retenido, vuelta = descartado, Vuelta(texto="".join(descartado))

        texto_retenido = "".join(retenido)
        if (
            retener
            and not vuelta.llamadas
            and not reintento
            and recomienda_sin_buscar(texto_retenido, ctx.candidatos())
            and _ahora() - inicio
            < settings.LLM_TIMEOUT_SECONDS * _FRACCION_PARA_REINTENTAR
        ):
            logger.warning("Recomendó sin buscar: se repite la llamada con tool_choice")
            reintento = forzar_ahora = True
            descartado = retenido
            continue

        # Texto corto y una búsqueda: era un «ya busco», y la respuesta viene después.
        # Se descarta solo del front; el modelo lo sigue viendo en `mensajes`.
        es_preambulo = vuelta.llamadas and len(texto_retenido) <= _LARGO_DE_PREAMBULO
        if retenido and not es_preambulo:
            async for evento in _sacar(
                filtro, partes, _con_separador(retenido, separar)
            ):
                yield evento
        # Lo que el filtro retenía por si era un marcador: la vuelta terminó.
        if resto := _soltar(filtro, partes):
            yield resto

        if not vuelta.llamadas:
            break

        yield Estado("searching")
        resultados, resumen = await en_hilo(_correr_tools, ctx, vuelta.llamadas)
        tools_pedidas.extend(resumen)
        mensajes.append(_mensaje_del_asistente(vuelta))
        mensajes.extend(resultados)
    else:
        # `for ... else`: el `else` corre solo si el ciclo terminó sin `break` (en
        # Java no hay equivalente). Acá: la última vuelta permitida todavía pedía
        # tools, así que el modelo no llegó a responder.
        motivo = "se pasó del tope de vueltas con tools"
        ultima_sin_tools = True
        async for evento in _ultima_llamada(
            proveedor, mensajes, partes, motivo, filtro
        ):
            yield evento

    if not "".join(partes).strip():
        # El turno terminó sin una sola palabra para el usuario.
        ultima_sin_tools = True
        async for evento in _ultima_llamada(
            proveedor, mensajes, partes, "el modelo no escribió nada", filtro
        ):
            yield evento

    respuesta = "".join(partes)
    _registrar_turno(tools_pedidas, vueltas, ultima_sin_tools, ctx, filtro, reintento)
    yield Resultado(respuesta, ctx.tarjetas)
