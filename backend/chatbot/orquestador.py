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
import re
import unicodedata

from chatbot.anonimizar import CONVERSACION, anonimizar
from chatbot.contexto import armar_perfil
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.idioma import detectar_idioma
from chatbot.llm import Vuelta, crear_proveedor
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.prompts import armar_sistema
from chatbot.puente import en_hilo
from chatbot.tools import ESQUEMAS, ContextoTurno, ejecutar
from chatbot.tools.personales import mostrar_tarjetas

logger = logging.getLogger(__name__)

# Rondas de tools permitidas. Hay una llamada más, para la respuesta final.
_MAX_VUELTAS_CON_TOOLS = 4
_MENSAJES_DE_HISTORIAL = 10
# Cuánto texto de una vuelta se retiene antes de mandarlo. Un preámbulo («I'll
# look that up.») es corto: si la vuelta termina antes de este largo y pidió
# buscar, se descarta. Una respuesta de verdad lo pasa enseguida y sigue en vivo.
_LARGO_DE_PREAMBULO = 200
_TOOL_DE_TARJETAS = "mostrar_tarjetas"
# Un título de hasta este largo («Up», «Her», «It») cuenta solo en negrita Markdown
# (**Her**): suelto, «Her latest film…» o «It is…» al empezar una oración serían
# tarjetas. El modelo escribe los títulos en negrita, así que no se pierde nada.
_LARGO_DE_TITULO_CORTO = 3
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


def _plegar_letra(letra):
    """Una letra en minúscula y sin acento: «Á» → «a». Siempre devuelve una sola.

    `NFKD` separa la letra de su tilde («á» pasa a «a» más la tilde sola) y
    `combining` reconoce la tilde suelta para descartarla. Si el resultado no es una
    sola letra («ß» da «ss»), queda la original en minúscula: así el texto plegado
    tiene el mismo largo y las posiciones coinciden con las del original.
    """
    base = "".join(
        c for c in unicodedata.normalize("NFKD", letra) if not unicodedata.combining(c)
    ).lower()
    return base if len(base) == 1 else letra.lower()


def _plegar(texto):
    return "".join(_plegar_letra(letra) for letra in texto)


def _tarjetas_nombradas(respuesta, ctx):
    """Los títulos para recomendar que la respuesta nombra, en orden de aparición.

    Es la red para cuando el modelo recomienda en el texto pero no llama a
    `mostrar_tarjetas` (en el set dorado del 08/11/2026, 5 de 8 veces). Solo
    cuentan los títulos de `ctx.recomendables`: lo que devolvió una búsqueda para
    recomendar en este turno, que ya viene sin lo visto. Devuelve los pedidos en
    el formato de `mostrar_tarjetas`, que se encarga del tope de 3 y los repetidos.
    """
    plegada = _plegar(respuesta)
    # Cada título con todas sus apariciones, como pares (inicio, fin).
    apariciones = {}
    for clave in ctx.recomendables:
        nombre = (ctx.encontrados[clave].get("titulo") or "").strip()
        if not nombre:
            continue
        if len(nombre) <= _LARGO_DE_TITULO_CORTO:
            # Escrito igual y entre `**`: `\*` es un asterisco literal, porque en
            # una expresión regular `*` solo significa «repetir». El tramo es el
            # del título, sin los asteriscos.
            patron, texto, margen = rf"\*\*{re.escape(nombre)}\*\*", respuesta, 2
        else:
            # `(?<!\w)` y `(?!\w)`: que no haya una letra pegada antes ni después.
            # Así «Moon» no aparece dentro de «Moonlight». `re.escape` hace que los
            # signos del título («Se7en», «Alien³», «¿Qué pasó ayer?») se busquen
            # tal cual.
            patron = rf"(?<!\w){re.escape(_plegar(nombre))}(?!\w)"
            texto, margen = plegada, 0
        # `finditer` recorre todas las apariciones, no solo la primera.
        tramos = [
            (m.start() + margen, m.end() - margen) for m in re.finditer(patron, texto)
        ]
        if tramos:
            apariciones[clave] = tramos

    # Gana el más largo: una aparición que cae dentro de la de otro título más
    # largo no cuenta. «Probá Dune: Part Two» nombra a esa, no a «Dune».
    todos = [tramo for tramos in apariciones.values() for tramo in tramos]
    nombrados = []
    for clave, tramos in apariciones.items():
        sueltos = [
            (inicio, fin)
            for inicio, fin in tramos
            if not any(
                otro_inicio <= inicio
                and fin <= otro_fin
                and fin - inicio < otro_fin - otro_inicio
                for otro_inicio, otro_fin in todos
            )
        ]
        if sueltos:
            nombrados.append((min(sueltos)[0], clave))
    # Ordena por posición en el texto; la clave desempata siempre igual.
    nombrados.sort()
    return [{"id_tmdb": id_tmdb, "tipo": tipo} for _, (id_tmdb, tipo) in nombrados]


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

    for numero_de_vuelta in range(_MAX_VUELTAS_CON_TOOLS + 1):
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
        if numero_de_vuelta == _MAX_VUELTAS_CON_TOOLS and not cierra_el_turno:
            raise ErrorDelTurno("Se pasó del tope de vueltas con tools")

        if not _solo_tarjetas(vuelta):
            yield Estado("searching")
        resultados = await en_hilo(_correr_tools, ctx, vuelta.llamadas)
        if cierra_el_turno:
            break
        mensajes.append(_mensaje_del_asistente(vuelta))
        mensajes.extend(resultados)

    respuesta = "".join(partes)
    if not respuesta.strip():
        raise ErrorDelTurno("El modelo no escribió nada")
    if not ctx.tarjetas:
        # Recomendó en el texto y no mostró tarjetas: se arman con lo que nombró.
        # `mostrar_tarjetas` no toca la base, así que se llama directo, sin el
        # puente. Si nombró títulos que ninguna búsqueda devolvió, no pasa nada.
        mostrar_tarjetas(ctx, _tarjetas_nombradas(respuesta, ctx))
        if ctx.tarjetas:
            logger.info("Tarjetas armadas por el orquestador: %d", len(ctx.tarjetas))
    yield Resultado(respuesta, ctx.tarjetas)
