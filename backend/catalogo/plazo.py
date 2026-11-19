"""El plazo de red: cuánto tiempo le queda a quien está esperando una respuesta.

Lo abre el chatbot alrededor de sus tools (`chatbot/orquestador.py`). Mientras está
abierto, lo que sale a la red sabe que hay una persona esperando y que el turno
tiene un final:

- **TMDB** (`catalogo/client.py`) usa un timeout más corto y menos reintentos, y
  nunca espera más de lo que queda.
- **Ollama** (`catalogo/services/semantica.py`) espera como mucho lo que queda.

Fuera de un plazo (el resto de la app, Celery, la sync diaria) no cambia nada:
`que_queda()` y `para_tmdb()` devuelven `None` y cada cliente usa sus valores de
siempre.

Vive en una `ContextVar`, igual que el contador de `presupuesto.py`: es una variable
«por pedido». Cada pedido ve la suya aunque varios corran a la vez, y `sync_to_async`
la copia al hilo donde corren las tools. En Java lo más parecido es un `ThreadLocal`.
"""

import contextvars
import time
from contextlib import contextmanager
from dataclasses import dataclass

_plazo = contextvars.ContextVar("plazo_de_red", default=None)


def _ahora():
    """El reloj. Aparte para poder fijarlo en los tests."""
    return time.monotonic()


@dataclass(frozen=True)
class _PlazoDeRed:
    # El instante (de `time.monotonic()`) en que se acaba el tiempo.
    vence: float
    timeout_tmdb: float
    reintentos_tmdb: int


@dataclass(frozen=True)
class LimiteTMDB:
    """Cómo tiene que llamar a TMDB el cliente mientras hay un plazo abierto."""

    # Segundos que puede esperar este pedido. 0 quiere decir «ya no hay tiempo».
    timeout: float
    # Cuántas veces puede reintentar un fallo pasajero.
    reintentos: int


@contextmanager
def plazo_de_red(segundos, *, timeout_tmdb, reintentos_tmdb):
    """Dentro del bloque, la red tiene `segundos` en total para contestar.

    Se usa con `with`. Al salir del bloque (aunque sea por un error) vuelve a no
    haber plazo: es lo que garantiza el `finally`.
    """
    token = _plazo.set(
        _PlazoDeRed(
            vence=_ahora() + max(0.0, segundos),
            timeout_tmdb=timeout_tmdb,
            reintentos_tmdb=reintentos_tmdb,
        )
    )
    try:
        yield
    finally:
        _plazo.reset(token)


def que_queda():
    """Segundos que quedan del plazo abierto (nunca menos de 0), o `None` si no hay."""
    plazo = _plazo.get()
    if plazo is None:
        return None
    return max(0.0, plazo.vence - _ahora())


def para_tmdb():
    """El límite para la próxima llamada a TMDB, o `None` si no hay plazo abierto."""
    plazo = _plazo.get()
    if plazo is None:
        return None
    return LimiteTMDB(
        timeout=min(plazo.timeout_tmdb, max(0.0, plazo.vence - _ahora())),
        reintentos=plazo.reintentos_tmdb,
    )
