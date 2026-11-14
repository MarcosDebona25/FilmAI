"""Los marcadores `[[n]]`: cómo el modelo elige qué títulos llevan tarjeta.

Cada título que devuelve una tool lleva un número de referencia `ref`, por orden de
aparición en el turno. Para recomendar uno, el modelo escribe `[[n]]` en lugar de su
nombre. Este módulo cambia, mientras el texto sale por SSE, cada marcador por
`**Título** (año)` y suma la tarjeta de ese título. Así lo que se lee y lo que se ve
como tarjeta salen del mismo lugar y no pueden contradecirse.

Lo usa: `orquestador.py`.
Usa: `ContextoTurno` de `tools/turno.py` (de ahí salen los candidatos) y el catálogo
de TMDB (`una_parte_por_saga` le pregunta a qué colección pertenece cada película).
"""

import logging
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait as esperar

from catalogo.services.tmdb import get_catalog_service

logger = logging.getLogger(__name__)

# Las tarjetas que se muestran como mucho. Más títulos van en el texto, sin tarjeta.
TOPE_TARJETAS = 3

# Cuánto se espera, en total, a que TMDB diga las colecciones (segundos). Medido el
# 14/11/2026: un detalle tarda 180-540 ms en frío (570 ms tres a la vez) y 1,3 ms con
# caché. 2 s cubre dos rondas en frío y un TMDB algo lento; pasado ese tiempo la
# respuesta sale con las tarjetas como si no existiera esta regla. Es menos que el
# `TMDB_TIMEOUT` de una llamada (5 s) a propósito: acá, esperar de más le cuesta al
# usuario más que mostrar una parte repetida.
PRESUPUESTO_SAGAS = 2.0

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
        # Los títulos que el modelo marcó, en orden y sin repetir, SIN el tope: el
        # orquestador los usa al final para saltear las partes repetidas de una saga
        # (`una_parte_por_saga`) y que el lugar lo ocupe el título que sigue.
        self.mencionados = []
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
        if titulo not in self.mencionados:
            self.mencionados.append(titulo)
        self._sumar_tarjeta(titulo)
        anio = titulo.get("anio")
        return f"{espacio}**{titulo['titulo']}**" + (f" ({anio})" if anio else "")

    def _sumar_tarjeta(self, titulo):
        """La tarjeta del título, si no está ya y no se pasó del tope."""
        if len(self.ctx.tarjetas) == TOPE_TARJETAS or titulo in self.ctx.tarjetas:
            return
        self.ctx.tarjetas.append(titulo)


def _coleccion_de(id_tmdb):
    """El id de la colección (saga) de una película en TMDB, o `None` si no tiene.

    TMDB agrupa las partes de una saga en una «colección» y la informa en el detalle
    de cada película: `{"belongs_to_collection": {"id": 726871, "name": "Dune
    Collection", ...}}`, o `null` si es suelta. `get_catalog_service()` ya cachea el
    detalle 24 h en Redis. Si TMDB falla, la excepción sube: la maneja el que llama.
    """
    detalle = get_catalog_service().get_movie_detail(id_tmdb)
    coleccion = detalle.get("belongs_to_collection")
    return coleccion.get("id") if isinstance(coleccion, dict) else None


