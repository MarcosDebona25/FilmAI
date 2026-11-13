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

from django.utils import timezone

from chatbot.anonimizar import APOSTROFOS, CONVERSACION, anonimizar
from chatbot.contexto import armar_perfil
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.idioma import detectar_idioma
from chatbot.llm import Vuelta, crear_proveedor
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.prompts import armar_sistema
from chatbot.puente import en_hilo
from chatbot.tools import ESQUEMAS, FUNCIONES, ContextoTurno, ejecutar
from chatbot.tools.personales import mostrar_tarjetas

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
# Un título de hasta este largo («Up», «Her», «It») es una palabra común: en la
# pregunta del usuario solo cuenta escrito igual (ver `_lo_escribio_el_usuario`).
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
        hoy=timezone.localdate(),
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


def _cantidad_de(resultado):
    """Cuántos resultados trajo una tool, para el log: un número o `"error"`.

    Las búsquedas devuelven `{"resultados": [...]}` y `mostrar_tarjetas`
    `{"tarjetas": [...]}`: se cuenta la lista. Una tool que devuelve un solo dato
    (`detalle`) cuenta como 1. Solo se mira el tamaño, nunca el contenido.
    """
    if "error" in resultado:
        return "error"
    for clave in ("resultados", "tarjetas"):
        if isinstance(resultado.get(clave), list):
            return len(resultado[clave])
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


def _solo_tarjetas(vuelta):
    return all(llamada.nombre == _TOOL_DE_TARJETAS for llamada in vuelta.llamadas)


def _con_tarjetas(vuelta):
    return any(llamada.nombre == _TOOL_DE_TARJETAS for llamada in vuelta.llamadas)


def _plegar_letra(letra):
    """Una letra en minúscula y sin acento: «Á» → «a». Siempre devuelve una sola.

    `NFKD` separa la letra de su tilde («á» pasa a «a» más la tilde sola) y
    `combining` reconoce la tilde suelta para descartarla. Si el resultado no es una
    sola letra («ß» da «ss»), queda la original en minúscula: así el texto plegado
    tiene el mismo largo y las posiciones coinciden con las del original. Los
    apóstrofos curvos pasan a ser el recto, también de a una letra.
    """
    if letra in APOSTROFOS:
        return APOSTROFOS[letra]
    base = "".join(
        c for c in unicodedata.normalize("NFKD", letra) if not unicodedata.combining(c)
    ).lower()
    return base if len(base) == 1 else letra.lower()


def _plegar(texto):
    """El texto en minúscula, sin acentos y con un solo tipo de apóstrofo.

    Antes lo pasa a `NFC`, que junta cada letra con su tilde suelta: «e» + U+0301
    pasa a ser «é». Un texto que viene «descompuesto» (en NFD) se ve igual que uno
    «compuesto», pero son otros caracteres, y sin esto la tilde quedaba en el medio
    y el título no coincidía. Desde acá, las posiciones son las del texto en NFC.
    """
    return "".join(
        _plegar_letra(letra) for letra in unicodedata.normalize("NFC", texto)
    )


# Palabras que dicen qué es un título, ya plegadas (sin acento ni mayúscula). En
# español y en inglés. `\b` es un borde de palabra: «tv» no cuenta dentro de «atv».
_PISTAS_DE_TIPO = {
    "movie": re.compile(r"\b(?:pelicula|peliculas|movie|movies|film|films|filme)\b"),
    "tv": re.compile(
        r"\b(?:serie|series|miniserie|miniseries|show|shows|tv|temporada|season)\b"
    ),
}
# Cuántas letras a cada lado de la mención se miran en busca de una pista.
_RADIO_DE_PISTAS = 60


