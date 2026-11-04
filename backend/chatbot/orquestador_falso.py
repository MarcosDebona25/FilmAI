"""Un `responder()` de mentira que cumple el contrato de `chatbot/eventos.py`.

Sirve para construir y probar la vista SSE (PR5) antes de que exista el
orquestador real (PR3): reproduce un guion fijo de eventos, puede tardar entre
uno y otro (para probar la cancelación y el tiempo máximo del turno) y puede
fallar en un paso dado (para probar el evento `error`). Cuando el PR3 entre en
`main`, la vista lo reemplaza por `orquestador.responder` cambiando una línea.
"""

import asyncio
from collections.abc import AsyncIterator, Sequence

from chatbot.eventos import ErrorDelTurno, Estado, Evento, Resultado, Texto

GUION_BASICO: tuple[Evento, ...] = (
    Estado(code="searching"),
    Texto(delta="Te recomiendo "),
    Texto(delta="*Moon*, "),
    Texto(delta="un drama de ciencia ficción íntimo."),
    Resultado(
        texto="Te recomiendo *Moon*, un drama de ciencia ficción íntimo.",
        tarjetas=[
            {
                "id_tmdb": 17431,
                "tipo": "movie",
                "titulo": "Moon",
                "poster": None,
                "anio": 2009,
            }
        ],
    ),
)


class OrquestadorFalso:
    """Reproduce `guion` con `demora` segundos antes de cada evento.

    Con `falla_en=n` entrega los primeros `n` eventos y lanza `ErrorDelTurno`,
    como haría el real si DeepSeek se cae a mitad del turno.
    """

    def __init__(
        self,
        guion: Sequence[Evento] = GUION_BASICO,
        demora: float = 0.0,
        falla_en: int | None = None,
    ):
        self.guion = tuple(guion)
        self.demora = demora
        self.falla_en = falla_en
        # Lo que recibió cada llamada, para que los tests de la vista lo verifiquen.
        self.llamadas: list[tuple] = []

    async def responder(self, chat, texto: str, idioma: str) -> AsyncIterator[Evento]:
        self.llamadas.append((chat, texto, idioma))
        for paso, evento in enumerate(self.guion):
            if paso == self.falla_en:
                raise ErrorDelTurno("Falla simulada por OrquestadorFalso")
            # `sleep(0)` también cede el control: el loop puede cancelar acá.
            await asyncio.sleep(self.demora)
            yield evento
