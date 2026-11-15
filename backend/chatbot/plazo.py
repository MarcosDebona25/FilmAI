"""El plazo del turno: cuánto tiempo queda para responder y cómo cortar a tiempo.

El orquestador crea un `Plazo` al empezar cada turno (25 s por defecto,
`LLM_TIMEOUT_SECONDS`) y le pregunta `queda()` antes de cada paso. Para que un paso
no se pase, lo envuelve en un `Corte`.

Lo usa: `orquestador.py`. La explicación completa del reparto está en
`backend/chatbot/README.md`, «El plazo del turno».
"""

import asyncio
from contextlib import aclosing

# Lo que devuelve `anext(flujo, _FIN)` cuando el flujo se terminó. `object()` crea
# un valor único: no se puede confundir con nada que entregue el proveedor.
_FIN = object()


class Corte:
    """Un límite de tiempo para una o varias esperas (`await`).

        corte = Corte(5)                      # vence en 5 segundos
        try:
            dato = await corte.esperar(algo_lento())
        except TimeoutError:
            ...  # `corte.vencio()` dice si fue este corte

    Cómo funciona por dentro (`asyncio.timeout_at`, de la biblioteca estándar): al
    empezar a esperar le pide al event loop que lo despierte a la hora del límite.
    Si esa hora llega y lo esperado no terminó, el event loop **cancela** esa espera:
    el `await` que estaba esperando (al modelo, a un hilo) lanza `CancelledError` ahí
    mismo, los `finally` y los `async with` de adentro corren (así se cierra la
    conexión con el modelo) y `esperar` termina con `TimeoutError`.

    En Java sería parecido a `future.get(5, TimeUnit.SECONDS)` seguido de
    `future.cancel(true)`. Dos diferencias:

    - Acá no hay otro hilo que interrumpir: todo pasa en el event loop, y solo se
      puede cortar en un `await`. No queda ninguna tarea suelta: lo cancelado es la
      misma corrutina que estaba esperando.
    - El código común que corre en un hilo (`en_hilo`) no se puede cancelar: el
      orquestador deja de esperarlo, pero el hilo sigue hasta terminar. Por eso las
      tools reciben además su propio plazo de red (`catalogo/plazo.py`), que hace
      que terminen solas a la misma hora.

    El mismo `Corte` sirve para varias esperas seguidas (cada pedazo del modelo):
    todas comparten la hora límite, y `correr_hasta` la puede mover. El límite rige
    solo mientras se espera adentro de `esperar`: lo que pasa entre una espera y la
    siguiente (por ejemplo, un `yield` que le entrega un evento a la vista) no se
    cancela.

    Es una clase propia, y no `asyncio.timeout_at` directo, para tener un solo lugar
    que los tests reemplazan por un corte de mentira (`tests_plazo.CorteFalso`).
    """

    def __init__(self, segundos):
        # La hora del event loop (segundos, como `time.monotonic`) en que vence.
        self._vence = asyncio.get_running_loop().time() + max(0.0, segundos)
        self._vencio = False

    async def esperar(self, cosa):
        """Espera `cosa` (una corrutina) y devuelve su resultado, o `TimeoutError`."""
        limite = asyncio.timeout_at(self._vence)
        try:
            async with limite:
                return await cosa
        except TimeoutError:
            # `expired()` distingue este límite de un `TimeoutError` que venga de
            # otro lado (un socket, el SDK del modelo).
            if limite.expired():
                self._vencio = True
            raise

    def correr_hasta(self, segundos):
        """Mueve el límite: desde ahora, quedan `segundos`."""
        self._vence = asyncio.get_running_loop().time() + max(0.0, segundos)

    def vencio(self):
        """`True` si alguna espera se cortó por este límite (y no por otro error)."""
        return self._vencio


async def recorrer(flujo, corte):
    """Como `async for item in flujo`, pero cada espera tiene el límite de `corte`.

    `flujo` es el generador async del proveedor. `anext(flujo, _FIN)` pide el
    próximo elemento (es lo que hace `async for` por dentro) y devuelve `_FIN` si no
    hay más. `aclosing` garantiza que el flujo se cierre al salir, pase lo que pase:
    es lo que cierra la conexión con el modelo si el turno se corta.
    """
    async with aclosing(flujo):
        while True:
            item = await corte.esperar(anext(flujo, _FIN))
            if item is _FIN:
                return
            yield item


class Plazo:
    """El tiempo total de un turno y cuánto queda.

    `reloj` es una función que devuelve segundos (por defecto la da el orquestador:
    `_ahora`, que es `time.monotonic`). Va por parámetro para que los tests pasen un
    reloj de mentira y no haya que dormir de verdad (como inyectar un `Clock`).
    """

    def __init__(self, segundos, reloj):
        self.total = segundos
        self._reloj = reloj
        self._inicio = reloj()

    def transcurrido(self):
        """Segundos desde que empezó el turno."""
        return self._reloj() - self._inicio

    def queda(self, reserva=0.0):
        """Segundos que quedan, guardando `reserva` para después. Nunca menos de 0."""
        return max(0.0, self.total - self.transcurrido() - reserva)

    def cortar(self, reserva=0.0):
        """Un `Corte` que vence cuando al plazo le quede solo la `reserva`."""
        return Corte(self.queda(reserva))