def _tipo_segun_pistas(plegada, inicio, fin, pregunta):
    """`"movie"`, `"tv"` o `None` si el contexto no se decide por ninguno.

    Primero manda lo que dice el modelo cerca de la mención («la serie **Fargo**»):
    gana la pista más cercana. Si no hay ninguna (o están a igual distancia), se
    cuentan las de la pregunta del usuario. `plegada` y `pregunta` ya vienen plegadas.
    """
    cercanas = []
    for tipo, patron in _PISTAS_DE_TIPO.items():
        distancias = [
            # Cuántas letras separan la pista de la mención (0 si se tocan).
            max(0, m.start() - fin, inicio - m.end())
            for m in patron.finditer(
                plegada, max(0, inicio - _RADIO_DE_PISTAS), fin + _RADIO_DE_PISTAS
            )
        ]
        if distancias:
            cercanas.append((min(distancias), tipo))
    # Con dos tipos, gana el de la pista más cercana; a igual distancia no deciden.
    cercanas.sort()
    if len(cercanas) == 1 or (len(cercanas) == 2 and cercanas[0][0] < cercanas[1][0]):
        return cercanas[0][1]

    cuenta = {t: len(p.findall(pregunta)) for t, p in _PISTAS_DE_TIPO.items()}
    if cuenta["movie"] != cuenta["tv"]:
        return max(cuenta, key=cuenta.get)
    return None


def _lo_escribio_el_usuario(nombre, pregunta):
    """¿El usuario escribió este título en su pregunta?

    Un título largo cuenta con otra mayúscula o acentos y solo como palabra entera:
    «Moon» no está en «Moonlight». Uno corto («It», «Her», «Up») es una palabra común
    («is it scary?»): solo cuenta escrito igual, con su mayúscula. Los bordes del patrón piden que no
    haya una letra pegada antes ni después.
    """
    if len(nombre) <= _LARGO_DE_TITULO_CORTO:
        texto = unicodedata.normalize("NFC", pregunta)
        patron = rf"(?<!\w){re.escape(unicodedata.normalize('NFC', nombre))}(?!\w)"
    else:
        texto, patron = _plegar(pregunta), rf"(?<!\w){re.escape(_plegar(nombre))}(?!\w)"
    return re.search(patron, texto) is not None


def _tarjetas_nombradas(respuesta, ctx, pregunta=""):
    """Los títulos para recomendar que la respuesta nombra, en orden de aparición.

    Es la red para cuando el modelo recomienda en el texto pero no llama a
    `mostrar_tarjetas` (en el set dorado del 08/11/2026, 5 de 8 veces). Solo
    cuentan los títulos de `ctx.recomendables`: lo que devolvió una búsqueda para
    recomendar en este turno, que ya viene sin lo visto. Devuelve los pedidos en
    el formato de `mostrar_tarjetas`, que se encarga del tope de 3 y los repetidos.

    Reglas (12/11/2026):
    - Solo cuenta un título escrito en **negrita**: así se marca una recomendación,
      y un título suelto en la prosa puede ser otra cosa.
    - Uno que el usuario ya escribió en su `pregunta` no arma tarjeta: lo nombró de
      referencia («algo como Arrival»).
    - Si una película y una serie se llaman igual, se elige por las pistas del
      contexto (`_tipo_segun_pistas`); sin pistas, la primera que trajo la búsqueda.
      Una sola tarjeta por mención.
    """
    plegada = _plegar(respuesta)
    pregunta_plegada = _plegar(pregunta)
    # Cada mención en el texto, como (inicio, fin), con los títulos que se llaman así.
    menciones = {}
    # `ctx.encontrados` es un `dict`: Python recuerda el orden en que se insertaron las
    # claves, así que esto recorre los títulos en el orden de las búsquedas.
    # `ctx.recomendables` es un `set` y no tiene orden: solo se usa para filtrar.
    for clave, titulo in ctx.encontrados.items():
        nombre = (titulo.get("titulo") or "").strip()
        if (
            clave not in ctx.recomendables
            or not nombre
            or _lo_escribio_el_usuario(nombre, pregunta)
        ):
            continue
        # `\*` es un asterisco literal: en una expresión regular `*` solo significa
        # «repetir». `re.escape` hace que los signos del título («Se7en», «Alien³»,
        # «¿Qué pasó ayer?») se busquen tal cual.
        patron = rf"\*\*{re.escape(_plegar(nombre))}\*\*"
        # `finditer` recorre todas las apariciones, no solo la primera.
        for m in re.finditer(patron, plegada):
            menciones.setdefault((m.start(), m.end()), []).append(clave)

    elegidos = []
    for (inicio, fin), claves in sorted(menciones.items()):
        elegida = claves[0]
        if len(claves) > 1:
            tipo = _tipo_segun_pistas(plegada, inicio, fin, pregunta_plegada)
            # `next(..., elegida)`: el primero que cumple, o `elegida` si ninguno.
            elegida = next((c for c in claves if c[1] == tipo), elegida)
        elegidos.append(elegida)
    return [{"id_tmdb": id_tmdb, "tipo": tipo} for id_tmdb, tipo in elegidos]


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


