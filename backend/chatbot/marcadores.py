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
import unicodedata

logger = logging.getLogger(__name__)

# Las tarjetas que se muestran como mucho. Más títulos van en el texto, sin tarjeta.
TOPE_TARJETAS = 3

# Un marcador completo: `[[` + de 1 a 3 dígitos + `]]`. Los paréntesis hacen
# «grupos», que se leen con `group(n)`: el 1 captura el espacio que lo precede (por
# si hay que borrarlo), el 2 una negrita que lo abre y el 3 el número. El modelo a
# veces lo escribe envuelto en negrita (`**[[3]]**`) o con el año (`[[3]] (1999)`):
# como el filtro agrega las dos cosas por su cuenta, acá se absorben para no
# duplicarlas. `(?(2)\*\*)` es un condicional: pide el `**` de cierre solo si hubo
# uno de apertura. `\s` es cualquier espacio o salto de línea.
_MARCADOR = re.compile(
    r"(\s?)(\*\*)?\[\[(\d{1,3})\]\](?:\s?\(\d{4}\))?(?(2)\*\*)(?:\s?\(\d{4}\))?"
)

# Los únicos caracteres que pueden formar parte de un marcador a medias: espacios,
# `*`, `[`, `]`, dígitos y paréntesis. Mientras el final del texto sea una racha de
# estos (de hasta 26: el marcador más largo, `**[[123]] (1999)**`, tiene 18 más los
# espacios), el filtro no sabe todavía si es un marcador (ver `_cola_incompleta`).
_RACHA_POSIBLE = re.compile(r"[\s*\[\]\d()]{0,26}\Z")

# Lo que queda retenido si el stream termina en medio de un marcador: se descarta.
_MARCADOR_CORTADO = re.compile(r"\s?(?:\*\*)?\[\[\d{0,3}(?:\]\]?)?[\s(\d)*]*\Z")

# Una negrita escrita por el modelo (`**algo**`), que en el prompt está reservada
# para los títulos que pone este filtro.
_NEGRITA = re.compile(r"\*\*[^*\n]+\*\*")


def _cola_incompleta(texto):
    """Dónde empieza el final del texto que podría ser un marcador a medias.

    Devuelve la posición desde la que hay que retener (`len(texto)` si no hay nada
    que retener). Mira la racha final de caracteres posibles en un marcador
    (`_RACHA_POSIBLE`) y retiene desde su primer `*` o `[`, más el espacio que lo
    precede. Retiene de más a propósito: un `(19` suelto también se queda esperando
    al próximo trozo. No pasa nada: se suelta enseguida, apenas llega algo que no
    encaja. Sin `*` ni `[`, solo se retiene un espacio final, por si lo que sigue es
    un marcador inválido que se borra junto con ese espacio.
    """
    racha = _RACHA_POSIBLE.search(texto)
    inicio, cola = racha.start(), racha.group()
    disparadores = [i for i in (cola.find("*"), cola.find("[")) if i != -1]
    if not disparadores:
        return len(texto) - 1 if texto[-1:].isspace() else len(texto)
    desde = min(disparadores)
    if desde > 0 and cola[desde - 1].isspace():
        desde -= 1
    return inicio + desde


