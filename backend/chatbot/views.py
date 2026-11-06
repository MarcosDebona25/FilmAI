import asyncio
import logging
from dataclasses import dataclass

from django.conf import settings
from django.http import StreamingHttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.generics import ListAPIView
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.pagination import CursorPagination
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from catalogo.presupuesto import contar_llamadas
from catalogo.services.semantica import pedir_carga_del_modelo
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.limites import soltar_candado, sumar_mensaje, tomar_candado
from chatbot.models import Chat
from chatbot.orquestador import responder
from chatbot.puente import en_hilo
from chatbot.serializers import EntradaMensajeSerializer, MensajeSerializer
from chatbot.servicio import guardar_turno, historial_de
from chatbot.sse import frame, frame_error
from filmai.errores.base import ExcepcionAPI
from filmai.idioma import idioma_efectivo

logger = logging.getLogger(__name__)


class PrepararChatView(APIView):
    """Se llama al abrir el panel, para que el modelo cargue mientras se escribe."""

    @extend_schema(
        request=None,
        responses={202: OpenApiResponse(description="Carga pedida.")},
    )
    def post(self, request):
        pedir_carga_del_modelo()
        return Response(status=status.HTTP_202_ACCEPTED)


class MensajesCursorPagination(CursorPagination):
    """Cursor de 20 para el historial, que el panel carga hacia arriba.

    Cursor y no `?page=2`: en un chat llegan mensajes nuevos mientras se lee, y
    con offset cada uno empuja todo un lugar y la página siguiente repite el
    último mensaje de la anterior. El cursor dice «los anteriores a este», así que
    lo nuevo no lo mueve.

    Desempata por `-id`: si dos mensajes tienen la misma `fecha_hora`, el orden
    entre ellos tiene que ser fijo para que el cursor no pierda el hilo.

    Sin `total` (06/11/2026): el panel no muestra cuántos mensajes hay y `next`
    en `null` ya dice que no quedan más. Se ahorra un `COUNT(*)` por página.
    """

    page_size = 20
    ordering = ("-fecha_hora", "-id")


class HistorialView(ListAPIView):
    """El historial del chat del usuario, de más nuevo a más viejo, de a 20.

    Las tarjetas vuelven como se guardaron, en el idioma de su turno.
    """

    serializer_class = MensajeSerializer
    pagination_class = MensajesCursorPagination

    def get_queryset(self):
        return historial_de(self.request.user)


class NegociacionSoloJSON(DefaultContentNegotiation):
    """Ignora el `Accept`: lo que DRF renderiza en este endpoint es siempre JSON.

    El panel manda `Accept: text/event-stream`. Con la negociación por defecto, DRF
    no encuentra un renderizador para ese tipo y responde 406 (Not Acceptable) antes
    de llegar a la vista. El stream no pasa por un renderizador (es un
    `StreamingHttpResponse`); lo único que DRF renderiza acá son los errores previos
    al stream y el historial, y los dos son JSON.
    """

    def select_renderer(self, request, renderers, format_suffix=None):
        renderizador = next(r for r in renderers if r.media_type == "application/json")
        return renderizador, renderizador.media_type


@dataclass(frozen=True)
class Turno:
    """Lo que la puerta (`MensajesView.post`) le pasa al stream, ya validado."""

    chat: Chat
    texto: str
    idioma: str
    token: str  # del candado: solo con él se puede soltar
    ident: str  # la IP, a la que se le cobran las llamadas a TMDB de las tools


def _guardar_y_soltar(turno, resultado):
    """Guarda el turno y suelta el candado, en una sola ida al hilo.

    Va junta porque, si el navegador corta durante el guardado, Django cierra el
    contexto de hilos del pedido: una segunda ida caería en un hilo que nadie
    maneja. Y el candado se suelta recién cuando el guardado terminó, así un
    reintento no puede entrar mientras la pareja todavía se está escribiendo.
    """
    try:
        return guardar_turno(turno.chat, turno.texto, resultado)
    finally:
        soltar_candado(turno.chat.pk, turno.token)


def _registrar_falla_del_guardado(tarea):
    """Si el guardado falla después de un corte, nadie más va a leer su error."""
    if not tarea.cancelled() and tarea.exception() is not None:
        logger.error("Falló el guardado del turno", exc_info=tarea.exception())


async def _stream(turno):
    """Los eventos de un turno, en el orden del contrato (`contracts/sse-chat.md`).

    Es un generador async: cada `yield` escribe un evento en la conexión.
    Si el navegador corta, Django cancela la tarea que lo recorre y la
    cancelación entra por el `await` donde estaba (o por un `yield`).
    """
    guardando = False
    try:
        # Se abre acá y no alrededor del `return` de la vista: un `with` afuera se
        # cerraría antes del primer evento y las tools quedarían sin presupuesto.
        with contar_llamadas(ident=turno.ident):
            resultado = None
            limite = asyncio.timeout(settings.LLM_TIMEOUT_SECONDS)
            try:
                # El tope es de reloj, tools incluidas. Cubre el modelo y las tools;
                # el guardado queda afuera, para que un turno que llegó justo no se
                # corte a la mitad de escribir.
                async with limite:
                    async for evento in responder(
                        turno.chat, turno.texto, turno.idioma
                    ):
                        if isinstance(evento, Resultado):
                            resultado = evento
                        elif isinstance(evento, Estado):
                            yield frame("estado", {"code": evento.code})
                        elif isinstance(evento, Texto):
                            yield frame("texto", {"delta": evento.delta})
            except TimeoutError:
                if limite.expired():
                    logger.error(
                        "El turno superó los %s s", settings.LLM_TIMEOUT_SECONDS
                    )
                else:
                    # Un timeout propio de una tool o del socket, dentro del tope.
                    logger.exception("Un timeout interno cortó el turno del chat")
                yield frame_error()
                return
            except ErrorDelTurno:
                # El orquestador ya registró la causa al lanzarlo.
                logger.warning("El turno terminó con error")
                yield frame_error()
                return
            except Exception:
                # Algo que no esperábamos. El usuario ve lo mismo; la causa va al log.
                logger.exception("El turno del chat falló")
                yield frame_error()
                return
            if resultado is None:
                logger.error("El orquestador terminó sin entregar un Resultado")
                yield frame_error()
                return

            guardando = True
            tarea = asyncio.ensure_future(en_hilo(_guardar_y_soltar, turno, resultado))
            tarea.add_done_callback(_registrar_falla_del_guardado)
            try:
                # `shield`: si el navegador corta ahora, la cancelación llega acá
                # pero la tarea de guardado sigue hasta el COMMIT.
                pregunta, respuesta = await asyncio.shield(tarea)
            except Exception:
                logger.exception("Falló el guardado del turno")
                yield frame_error()
                return

            yield frame("tarjetas", {"tarjetas": resultado.tarjetas})
            yield frame("fin", {"id": respuesta.pk, "id_pregunta": pregunta.pk})
    finally:
        if not guardando:
            soltar_candado(turno.chat.pk, turno.token)