def _registrar_turno(tools_pedidas, vueltas, ultima_sin_tools, origen_de_tarjetas):
    """Una línea de INFO al cerrar el turno: cómo fue, no de qué se habló.

    Sirve para entender, mirando el log, por qué el modelo hizo lo que hizo (qué
    tools pidió y con cuántos resultados, si se quedó sin vueltas, de dónde salieron
    las tarjetas). A propósito no lleva la pregunta ni la respuesta: son datos
    personales y los logs se guardan.
    """
    logger.info(
        "Turno: tools=%s vueltas=%d ultima_sin_tools=%s tarjetas=%s",
        ",".join(tools_pedidas) or "ninguna",
        vueltas,
        "si" if ultima_sin_tools else "no",
        origen_de_tarjetas,
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
    # Para la línea de diagnóstico del final (ver `_registrar_turno`).
    tools_pedidas, vueltas, ultima_sin_tools = [], 0, False

    for _ in range(_MAX_VUELTAS_CON_TOOLS + 1):
        vueltas += 1
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
        resultados, resumen = await en_hilo(_correr_tools, ctx, vuelta.llamadas)
        tools_pedidas.extend(resumen)
        if cierra_el_turno:
            break
        mensajes.append(_mensaje_del_asistente(vuelta))
        mensajes.extend(resultados)
    else:
        # `for ... else`: el `else` corre solo si el ciclo terminó sin `break` (en
        # Java no hay equivalente). Acá: la última vuelta permitida todavía pedía
        # tools, así que el modelo no llegó a responder.
        motivo = "se pasó del tope de vueltas con tools"
        ultima_sin_tools = True
        async for evento in _ultima_llamada(proveedor, mensajes, partes, motivo):
            yield evento

    if not "".join(partes).strip():
        # El turno terminó sin una sola palabra para el usuario.
        ultima_sin_tools = True
        async for evento in _ultima_llamada(
            proveedor, mensajes, partes, "el modelo no escribió nada"
        ):
            yield evento

    respuesta = "".join(partes)
    origen = "mostrar_tarjetas" if ctx.tarjetas else "ninguna"
    if not ctx.tarjetas:
        # Recomendó en el texto y no mostró tarjetas: se arman con lo que nombró.
        # `mostrar_tarjetas` no toca la base, así que se llama directo, sin el
        # puente. Si nombró títulos que ninguna búsqueda devolvió, no pasa nada.
        mostrar_tarjetas(ctx, _tarjetas_nombradas(respuesta, ctx, texto))
        if ctx.tarjetas:
            origen = "red"
            logger.info("Tarjetas armadas por el orquestador: %d", len(ctx.tarjetas))
    _registrar_turno(tools_pedidas, vueltas, ultima_sin_tools, origen)
    yield Resultado(respuesta, ctx.tarjetas)
