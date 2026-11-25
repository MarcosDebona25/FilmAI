"""El corazón del chatbot: el ida y vuelta entre el modelo y las tools.

Conecta las piezas: arma lo que recibe el modelo, corre las tools que pide y entrega
los eventos de `eventos.py`. También administra el tiempo: cada turno tiene un plazo
(`plazo.py`, 25 s) que se reparte entre las llamadas al modelo y las tools, y si no
alcanza cierra con lo que tiene. No guarda nada: eso y el candado son de la vista.
Mapa completo: `backend/chatbot/README.md`.

Lo usan: la vista del chat (PR 5) y `manage.py chatear`.
Usa: `llm.py`, `prompts.py`, `contexto.py`, `anonimizar.py` y `tools/`.

Lo async es solo este archivo y `llm.py`. Todo lo que toca la base o TMDB es código
común, y se llama con `await en_hilo(...)`.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from catalogo.plazo import plazo_de_red
from chatbot.anonimizar import CONVERSACION, anonimizar
from chatbot.contexto import armar_perfil
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.idioma import detectar_idioma
from chatbot.llm import Vuelta, crear_proveedor
from chatbot.marcadores import (
    PRESUPUESTO_SAGAS,
    TOPE_TARJETAS,
    FiltroDeMarcadores,
    recomienda_sin_buscar,
    tarjetas_sin_marcadores,
    una_parte_por_saga,
)
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.plazo import Plazo, recorrer
from chatbot.prompts import armar_sistema
from chatbot.puente import en_hilo
from chatbot.servicio import titulos_recordados
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
# --- Cómo se reparte el plazo del turno (`LLM_TIMEOUT_SECONDS`, 25 s) ---
# Son partes del total, así que acompañan al plazo si se lo cambia. Entre paréntesis,
# lo que valen con 25 s. Medido el 15/11/2026: una llamada al modelo tarda 1,6-2,5 s
# y un turno con 4 llamadas y 6 tools, 8,9 s.
#
# La reserva para cerrar (7,5 s): tiempo que se guarda para la última llamada, la
# que escribe la respuesta. Buscar (modelo con tools, y las tools) puede usar el
# resto: hasta el segundo 17,5. Son 3 veces lo que tarda una llamada normal.
_FRACCION_PARA_CERRAR = 0.3
# Lo mínimo que tiene que quedar para empezar otra vuelta con tools (10 s): la
# reserva más 2,5 s, que es lo que tarda una vuelta. Con menos, la vuelta no llegaría
# a terminar y se pagaría una llamada al modelo para nada.
_FRACCION_PARA_OTRA_VUELTA = 0.4
# La búsqueda forzada (ver `_hay_que_forzar_la_busqueda`) solo se intenta si el
# turno lleva menos de esta parte del plazo (10 s): otra llamada al modelo más las
# tools y la respuesta tienen que entrar en lo que queda.
_FRACCION_PARA_REINTENTAR = 0.4
# Con qué termina una respuesta que se cortó a la mitad por tiempo.
_CORTADA = "…"
# El resultado que ve el modelo de una tool que no llegó a correr o a terminar.
_SIN_TIEMPO = {"error": "tool_failed"}
_ROLES = {TipoAutor.USUARIO: "user", TipoAutor.CHATBOT: "assistant"}


def _historial(chat, usuario):
    """Los últimos mensajes de la sesión actual, de más viejo a más nuevo.

    Sale anonimizado y con dos cuidados para que el modelo no imite lo que no debe
    (revisión del 13/11/2026: con rechazos viejos guardados, 4 de 4 respuestas a un
    pedido válido eran rechazos, y con el chat limpio 4 de 4 salían bien):

    - **Solo la sesión actual.** Se recorren los mensajes del más nuevo al más viejo
      y se corta en el primer hueco mayor a `CHAT_VENTANA_SESION_MINUTOS`. El primer
      hueco se mide contra el momento actual (el mensaje que está por llegar): si el
      último mensaje guardado es de hace horas, es otra sesión y el historial va vacío.
    - **Sin negritas en lo que dijo el asistente.** Lo guardado lleva `**Título**`
      (lo arma el filtro de marcadores), pero el modelo no tiene que ver su propia
      respuesta con negritas: las copiaría sin haber buscado. Es una copia: lo
      guardado queda como está.
    """
    ventana = timedelta(minutes=settings.CHAT_VENTANA_SESION_MINUTOS)
    ultimos = Mensaje.objects.filter(chat=chat).order_by("-fecha_hora", "-id")[
        :_MENSAJES_DE_HISTORIAL
    ]
    sesion = []
    # Hasta dónde llega el hueco que se está midiendo: al principio, hasta ahora.
    # `timedelta` es una duración, como `java.time.Duration`: se compara con `>`.
    referencia = timezone.now()
    for mensaje in ultimos:
        if referencia - mensaje.fecha_hora > ventana:
            break
        sesion.append(mensaje)
        referencia = mensaje.fecha_hora

    historial = []
    for mensaje in reversed(sesion):
        texto = anonimizar(mensaje.texto, usuario, CONVERSACION)
        if mensaje.autor == TipoAutor.CHATBOT:
            texto = texto.replace("**", "")
        historial.append({"role": _ROLES[mensaje.autor], "content": texto})
    return historial


def _reloj():
    """Segundos para medir cuánto tarda el turno (solo para el log). Fijable en tests."""
    return time.perf_counter()


class _Medicion:
    """Lo que costó el turno: una `Vuelta` por cada llamada al modelo.

    Solo mira cantidades (tokens, segundos, el motivo de fin): nunca texto. Se llena
    con cada `Vuelta` que entrega el proveedor, incluidas la llamada descartada de la
    búsqueda forzada y la última sin tools, porque también cuestan.
    """

    def __init__(self):
        self.vueltas = []

    def sumar(self, vuelta):
        self.vueltas.append(vuelta)

    def _suma(self, campo):
        """La suma de un campo de `Uso` entre las llamadas, o `"?"` si ninguna lo informó."""
        valores = [
            getattr(v.uso, campo)
            for v in self.vueltas
            if v.uso and getattr(v.uso, campo) is not None
        ]
        return sum(valores) if valores else "?"

    def resumen(self, total):
        """Los campos para la línea `Turno:`, ya como texto: `clave=valor` separados."""
        return (
            f"llamadas={len(self.vueltas)} tokens_entrada={self._suma('entrada')} "
            f"tokens_salida={self._suma('salida')} "
            f"cache_acierto={self._suma('cache_acierto')} "
            f"cache_fallo={self._suma('cache_fallo')} "
            f"cortado_por_largo={'si' if any(v.fin == 'length' for v in self.vueltas) else 'no'} "
            f"segundos_por_llamada={','.join(f'{v.segundos:.1f}' for v in self.vueltas)} "
            f"segundos_total={total:.1f}"
        )


def _ahora():
    """El reloj del plazo del turno. Aparte para poder fijarlo en los tests."""
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
        titulos_recordados(chat.contexto.get("ya_recomendados", [])),
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


def _nombre_para_el_log(llamada):
    """El nombre de la tool, solo si es una real.

    El nombre lo escribe el modelo: si no es una tool real, un nombre con saltos de
    línea podría forjar líneas falsas en el log.
    """
    return llamada.nombre if llamada.nombre in FUNCIONES else "desconocida"


def _mensaje_de_tool(llamada, resultado):
    """El resultado de una tool, en el formato que espera el modelo."""
    return {
        "role": "tool",
        "tool_call_id": llamada.id,
        "content": json.dumps(resultado, ensure_ascii=False),
    }


def _correr_tools(ctx, llamadas, segundos):
    """Corre las tools de una vuelta, en orden, con `segundos` para toda la tanda.

    Devuelve dos listas: los mensajes de resultado para el modelo y, para el log,
    un `nombre(cantidad)` por tool. Una función puede devolver varios valores en
    Python (una tupla); en Java habría que armar una clase chica para eso.

    Corre en un hilo, y un hilo no se puede cancelar desde afuera. Por eso el
    tiempo viaja hacia adentro: `plazo_de_red` deja anotado cuánto queda, y TMDB y
    Ollama lo consultan antes de cada pedido (`catalogo/plazo.py`). Además TMDB usa
    acá un timeout más corto que en el resto de la app (`CHAT_TMDB_TIMEOUT`).
    """
    resultados, resumen = [], []
    with plazo_de_red(
        segundos,
        timeout_tmdb=settings.CHAT_TMDB_TIMEOUT,
        reintentos_tmdb=settings.CHAT_TMDB_REINTENTOS,
    ):
        for llamada in llamadas:
            argumentos = _argumentos_de(llamada)
            if argumentos is None:
                # Pasa si el modelo se quedó sin tokens en medio de los argumentos.
                resultado = {"error": "tool_failed"}
            else:
                resultado = ejecutar(ctx, llamada.nombre, argumentos)
            resumen.append(f"{_nombre_para_el_log(llamada)}({_cantidad_de(resultado)})")
            resultados.append(_mensaje_de_tool(llamada, resultado))
    return resultados, resumen


def _tools_sin_tiempo(llamadas):
    """Lo mismo que devuelve `_correr_tools`, para tools que no corrieron o se cortaron.

    El modelo las ve como búsquedas fallidas (`tool_failed`). Hay que contestarle
    cada una: un pedido de tool sin su resultado es un error para el proveedor.
    """
    resultados = [_mensaje_de_tool(llamada, _SIN_TIEMPO) for llamada in llamadas]
    resumen = [f"{_nombre_para_el_log(llamada)}(sin_tiempo)" for llamada in llamadas]
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


# --- El turno, partido en pasos ---------------------------------------------------
#
# `responder` (al final del archivo) es el índice: llama a estos pasos en orden.
# Cada paso recibe el mismo `_Turno`, que es la memoria compartida entre todos.
#
#   _abrir_turno          lee la base y arma lo que recibe el modelo
#   _conversar            el ciclo de vueltas; por cada vuelta:
#     _escuchar             una llamada al modelo (retiene o transmite el texto)
#     _hay_que_forzar_la_busqueda   ¿recomendó sin buscar?
#     _cerrar_texto_de_la_vuelta    entrega lo retenido, salvo un preámbulo
#     _buscar               corre las tools y le deja los resultados al modelo
#     (si se acaba el tiempo: _cerrar_respuesta_cortada o _ultima_llamada)
#   _asegurar_respuesta   si no hubo ni una palabra, una última llamada
#   _armar_tarjetas       la red sin marcadores y una parte por saga
#   _registrar_turno      la línea `Turno:` del log
#
# Varios pasos son generadores async (`async def` con `yield`): no devuelven un
# valor, van entregando eventos. El que los llama los recorre con `async for` y
# reenvía cada evento con su propio `yield`. En Java sería parecido a recibir un
# `Consumer<Evento>` y llamarlo por cada evento. Como un generador no puede además
# devolver un resultado con `return valor`, lo que cada paso averigua queda escrito
# en `_Turno` o en `_Escucha`.


@dataclass
class _Turno:
    """Todo lo que se va sabiendo de un turno mientras se responde.

    Antes eran una docena de variables sueltas dentro de `responder`. Juntas en un
    objeto, cada paso puede ser una función aparte que recibe el turno. Un
    `@dataclass` es una clase a la que Python le escribe el constructor a partir de
    los campos (como un `record` de Java, pero este se puede modificar).

    `field(default_factory=list)` le da a cada turno su propia lista vacía: con
    `= []` todos los turnos compartirían la misma.
    """

    proveedor: object
    ctx: ContextoTurno
    # La conversación que recibe el modelo. Crece con cada vuelta de tools.
    mensajes: list
    # Cambia los `[[n]]` del modelo por el título y suma las tarjetas (marcadores.py).
    filtro: FiltroDeMarcadores
    # Cuánto tiempo le queda al turno (ver `plazo.py` y las `_FRACCION_…` de arriba).
    plazo: Plazo
    # `_reloj()` al empezar, para los `segundos_total` del log.
    inicio_medido: float
    # El texto que ya salió al usuario, en pedazos. Unidos son la respuesta final.
    partes: list = field(default_factory=list)
    medicion: _Medicion = field(default_factory=_Medicion)
    # Para la línea de diagnóstico del final (ver `_registrar_turno`).
    tools_pedidas: list = field(default_factory=list)
    vueltas: int = 0
    ultima_sin_tools: bool = False
    # Búsqueda forzada: `reintento` dice que ya se decidió hacerla (es una sola por
    # turno) y `descartado` guarda el texto del primer intento, por si la llamada
    # forzada falla.
    reintento: bool = False
    descartado: list | None = None
    # Si el plazo obligó a cerrar antes, para el log: `no`, `busqueda` (se dejó de
    # buscar y se respondió con lo que había) o `respuesta` (el texto quedó cortado).
    sin_tiempo: str = "no"

    def respuesta(self):
        """El texto que el usuario recibió hasta ahora, de corrido."""
        return "".join(self.partes)

    def reserva(self):
        """Los segundos del plazo que se guardan para la respuesta final."""
        return self.plazo.total * _FRACCION_PARA_CERRAR


@dataclass
class _Escucha:
    """Una llamada al modelo dentro del ciclo: cómo se hace y qué dejó.

    Los tres primeros campos se deciden antes de llamar; `retenido` y `vuelta` los
    llena `_escuchar` mientras el modelo escribe.
    """

    # Mientras ninguna tool corrió, la vuelta se retiene entera: si resulta que el
    # modelo recomendó sin buscar, hay que poder descartarla sin que el usuario haya
    # leído nada. Después de una búsqueda se transmite en vivo.
    retener: bool
    # Sin esto, el texto de dos vueltas saldría pegado: «…despacio.¿Querés…».
    separar: bool
    # La llamada va con `tool_choice="required"` (la búsqueda forzada).
    forzada: bool
    # Lo que todavía no salió al front, por si resulta ser un preámbulo.
    retenido: list = field(default_factory=list)
    vuelta: Vuelta | None = None
    # El modelo ya mandó algún texto en esta llamada (retenido o transmitido).
    escribio: bool = False
    # El plazo cortó la llamada antes de que terminara: no hay `vuelta`.
    cortada: bool = False

    def texto_retenido(self):
        return "".join(self.retenido)


async def _abrir_turno(chat, texto, idioma, proveedor, plazo):
    """Paso 1: elige el proveedor y lee de la base todo lo que el turno necesita.

    Es `async def` sin `yield`: una corrutina común, que se llama con `await` y sí
    devuelve un valor (el `_Turno`).
    """
    try:
        proveedor = proveedor or crear_proveedor()
        ctx, mensajes = await en_hilo(_preparar, chat, texto, idioma)
    except Exception as error:
        # Un `LLM_PROVIDER` que no existe, la base caída o un `contexto` mal armado.
        logger.exception("No se pudo preparar el turno")
        raise ErrorDelTurno("No se pudo preparar el turno") from error
    return _Turno(
        proveedor=proveedor,
        ctx=ctx,
        mensajes=mensajes,
        filtro=FiltroDeMarcadores(ctx),
        plazo=plazo,
        # Se llama acá y no como valor por defecto del campo: así los tests pueden
        # reemplazar `_reloj` con `patch`.
        inicio_medido=_reloj(),
    )


async def _sacar_retenido(turno, escucha):
    """Manda al front lo que la vuelta tenía retenido, con su separador si hace falta."""
    async for evento in _sacar(
        turno.filtro,
        turno.partes,
        _con_separador(escucha.retenido, escucha.separar),
    ):
        yield evento
    escucha.separar, escucha.retenido = False, []


async def _escuchar(turno, escucha):
    """Una llamada al modelo: junta su texto y deja la `Vuelta` en `escucha`.

    El texto llega de a pedazos. Se acumula en `escucha.retenido` y sale al front
    solo cuando ya se sabe que no es un preámbulo: si la vuelta no se retiene entera
    (`escucha.retener`) y lo acumulado pasó `_LARGO_DE_PREAMBULO`. Desde ahí cada
    pedazo sale en vivo.

    El tiempo: mientras el modelo no escribió nada, la llamada se corta cuando al
    plazo le queda solo la reserva para cerrar (si está colgado, todavía se puede
    pedir una respuesta corta). En cuanto llega el primer texto, el límite se corre
    hasta el final del plazo: una respuesta que ya está saliendo no se interrumpe
    para volver a pedirla. Si el corte llega, queda `escucha.cortada = True`.
    """
    # `**{...}` abre el diccionario como argumentos con nombre; vacío, no pasa
    # ninguno (así un proveedor sin `tool_choice` sigue funcionando).
    extra = {"tool_choice": "required"} if escucha.forzada else {}
    en_vivo = False
    corte = turno.plazo.cortar(reserva=turno.reserva())
    try:
        flujo = turno.proveedor.escribir(turno.mensajes, ESQUEMAS, **extra)
        # `recorrer` es un `async for` en el que cada espera al modelo tiene límite.
        async for item in recorrer(flujo, corte):
            if isinstance(item, Vuelta):
                escucha.vuelta = item
                turno.medicion.sumar(item)
                continue
            if item and not escucha.escribio:
                escucha.escribio = True
                corte.correr_hasta(turno.plazo.queda())
            escucha.retenido.append(item)
            if escucha.retener or (
                not en_vivo and len(escucha.texto_retenido()) <= _LARGO_DE_PREAMBULO
            ):
                continue
            en_vivo = True
            async for evento in _sacar_retenido(turno, escucha):
                yield evento
    except Exception as error:
        # `Exception` no incluye `CancelledError`: si el usuario cancela, la
        # cancelación tiene que llegar a la vista.
        if isinstance(error, TimeoutError) and corte.vencio():
            # No es una falla del proveedor: se acabó el tiempo de esta llamada.
            # Qué hacer lo decide `_conversar`.
            logger.warning("El plazo cortó una llamada al modelo")
            escucha.cortada = True
            return
        logger.exception("El proveedor falló")
        if not (escucha.forzada and turno.descartado):
            raise ErrorDelTurno("El proveedor falló") from error
        # La llamada forzada falló: se muestra el primer intento (sin los
        # marcadores inválidos), que es mejor que un error.
        escucha.retenido = turno.descartado
        escucha.vuelta = Vuelta(texto="".join(turno.descartado))


def _hay_que_forzar_la_busqueda(turno, escucha):
    """¿El modelo recomendó sin haber buscado, y todavía hay tiempo para repetir?

    Solo puede pasar en una vuelta retenida (ninguna tool corrió), que no pidió
    tools, una vez por turno y si el texto nombra un título que no salió de una
    búsqueda (`recomienda_sin_buscar`). El reloj se mira al final y solo si todo lo
    anterior se cumple: `and` deja de evaluar en el primer `False`, igual que `&&`.
    """
    return (
        escucha.retener
        and not escucha.vuelta.llamadas
        and not turno.reintento
        and recomienda_sin_buscar(escucha.texto_retenido(), turno.ctx.candidatos())
        and turno.plazo.transcurrido() < turno.plazo.total * _FRACCION_PARA_REINTENTAR
    )


async def _cerrar_texto_de_la_vuelta(turno, escucha):
    """Al terminar una vuelta, entrega el texto que seguía retenido.

    Texto corto y una búsqueda: era un «ya busco», y la respuesta viene después. Se
    descarta solo del front; el modelo lo sigue viendo en `mensajes`.
    """
    es_preambulo = (
        escucha.vuelta.llamadas and len(escucha.texto_retenido()) <= _LARGO_DE_PREAMBULO
    )
    if escucha.retenido and not es_preambulo:
        async for evento in _sacar_retenido(turno, escucha):
            yield evento
    # Lo que el filtro retenía por si era un marcador: la vuelta terminó.
    if resto := _soltar(turno.filtro, turno.partes):
        yield resto


def _cerrar_respuesta_cortada(turno, escucha):
    """El plazo cortó una respuesta a la mitad: entrega lo que había y la cierra con «…».

    Devuelve un solo `Texto` con lo que seguía retenido (si la vuelta se retenía
    entera, es todo lo que escribió) más los puntos suspensivos. Lo que ya había
    salido al front no se toca. Es una respuesta incompleta pero válida: el turno
    termina con su `Resultado` y se guarda, en vez de perderse en un error.
    """
    turno.sin_tiempo = "respuesta"
    pendiente = (
        _con_separador(escucha.retenido, escucha.separar) if escucha.retenido else []
    )
    # El filtro cambia los `[[n]]` por el título; `cerrar()` suelta lo que retenía
    # (un marcador que quedó por la mitad se descarta).
    texto = "".join(turno.filtro.alimentar(pedazo) for pedazo in pendiente)
    texto = (texto + turno.filtro.cerrar()).rstrip() + _CORTADA
    turno.partes.append(texto)
    return Texto(texto)


async def _buscar(turno, vuelta):
    """Corre las tools que pidió el modelo y le deja los resultados en `mensajes`.

    Las tools son código común (bloquean mientras esperan a TMDB o a la base): van
    por `en_hilo`, y el `await` espera sin frenar a los demás pedidos.

    Tienen para correr lo que queda del plazo menos la reserva para cerrar. Devuelve
    `False` si no había tiempo para correrlas o si se pasaron: en los dos casos el
    modelo las recibe como fallidas y `_conversar` pasa a la respuesta final.

    Si se pasan, el `Corte` deja de esperarlas pero el hilo sigue hasta que la tool
    termina (un hilo no se puede cancelar). Termina enseguida, porque adentro TMDB y
    Ollama tienen el mismo límite (`plazo_de_red`). Mientras tanto, lo próximo que
    vaya al hilo (las sagas, el guardado) espera detrás.
    """
    segundos = turno.plazo.queda(reserva=turno.reserva())
    a_tiempo = segundos > 0
    if a_tiempo:
        corte = turno.plazo.cortar(reserva=turno.reserva())
        try:
            resultados, resumen = await corte.esperar(
                en_hilo(_correr_tools, turno.ctx, vuelta.llamadas, segundos)
            )
        except TimeoutError:
            if not corte.vencio():
                raise
            logger.warning("El plazo cortó las tools")
            a_tiempo = False
    if not a_tiempo:
        turno.sin_tiempo = "busqueda"
        resultados, resumen = _tools_sin_tiempo(vuelta.llamadas)
    turno.tools_pedidas.extend(resumen)
    turno.mensajes.append(_mensaje_del_asistente(vuelta))
    turno.mensajes.extend(resultados)
    return a_tiempo


async def _ultima_llamada(turno, motivo):
    """Una llamada más, sin tools, para que el modelo responda con lo que ya tiene.

    Antes, pasarse del tope de vueltas o terminar sin texto era un error para el
    usuario (5 de 32 turnos del set dorado, 12/11/2026). Ahora se le pide al modelo
    que cierre: como no recibe tools, solo puede escribir. Si esta llamada también
    falla o vuelve vacía, ahí sí es un `ErrorDelTurno`.

    Entrega el texto en vivo y lo suma a `turno.partes`. Si ya había texto de otras
    vueltas, lo nuevo va separado con un «\n\n» y lo anterior no se repite.

    Tiene todo lo que queda del plazo. Si el plazo la corta: con algo escrito, el
    turno cierra con eso (lo de esta llamada termina en «…»); sin una sola palabra en
    todo el turno, es un `ErrorDelTurno`.
    """
    logger.warning("Última llamada sin tools: %s", motivo)
    turno.ultima_sin_tools = True
    turno.mensajes.append({"role": "system", "content": _AVISO_DE_ULTIMA_LLAMADA})
    separar = bool(turno.respuesta().strip())
    escrito = False
    corte = turno.plazo.cortar()
    try:
        async for item in recorrer(turno.proveedor.escribir(turno.mensajes, []), corte):
            # Si el modelo pidiera tools igual, la `Vuelta` final se ignora: solo
            # importa el texto que salió.
            if isinstance(item, Vuelta):
                turno.medicion.sumar(item)
                continue
            if not item:
                continue
            saliente = turno.filtro.alimentar(item)
            if not saliente:
                continue
            if separar:
                turno.partes.append("\n\n")
                yield Texto("\n\n")
                separar = False
            escrito = escrito or bool(saliente.strip())
            turno.partes.append(saliente)
            yield Texto(saliente)
    except Exception as error:
        if not (isinstance(error, TimeoutError) and corte.vencio()):
            logger.exception("La última llamada falló")
            raise ErrorDelTurno("La última llamada falló") from error
        logger.warning("El plazo cortó la última llamada")
        if escrito:
            turno.sin_tiempo = "respuesta"
            texto = turno.filtro.cerrar().rstrip() + _CORTADA
            turno.partes.append(texto)
            yield Texto(texto)
        elif not turno.respuesta().strip():
            raise ErrorDelTurno("Se acabó el plazo sin respuesta") from error
        # Sin nada nuevo pero con texto de vueltas anteriores: el turno cierra con eso.
        return
    if resto := _soltar(turno.filtro, turno.partes):
        escrito = escrito or bool(resto.delta.strip())
        yield resto
    if not escrito:
        raise ErrorDelTurno("La última llamada no escribió nada")


def _alcanza_para_otra_vuelta(turno):
    """¿Queda tiempo para otra vuelta con tools y, después, para la respuesta?"""
    return turno.plazo.queda() >= turno.plazo.total * _FRACCION_PARA_OTRA_VUELTA


async def _conversar(turno):
    """Paso 2: el ida y vuelta con el modelo, hasta que responde sin pedir tools.

    Cada pasada del ciclo es una vuelta: una llamada al modelo y, si pidió tools,
    correrlas. Termina con `return` cuando el modelo contesta sin pedir nada (o
    cuando el plazo corta una respuesta que ya estaba saliendo).

    Si el ciclo se termina de otra forma, el modelo todavía no respondió: se sale
    con `break` y `motivo` dice por qué. Lo que sigue al `for` es igual en todos los
    casos: una última llamada sin tools para que responda con lo que encontró.
    """
    # La próxima llamada es la búsqueda forzada (ver `_hay_que_forzar_la_busqueda`).
    forzar = False
    motivo = "se pasó del tope de vueltas con tools"
    for numero in range(_MAX_VUELTAS_CON_TOOLS + 1):
        # Antes de otra vuelta se mira el reloj (la primera se hace siempre).
        if numero and not _alcanza_para_otra_vuelta(turno):
            turno.sin_tiempo = "busqueda"
            motivo = "no queda tiempo para otra vuelta con tools"
            break
        turno.vueltas += 1
        escucha = _Escucha(
            retener=not turno.tools_pedidas,
            separar=bool(turno.partes),
            forzada=forzar,
        )
        forzar = False
        async for evento in _escuchar(turno, escucha):
            yield evento

        if escucha.cortada and escucha.escribio:
            # Se acabó el plazo con la respuesta a medio escribir: sale lo que hay.
            yield _cerrar_respuesta_cortada(turno, escucha)
            return
        if escucha.cortada:
            # El modelo no dijo nada en su tiempo. Queda la reserva para cerrar.
            turno.sin_tiempo = "busqueda"
            motivo = "el modelo no contestó a tiempo"
            break

        if _hay_que_forzar_la_busqueda(turno, escucha):
            # Se descarta lo que escribió y la llamada se repite, una sola vez, con
            # `tool_choice="required"`.
            logger.warning("Recomendó sin buscar: se repite la llamada con tool_choice")
            turno.reintento = forzar = True
            turno.descartado = escucha.retenido
            continue

        async for evento in _cerrar_texto_de_la_vuelta(turno, escucha):
            yield evento
        if not escucha.vuelta.llamadas:
            # Respondió sin pedir tools: la conversación con el modelo terminó.
            return

        if turno.plazo.queda(reserva=turno.reserva()) > 0:
            yield Estado("searching")
        if not await _buscar(turno, escucha.vuelta):
            motivo = "no hubo tiempo para terminar de buscar"
            break

    # Solo se llega acá si el modelo todavía no respondió (ver `motivo`).
    async for evento in _ultima_llamada(turno, motivo):
        yield evento


async def _asegurar_respuesta(turno):
    """Paso 3: si el turno terminó sin una sola palabra para el usuario, la pide."""
    if turno.respuesta().strip():
        return
    async for evento in _ultima_llamada(turno, "el modelo no escribió nada"):
        yield evento


async def _armar_tarjetas(turno, respuesta, pedido):
    """Paso 4: deja en `ctx.tarjetas` las tarjetas definitivas del turno.

    Devuelve `(red, saga_descartadas, sin_tarjeta)` para el log: si las tarjetas
    salieron de la red de seguridad, cuántas se saltearon por repetir saga y cuántos
    títulos recomendados quedaron sin tarjeta por el tope (sin contar esas sagas).
    """
    ctx, filtro = turno.ctx, turno.filtro
    # Red de seguridad: hubo búsquedas, pero el modelo recomendó en texto plano (sin
    # un solo `[[n]]` válido). El texto ya salió y no se toca: solo se arman las
    # tarjetas de los candidatos que nombra (ver `tarjetas_sin_marcadores`).
    red = False
    mencionados = filtro.mencionados
    if turno.tools_pedidas and filtro.validos == 0 and not ctx.tarjetas:
        # Sin tope: `una_parte_por_saga` elige y puede necesitar uno más.
        mencionados = tarjetas_sin_marcadores(respuesta, ctx, pedido, tope=None)
        ctx.tarjetas.extend(mencionados[:TOPE_TARJETAS])
        red = bool(ctx.tarjetas)
    # Una sola parte de cada saga (14/11/2026): con dos o más títulos se mira en TMDB
    # si alguna película repite colección. Es código bloqueante (hilos y red), así que
    # va por `en_hilo` como las tools. No falla nunca: ante un error, queda lo de antes.
    saga_descartadas = 0
    if len(mencionados) > 1:
        # Las sagas esperan a TMDB hasta 2 s, o lo que quede del plazo si es menos.
        tarjetas, saga_descartadas = await en_hilo(
            una_parte_por_saga,
            mencionados,
            presupuesto=min(PRESUPUESTO_SAGAS, turno.plazo.queda()),
        )
        ctx.tarjetas[:] = tarjetas
    sin_tarjeta = len(mencionados) - len(ctx.tarjetas) - saga_descartadas
    return red, saga_descartadas, sin_tarjeta


def _registrar_turno(turno, total, red=False, saga_descartadas=0, sin_tarjeta=0):
    """Paso 5: una línea de INFO al cerrar el turno: cómo fue, no de qué se habló.

    Sirve para entender, mirando el log, por qué el modelo hizo lo que hizo (qué
    tools pidió y con cuántos resultados, si se quedó sin vueltas, cuántos marcadores
    `[[n]]` usó y cuántos no correspondían a ningún título, cuántas negritas escribió
    por su cuenta, si hubo búsqueda forzada, cuántas tarjetas se saltearon por ser otra
    parte de una saga que ya tenía la suya, cuántos títulos recomendados quedaron sin
    tarjeta por el tope: `titulos_sin_tarjeta`, si el plazo obligó a cerrar antes:
    `sin_tiempo`) y cuánto costó: tokens de entrada y salida,
    los que salieron de la caché del proveedor, si alguna llamada se cortó por largo y
    los segundos de cada llamada y del turno (ver `_Medicion`). A propósito no lleva la
    pregunta ni la respuesta: son datos personales y los logs se guardan.
    """
    logger.info(
        "Turno: tools=%s vueltas=%d ultima_sin_tools=%s tarjetas=%s "
        "marcadores_validos=%d marcadores_invalidos=%d negritas_propias=%d "
        "reintento_forzado=%s saga_descartadas=%d titulos_sin_tarjeta=%d "
        "sin_tiempo=%s %s",
        ",".join(turno.tools_pedidas) or "ninguna",
        turno.vueltas,
        "si" if turno.ultima_sin_tools else "no",
        "red_sin_marcadores"
        if red
        else "marcadores"
        if turno.ctx.tarjetas
        else "ninguna",
        turno.filtro.validos,
        turno.filtro.invalidos,
        turno.filtro.negritas,
        "si" if turno.reintento else "no",
        saga_descartadas,
        sin_tarjeta,
        turno.sin_tiempo,
        turno.medicion.resumen(total),
    )


async def responder(chat, texto, idioma, *, proveedor=None):
    """Responde un mensaje, entregando eventos a medida que ocurren.

    Cumple las reglas de `eventos.py`. Es un generador async: cada `yield` le pasa
    un evento a la vista y sigue desde ahí cuando la vista pide el próximo.
    `proveedor` es para los tests; sin él, se usa el configurado.

    Acá solo está el orden de los pasos; el detalle de cada uno, en su función.
    """
    # El reloj del turno arranca acá: el plazo cubre todo, también leer la base.
    plazo = Plazo(settings.LLM_TIMEOUT_SECONDS, _ahora)
    turno = await _abrir_turno(chat, texto, idioma, proveedor, plazo)
    async for evento in _conversar(turno):
        yield evento
    async for evento in _asegurar_respuesta(turno):
        yield evento
    respuesta = turno.respuesta()
    red, saga_descartadas, sin_tarjeta = await _armar_tarjetas(turno, respuesta, texto)
    _registrar_turno(
        turno, _reloj() - turno.inicio_medido, red, saga_descartadas, sin_tarjeta
    )
    yield Resultado(respuesta, turno.ctx.tarjetas)
