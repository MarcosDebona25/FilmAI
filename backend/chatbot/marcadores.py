"""Los marcadores `[[n]]`: cómo el modelo elige qué títulos llevan tarjeta.

Cada título que devuelve una tool lleva un número de referencia `ref`, por orden de
aparición en el turno. Para recomendar uno, el modelo escribe `[[n]]` en lugar de su
nombre. Este módulo cambia, mientras el texto sale por SSE, cada marcador por
`**Título** (año)` y suma la tarjeta de ese título. Así lo que se lee y lo que se ve
como tarjeta salen del mismo lugar y no pueden contradecirse.

Lo usa: `orquestador.py`.
Usa: `ContextoTurno` de `tools/turno.py` (de ahí salen los candidatos).
"""

import logging
import re

logger = logging.getLogger(__name__)

# Las tarjetas que se muestran como mucho. Más títulos van en el texto, sin tarjeta.
TOPE_TARJETAS = 3

# Un marcador completo: `[[` + de 1 a 3 dígitos + `]]`. Los paréntesis hacen
# «grupos»: el primero captura el espacio que lo precede (por si hay que borrarlo)
# y el segundo, el número. `\s` es cualquier espacio o salto de línea.
_MARCADOR = re.compile(r"(\s?)\[\[(\d{1,3})\]\]")

# Cómo puede terminar un texto que todavía no está completo, para no mostrar
# `[[3` a medias. `\Z` es «el final del texto». Reconoce, en este orden y siempre
# pegado al final: un espacio opcional y después `[`, `[[`, `[[3` o `[[3]`. Hasta 3
# dígitos, como el marcador. Cada `(?: ... )?` es un tramo opcional.
_COLA_INCOMPLETA = re.compile(r"\s?(?:\[(?:\[(?:\d{1,3}\]?)?)?)?\Z")

# Lo que queda retenido si el stream termina en medio de un marcador: se descarta.
_MARCADOR_CORTADO = re.compile(r"\s?\[\[\d{0,3}\]?\Z")

# Una negrita escrita por el modelo (`**algo**`), que en el prompt está reservada
# para los títulos que pone este filtro.
_NEGRITA = re.compile(r"\*\*[^*\n]+\*\*")


class FiltroDeMarcadores:
    """Reemplaza los `[[n]]` de un texto que llega en trozos.

    El texto del modelo llega de a pedacitos (los `chunks` del stream) y un marcador
    puede quedar cortado entre dos: `[[` en uno y `3]]` en el siguiente. Si cada
    trozo se procesara solo, el `[[` saldría al usuario antes de saber qué viene
    después. Por eso el filtro **retiene** el final de cada trozo cuando podría ser
    el comienzo de un marcador (como mucho 6 caracteres) y lo junta con el trozo
    siguiente. Es un `StringBuilder` con memoria, que en Java sería un
    `FilterReader` con un buffer de lookahead.

    Uso:
        filtro = FiltroDeMarcadores(ctx)
        for trozo in stream:
            salida = filtro.alimentar(trozo)   # lo que ya se puede mostrar
        salida = filtro.cerrar()               # el resto, al terminar el texto

    Las tarjetas se suman a `ctx.tarjetas` a medida que aparecen los marcadores.
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.pendiente = ""
        self.validos = 0
        self.invalidos = 0
        # Todo lo que el modelo escribió, antes de reemplazar: sirve para contar
        # las negritas que puso por su cuenta (diagnóstico y búsqueda forzada).
        self._crudo = []

    @property
    def negritas(self):
        """Cuántas `**negritas**` escribió el modelo por su cuenta."""
        return len(_NEGRITA.findall("".join(self._crudo)))

    def alimentar(self, trozo):
        """Recibe un trozo y devuelve el texto que ya se puede mostrar."""
        self._crudo.append(trozo)
        texto = self.pendiente + trozo
        # `search` encuentra dónde empieza la cola que podría ser un marcador a
        # medias; todo lo anterior es seguro. Siempre hay coincidencia: el patrón
        # acepta una cola vacía.
        corte = _COLA_INCOMPLETA.search(texto).start()
        seguro, self.pendiente = texto[:corte], texto[corte:]
        return _MARCADOR.sub(self._reemplazar, seguro)

    def cerrar(self):
        """El texto retenido, cuando ya no va a llegar más. Un `[[3` sin cerrar se descarta."""
        resto, self.pendiente = self.pendiente, ""
        return _MARCADOR_CORTADO.sub("", resto)

    def _reemplazar(self, coincidencia):
        """Qué se escribe en lugar de un marcador completo (se usa en `re.sub`)."""
        espacio, numero = coincidencia.group(1), int(coincidencia.group(2))
        candidatos = self.ctx.candidatos()
        titulo = candidatos.get(numero)
        if titulo is None:
            # Se borra el marcador y el espacio anterior: «Mirá [[9]].» → «Mirá.».
            # Solo se loguea el número: el resto es texto del modelo.
            self.invalidos += 1
            logger.warning(
                "Marcador [[%d]] sin candidato (el turno tiene %d)",
                numero,
                len(candidatos),
            )
            return ""
        self.validos += 1
        self._sumar_tarjeta(titulo)
        anio = titulo.get("anio")
        return f"{espacio}**{titulo['titulo']}**" + (f" ({anio})" if anio else "")

    def _sumar_tarjeta(self, titulo):
        """La tarjeta del título, si no está ya y no se pasó del tope."""
        if len(self.ctx.tarjetas) == TOPE_TARJETAS or titulo in self.ctx.tarjetas:
            return
        self.ctx.tarjetas.append(titulo)


def recomienda_sin_buscar(texto, candidatos):
    """¿Este texto recomienda títulos sin que ninguna tool los haya devuelto?

    Es la señal para repetir la llamada obligando al modelo a buscar. Cuenta como
    recomendar: un marcador `[[n]]` sin candidato `n`, o una `**negrita**` (el prompt
    la reserva para los títulos y el modelo, sin buscar, los escribiría de memoria).
    `candidatos` es `{ref: título}` (ver `ContextoTurno.candidatos`).
    """
    inventados = any(int(n) not in candidatos for _, n in _MARCADOR.findall(texto))
    return inventados or bool(_NEGRITA.search(texto))