def una_parte_por_saga(titulos, tope=TOPE_TARJETAS, presupuesto=PRESUPUESTO_SAGAS):
    """Las tarjetas de la respuesta, sin dos películas de la misma saga.

    Recibe los títulos que el texto recomendó, en orden y sin el tope aplicado, y
    devuelve `(tarjetas, descartadas)`: las primeras `tope` que no repiten colección
    y cuántas se saltearon por ser de una saga que ya tenía tarjeta. La parte
    descartada sigue nombrada en el texto (no se toca): solo pierde la tarjeta, y su
    lugar lo ocupa el título que sigue. Las series no tienen colección en TMDB, así
    que nunca se descartan.

    Cómo evita llamadas de más:
    - Con menos de dos películas no hay con qué chocar: no se le pregunta nada a TMDB.
    - Se miran los títulos de a tandas del tamaño de los lugares que faltan, y los
      detalles de cada tanda se piden a la vez (un hilo por película). Lo normal es
      una sola tanda; si hubo un descarte, una segunda con los reemplazos.

    Nunca rompe el turno: si TMDB falla o se pasa del `presupuesto` (segundos en
    total), esa película entra como siempre, sin saber su colección.
    """
    if sum(t["tipo"] == "movie" for t in titulos) < 2:
        return list(titulos[:tope]), 0
    limite = time.monotonic() + presupuesto
    tarjetas, vistas, descartadas = [], set(), 0
    pendientes = list(titulos)
    hilos = ThreadPoolExecutor(max_workers=tope)
    try:
        while pendientes and len(tarjetas) < tope:
            lugares = tope - len(tarjetas)
            tanda, pendientes = pendientes[:lugares], pendientes[lugares:]
            colecciones = _colecciones_de(hilos, tanda, limite)
            for titulo in tanda:
                coleccion = colecciones.get(titulo["id_tmdb"])
                if coleccion is not None and coleccion in vistas:
                    descartadas += 1
                    continue
                if coleccion is not None:
                    vistas.add(coleccion)
                tarjetas.append(titulo)
    finally:
        # `wait=False`: no se espera a un hilo colgado (el cliente HTTP tiene su
        # propio timeout, así que termina solo). Sin esto el `with` habitual
        # esperaría a todos y el presupuesto no serviría de nada.
        hilos.shutdown(wait=False, cancel_futures=True)
    return tarjetas, descartadas


def _colecciones_de(hilos, titulos, limite):
    """`{id_tmdb: id de colección}` de las películas de `titulos` que se pudieron leer.

    Las pide a la vez al `hilos` (un `ThreadPoolExecutor`: en Java, un
    `ExecutorService`) y espera hasta `limite` (un `time.monotonic()`). Las que
    fallan, tardan o no tienen colección no aparecen: es lo mismo que «no se sabe».
    """
    futuros = {
        hilos.submit(_coleccion_de, t["id_tmdb"]): t["id_tmdb"]
        for t in titulos
        if t["tipo"] == "movie"
    }
    hechos, _ = esperar(futuros, timeout=max(0.0, limite - time.monotonic()))
    colecciones = {}
    for futuro, id_tmdb in futuros.items():
        if futuro not in hechos:
            futuro.cancel()
            logger.warning("Saga: TMDB no contestó a tiempo (película %d)", id_tmdb)
            continue
        try:
            coleccion = futuro.result()
        except Exception as error:
            logger.warning("Saga: sin detalle de la película %d (%r)", id_tmdb, error)
            continue
        if coleccion is not None:
            colecciones[id_tmdb] = coleccion
    return colecciones


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


def _normalizar_con_mapa(texto):
    """El texto para comparar títulos, y de dónde salió cada carácter.

    Normalizar es: sin tildes, en minúsculas y sin puntuación. `NFKD` separa cada letra
    de su tilde («é» → «e» más la marca) y las marcas sueltas se descartan; todo lo que
    no es letra ni número pasa a ser un espacio y los espacios repetidos se juntan:
    «¡Amélie!» y «amelie» quedan iguales. Devuelve `(normalizado, origen)`, donde
    `origen[i]` es la posición en el texto original del carácter `i` del normalizado
    (sirve para mirar la puntuación que la normalización borró).
    """
    caracteres, origen = [], []
    for i, letra in enumerate(texto):
        for suelta in unicodedata.normalize("NFKD", letra):
            if unicodedata.combining(suelta):
                continue
            for c in suelta.casefold():
                if c.isalnum():
                    caracteres.append(c)
                    origen.append(i)
                elif caracteres and caracteres[-1] != " ":
                    caracteres.append(" ")
                    origen.append(i)
    if caracteres and caracteres[-1] == " ":
        caracteres.pop()
        origen.pop()
    return "".join(caracteres), origen


def _normalizar(texto):
    """Solo el texto normalizado (ver `_normalizar_con_mapa`)."""
    return _normalizar_con_mapa(texto)[0]


