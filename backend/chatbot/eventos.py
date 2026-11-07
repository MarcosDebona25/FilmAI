"""Contrato entre el orquestador del chatbot y la vista que lo transmite (PR 0).

Es la costura entre los dos frentes del chatbot (`openspec/changes/chatbot/
tasks.md`, «Work split»): el Motor implementa `responder()` y el Canal lo
consume desde la vista SSE. Ninguno de los dos cambia este archivo sin
acordarlo con el otro.

Reglas de `responder(chat, texto, idioma)`:

1. Es un generador async: va entregando eventos a medida que ocurren.
2. Mientras trabaja entrega `Estado` (por ejemplo, al correr una tool) y
   `Texto` (cada pedazo de la respuesta, en orden).
3. Termina entregando **un único** `Resultado` con el texto completo y las
   tarjetas validadas. Ese último elemento no se transmite al navegador: la
   vista lo usa para guardar el turno y recién después emite `tarjetas` y
   `fin` (design.md, «Sequence of one message»).
4. Si el turno no puede terminar (falla el proveedor, se pasa del tope de
   vueltas) lanza `ErrorDelTurno` y no entrega `Resultado`. La vista lo
   convierte en el evento `error` con `chat_unavailable`.
5. No guarda nada ni toma el candado: el tiempo máximo del turno, el candado y
   el guardado son de la vista.
6. No atrapa `asyncio.CancelledError`: si el usuario cancela, la cancelación
   tiene que llegar a la vista sin que nadie la frene.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, NotRequired, Protocol, TypedDict

if TYPE_CHECKING:
    from chatbot.models import Chat


class Tarjeta(TypedDict):
    """Una tarjeta de producción, igual en el evento `tarjetas` y en el historial."""

    id_tmdb: int
    tipo: Literal["movie", "tv"]
    titulo: str
    # El formato exacto del póster lo fija `mostrar_tarjetas` (PR2); None si no tiene.
    poster: str | None
    anio: int | None
    # Promedio de TMDB con un decimal; None si no tiene. `NotRequired` porque las
    # tarjetas guardadas en `Mensaje.tarjetas` antes de sumarlo no lo traen
    # (07/11/2026). Las nuevas lo traen siempre.
    nota_tmdb: NotRequired[float | None]


@dataclass(frozen=True)
class Estado:
    """Algo está pasando (hoy, solo una búsqueda). El front traduce el código."""

    code: Literal["searching"]


@dataclass(frozen=True)
class Texto:
    """Un pedazo de la respuesta. El front los concatena en el orden en que llegan."""

    delta: str


@dataclass(frozen=True)
class Resultado:
    """Cierre del turno: lo que la vista guarda. Siempre es el último elemento."""

    texto: str
    tarjetas: list[Tarjeta] = field(default_factory=list)


Evento = Estado | Texto | Resultado


class ErrorDelTurno(Exception):
    """El turno no pudo terminar. La causa va al log; el usuario ve un solo mensaje."""


class Responder(Protocol):
    """Firma que cumplen `orquestador.responder` y `OrquestadorFalso.responder`.

    Se declara con `def` y no con `async def`: llamar a una función
    `async def` que tiene `yield` no ejecuta nada, devuelve un iterador async
    que se recorre con `async for`. Eso es lo que describe esta firma.
    """

    def __call__(
        self, chat: "Chat", texto: str, idioma: str
    ) -> AsyncIterator[Evento]: ...