class FiltroDeMarcadores:
    """Reemplaza los `[[n]]` de un texto que llega en trozos.

    El texto del modelo llega de a pedacitos (los `chunks` del stream) y un marcador
    puede quedar cortado entre dos: `[[` en uno y `3]]` en el siguiente. Si cada
    trozo se procesara solo, el `[[` saldría al usuario antes de saber qué viene
    después. Por eso el filtro **retiene** el final de cada trozo cuando podría ser
    el comienzo de un marcador (unos 25 caracteres como mucho) y lo junta con el trozo
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
        # Todo lo anterior a la cola incompleta es seguro: se puede reemplazar ya.
        corte = _cola_incompleta(texto)
        seguro, self.pendiente = texto[:corte], texto[corte:]
        return _MARCADOR.sub(self._reemplazar, seguro)

    def cerrar(self):
        """El texto retenido, cuando ya no va a llegar más. Un `[[3` sin cerrar se descarta."""
        resto, self.pendiente = self.pendiente, ""
        # Puede quedar un marcador completo (con un año a medias detrás): se resuelve
        # igual que en `alimentar`. Lo que siga sin cerrar se descarta.
        return _MARCADOR_CORTADO.sub("", _MARCADOR.sub(self._reemplazar, resto))

    def _reemplazar(self, coincidencia):
        """Qué se escribe en lugar de un marcador completo (se usa en `re.sub`)."""
        espacio, numero = coincidencia.group(1), int(coincidencia.group(3))
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
    inventados = any(
        int(m.group(3)) not in candidatos for m in _MARCADOR.finditer(texto)
    )
    return inventados or bool(_NEGRITA.search(texto))


def _normalizar(texto):
    """El texto para comparar títulos: sin tildes, en minúsculas y sin puntuación.

    `NFKD` separa cada letra de su tilde («é» → «e» más la marca de la tilde); después se descartan las
    marcas sueltas. Todo lo que no es letra ni número pasa a ser un espacio, y los
    espacios repetidos se juntan: «¡Amélie!» y «amelie» quedan iguales.
    """
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(re.sub(r"[\W_]+", " ", sin_tildes.casefold()).split())


def _nombres(ctx, clave, titulo):
    """Los nombres con los que un candidato puede aparecer en el texto, normalizados."""
    crudos = (titulo.get("titulo"), ctx.originales.get(clave))
    return {n for n in (_normalizar(c) for c in crudos if c) if n}


def tarjetas_sin_marcadores(texto, ctx):
    """Las tarjetas de los candidatos que el texto nombra sin haber usado `[[n]]`.

    Es la red de seguridad del final del turno (14/11/2026): el modelo buscó y
    recomendó en texto plano, así que sin esto la respuesta saldría sin tarjetas. No
    toca el texto, que ya se transmitió: solo devuelve qué tarjetas sumar, en orden
    de aparición y hasta `TOPE_TARJETAS`, sin repetir.

    Cómo decide:
    - Compara contra el título y el título original de cada candidato, normalizados
      (`_normalizar`) y como palabras completas: el patrón no encuentra «Up»
      dentro de «supuesto». Se arma con `(?<!\\w)` y `(?!\\w)`, que miran un
      carácter hacia atrás y hacia adelante sin consumirlo.
    - Si dos candidatos se llaman igual (película y serie), gana el que el texto
      acompaña con su año justo detrás; si ninguno, el primero (el de menor `ref`).
    - Un nombre que está dentro de otro más largo que también aparece («Up» dentro
      de «Up in the Air») no cuenta, salvo que el texto lo use también por su cuenta.
    """
    normal = _normalizar(texto)
    # (inicio, fin, nombre, clave) de cada aparición de cada candidato.
    apariciones = []
    for clave, titulo in ctx.encontrados.items():
        for nombre in _nombres(ctx, clave, titulo):
            for m in re.finditer(rf"(?<!\w){re.escape(nombre)}(?!\w)", normal):
                apariciones.append((m.start(), m.end(), nombre, clave))

    # Una aparición cubierta por otra más larga no cuenta.
    def tapada(a):
        return any(
            b[0] <= a[0] and a[1] <= b[1] and (b[1] - b[0]) > (a[1] - a[0])
            for b in apariciones
        )

    por_lugar = {}
    for a in apariciones:
        if not tapada(a):
            por_lugar.setdefault((a[0], a[1]), []).append(a[3])

    elegidos = {}  # clave -> posición de su primera aparición
    claves = list(ctx.encontrados)
    for (inicio, fin), homonimos in sorted(por_lugar.items()):
        homonimos = sorted(set(homonimos), key=claves.index)
        # El año que el texto pone justo después del nombre («Dune (2021)»).
        anio = re.match(r"\s?(\d{4})(?!\d)", normal[fin:])
        elegida = next(
            (
                c
                for c in homonimos
                if anio and str(ctx.encontrados[c].get("anio")) == anio.group(1)
            ),
            homonimos[0],
        )
        elegidos.setdefault(elegida, inicio)

    en_orden = sorted(elegidos, key=elegidos.get)
    return [ctx.encontrados[c] for c in en_orden[:TOPE_TARJETAS]]