# Lo que, pegado al título, lo vuelve parte de otro («Dune» → «Dune Parte Dos»):
# «parte»/«part» + un número, un ordinal o un romano. Se mira sobre el texto ya
# normalizado, así que va sin tildes ni mayúsculas.
_CONTINUACION = re.compile(
    r" (?:parte|part) (?:\d+\w*|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez"
    r"|one|two|three|four|five|six|seven|eight|nine|ten|primera|segunda|tercera"
    r"|first|second|third|i{1,3}|iv|vi{0,3}|ix|x)(?!\w)"
)
# Los dos puntos pegados al título (con o sin la negrita que lo cierra): «Dune: …».
_DOS_PUNTOS = re.compile(r"\**:")


def _es_parte_de_otro_titulo(normal, origen, texto, fin):
    """¿Lo que viene justo después del título (que termina en `fin`) lo continúa?

    Cuenta un «:» pegado o un «Parte/Part» con número: el texto habla de «Dune:
    Parte Dos», no de «Dune», que puede ser otra película.
    """
    return bool(
        _CONTINUACION.match(normal, fin)
        or _DOS_PUNTOS.match(texto, origen[fin - 1] + 1)
    )


def _nombres(ctx, clave, titulo):
    """Los nombres con los que un candidato puede aparecer en el texto, normalizados."""
    crudos = (titulo.get("titulo"), ctx.originales.get(clave))
    return {n for n in (_normalizar(c) for c in crudos if c) if n}


def tarjetas_sin_marcadores(texto, ctx, pedido="", tope=TOPE_TARJETAS):
    """Las tarjetas de los candidatos que el texto nombra sin haber usado `[[n]]`.

    Es la red de seguridad del final del turno (14/11/2026): el modelo buscó y
    recomendó en texto plano, así que sin esto la respuesta saldría sin tarjetas. No
    toca el texto, que ya se transmitió: solo devuelve qué tarjetas sumar, en orden
    de aparición y hasta `tope` (`None`: todas, para que `una_parte_por_saga` elija),
    sin repetir.

    Cómo decide:
    - Compara contra el título y el título original de cada candidato, normalizados
      (`_normalizar`) y como palabras completas: el patrón no encuentra «Up»
      dentro de «supuesto». Se arma con `(?<!\\w)` y `(?!\\w)`, que miran un
      carácter hacia atrás y hacia adelante sin consumirlo.
    - Si dos candidatos se llaman igual (película y serie), gana el que el texto
      acompaña con su año justo detrás; si ninguno, el primero (el de menor `ref`).
    - Un nombre que está dentro de otro más largo que también aparece («Up» dentro
      de «Up in the Air») no cuenta, salvo que el texto lo use también por su cuenta.
    - Un nombre seguido de «:» o de «Parte/Part» y un número («Dune: Parte Dos») es
      otro título que no está entre los candidatos: no cuenta.
    - No hay tarjeta para los títulos que el usuario nombró en su `pedido` (son la
      referencia, no la recomendación) ni para los que ya vio (`ctx.vistas`).
    """
    normal, origen = _normalizar_con_mapa(texto)
    del_pedido = _normalizar(pedido)
    # (inicio, fin, nombre, clave) de cada aparición de cada candidato.
    apariciones = []
    # Los candidatos que no pueden tener tarjeta (los nombra el pedido o ya se vieron).
    excluidos = set()
    for clave, titulo in ctx.encontrados.items():
        nombres = _nombres(ctx, clave, titulo)
        if clave in ctx.vistas or any(
            re.search(rf"(?<!\w){re.escape(n)}(?!\w)", del_pedido) for n in nombres
        ):
            excluidos.add(clave)
        for nombre in nombres:
            for m in re.finditer(rf"(?<!\w){re.escape(nombre)}(?!\w)", normal):
                if not _es_parte_de_otro_titulo(normal, origen, texto, m.end()):
                    apariciones.append((m.start(), m.end(), nombre, clave))

    # Una aparición cubierta por otra más larga no cuenta.
    def tapada(a):
        return any(
            b[0] <= a[0] and a[1] <= b[1] and (b[1] - b[0]) > (a[1] - a[0])
            for b in apariciones
        )

    por_lugar = {}
    for a in apariciones:
        if a[3] not in excluidos and not tapada(a):
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
    return [ctx.encontrados[c] for c in en_orden[:tope]]