def _error(descripcion):
    """Una respuesta de error con el sobre `{code, params, errors}` de toda la API."""
    return OpenApiResponse(
        response={"$ref": "#/components/schemas/ErrorEnvelope"},
        description=descripcion,
    )


@extend_schema_view(
    get=extend_schema(
        description=(
            "El historial del chat del usuario, de más nuevo a más viejo, de a 20.\n\n"
            "Las tarjetas vuelven como se guardaron, en el idioma de su turno."
        ),
    ),
    post=extend_schema(
        request=EntradaMensajeSerializer,
        description=(
            "Manda una pregunta y recibe la respuesta como eventos SSE. Estas "
            "respuestas llegan antes de abrir el stream, como JSON con el sobre de "
            "errores: 400, 401, 403, 409 y 429. El 200 es el stream, con los "
            "eventos `estado`, `texto`, `tarjetas`, `fin` y `error` que describe "
            "`contracts/sse-chat.md` (drf-spectacular no puede describir SSE). "
            "La pregunta y la respuesta se guardan juntas, al final; una cancelación "
            "antes de eso no deja nada."
        ),
        responses={
            (200, "text/event-stream"): OpenApiResponse(
                response=OpenApiTypes.STR,
                description="Stream de eventos; termina con `fin` o `error`.",
            ),
            400: _error("`validation_error`, con `errors.texto`."),
            401: _error(
                "`not_authenticated`, o `session_revoked` si la cuenta se dio de baja."
            ),
            403: _error("`permission_denied`: falta o falló el token CSRF."),
            409: _error("`chat_request_in_progress`: ya hay una respuesta en curso."),
            415: _error("`unsupported_media_type`: el cuerpo no es JSON."),
            429: _error("`throttled`, con `retry_after_seconds` y `Retry-After`."),
        },
    ),
)
class MensajesView(HistorialView):
    """`GET`: el historial. `POST`: una pregunta, con su respuesta en streaming.

    Son una clase y no dos rutas porque la URL es la misma. El `post` es una vista
    sync: Django la corre en un hilo, y ahí caben todos los chequeos previos
    (sesión, CSRF, validación, candado, tope por hora), que usan el ORM y la
    caché. Lo único async es el generador que arma el `StreamingHttpResponse`: el
    manejador ASGI lo recorre en el event loop sin ocupar un hilo mientras el
    modelo escribe (design.md, "The one async rule").

    La autenticación y el CSRF son los de DRF, los de todo el resto de la API
    (`JWTCookieAuthentication` con `JWT_AUTH_COOKIE_USE_CSRF`): así los fallos
    llegan con el sobre de errores y no con la página HTML de Django.
    """

    content_negotiation_class = NegociacionSoloJSON
    renderer_classes = (JSONRenderer,)
    # Solo JSON: el panel manda JSON, y un formulario no tiene por qué llegar acá.
    parser_classes = (JSONParser,)

    def post(self, request):
        entrada = EntradaMensajeSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        usuario = request.user
        # El chat lo crea la señal al crear el usuario; esto es la segunda red.
        chat, _ = Chat.objects.get_or_create(
            usuario=usuario, defaults={"titulo": "Chat"}
        )
        # Una sola vez por turno: las tools, las tarjetas y el prompt usan el mismo.
        idioma = idioma_efectivo(request, usuario)

        token = tomar_candado(chat.pk)
        if token is None:
            raise ExcepcionAPI("chat_request_in_progress")
        try:
            # Después del candado y la validación: un 400 o un 409 no gastan cupo.
            dentro_del_tope, espera = sumar_mensaje(usuario.pk)
            if not dentro_del_tope:
                raise Throttled(wait=espera)
        except BaseException:
            soltar_candado(chat.pk, token)
            raise

        turno = Turno(
            chat=chat,
            texto=entrada.validated_data["texto"],
            idioma=idioma,
            token=token,
            ident=BaseThrottle().get_ident(request),
        )
        # Si el navegador corta justo entre acá y el primer evento, el generador
        # no llega a arrancar y su `finally` no corre: el candado se libera solo,
        # a los 60 s.
        respuesta = StreamingHttpResponse(
            _stream(turno), content_type="text/event-stream"
        )
        respuesta["Cache-Control"] = "no-cache"
        # Sin esto, nginx acumula el cuerpo y el panel recibe todo junto al final.
        respuesta["X-Accel-Buffering"] = "no"
        return respuesta
