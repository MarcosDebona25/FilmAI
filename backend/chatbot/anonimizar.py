"""Saca los datos personales de lo que viaja al proveedor del chatbot (RNF #3).

Actúa solo sobre la copia que se manda: lo que se guarda y se muestra queda como
lo escribió el usuario. Los resultados de TMDB no pasan por acá, porque no son
datos del usuario y «[usuario] Scorsese» solo los ensuciaría.

Lo usan: `contexto.py` (reseñas), `tools/personales.py` (nombres de listas) y el
orquestador (PR 3), para el mensaje y el historial.
"""

import re
import unicodedata

# Lo que trata sobre el usuario (perfil, reseñas, listas): todo se reemplaza.
ESTRICTO = "estricto"
# Lo que escribe en el chat: un nombre suelto queda, para poder pedir a Mark
# Ruffalo siendo Mark. Se reemplaza el nombre completo y el nombre de usuario.
CONVERSACION = "conversacion"

# La parte local (antes de la `@`) admite también `'`, `#`, `!` y `%`: «o'neil@gmail.com»
# es un correo válido. El `-` va al final de los corchetes: en el medio sería un rango.
_CORREO = r"[\w.+'#!%-]+@[\w-]+(?:\.[\w-]+)+"
# Más cortas no son un nombre: «de» o «la» de «de la Cruz» aparecen en cualquier frase.
_LARGO_MINIMO_DE_PARTE = 3


# Apóstrofos que se ven iguales: el teclado del celular escribe el de «O'Connor»
# curvo (U+2019) y el nombre guardado puede tener el recto ('). Todos pasan a ser el
# recto. También lo usa el orquestador para comparar títulos.
APOSTROFOS = {"\u2019": "'", "\u2018": "'", "\u02bc": "'"}

# Letras que Unicode no descompone en «letra + tilde» (`NFD` no las toca): «Łukasz» y
# «Lukasz» eran para el programa dos palabras distintas. Cada una se pliega a la
# letra base más parecida, una por una, porque `_plano()` no puede cambiar el largo.
# U+0131 (i sin punto, turco), `ł` (polaco), `ø` (danés/noruego), `đ` (croata) y `ð`
# (islandés), `ħ` (maltés) y `ŧ` (sami). Todas llegan ya en minúscula.
LETRAS_SIN_DESCOMPONER = {
    "\u0131": "i",  # i sin punto: ruff avisa si va escrita tal cual
    "ł": "l",
    "ø": "o",
    "đ": "d",
    "ð": "d",
    "ħ": "h",
    "ŧ": "t",
}

# Letras que equivalen a dos: `ß` se escribe «ss» en un teclado sin ella. No entran en
# `_plano()` (cambiarían el largo): se resuelven en el patrón, que acepta cualquiera
# de las dos formas, la letra o su par, sea cuál sea la que está guardada.
_DOBLES = {"ß": "ss", "æ": "ae", "œ": "oe", "þ": "th"}
_PARTE_DOBLE = re.compile("(" + "|".join([*_DOBLES, *_DOBLES.values()]) + ")")
_AL_REVES = {**_DOBLES, **{par: letra for letra, par in _DOBLES.items()}}


def _plano(texto):
    """Minúsculas y sin tildes, con exactamente el mismo largo que `texto`.

    Se compara contra esta copia y se reemplaza en el original, así que cada
    posición de una tiene que valer para la otra.

    Antes pasa el texto a `NFC`, que junta cada letra con su tilde suelta («e» +
    U+0301 pasa a ser «é»): un nombre guardado «descompuesto» (NFD) se ve igual que
    uno compuesto, pero son otros caracteres, y sin esto no coincidían. Si `texto` ya
    está en NFC (como en `anonimizar`), el largo no cambia.
    """
    return "".join(_letra_plana(c) for c in unicodedata.normalize("NFC", texto))


def _letra_plana(caracter):
    """Un carácter, plegado a su letra base en minúscula (siempre uno solo)."""
    if caracter in APOSTROFOS:
        return APOSTROFOS[caracter]
    # `NFD` separa «é» en «e» + tilde: nos quedamos con la letra, sin la tilde.
    base = unicodedata.normalize("NFD", caracter)[0].lower()[0]
    return LETRAS_SIN_DESCOMPONER.get(base, base)


def _frase(texto):
    """Patrón de un texto de una o más palabras, con cualquier espacio entre ellas."""
    return r"\s+".join(_palabra(parte) for parte in _plano(texto).split())


def _palabra(palabra):
    """Patrón de una palabra ya plana: `ß` y «ss» valen lo mismo (y `æ`/«ae», etc.)."""
    # `split` con paréntesis conserva los separadores: las posiciones impares son las
    # letras dobles o sus pares, y cada una acepta las dos formas.
    trozos = _PARTE_DOBLE.split(palabra)
    return "".join(
        f"(?:{re.escape(trozo)}|{_AL_REVES[trozo]})" if i % 2 else re.escape(trozo)
        for i, trozo in enumerate(trozos)
    )


def _candidatos(usuario, alcance):
    """Los textos a reemplazar, según el alcance.

    Siempre el nombre completo. En `ESTRICTO`, además, cada parte suelta y el usuario.
    En `CONVERSACION`, el usuario, salvo que sea igual al nombre o al apellido.
    """
    nombre = usuario.nombre.strip()
    apellido = usuario.apellido.strip()
    nombre_usuario = usuario.nombre_usuario.strip()

    candidatos = [f"{nombre} {apellido}"] if nombre and apellido else []
    if alcance == ESTRICTO:
        candidatos += [nombre, apellido, nombre_usuario]
        candidatos += [
            parte
            for parte in f"{nombre} {apellido}".split()
            if len(parte) >= _LARGO_MINIMO_DE_PARTE
        ]
    elif _plano(nombre_usuario) not in (_plano(nombre), _plano(apellido)):
        candidatos.append(nombre_usuario)
    return [candidato for candidato in candidatos if candidato]


def anonimizar(texto, usuario, alcance):
    """Reemplaza correos por `[correo]` y datos del usuario por `[usuario]`."""
    texto = unicodedata.normalize("NFC", texto)
    # Lo más largo primero: «Juan Pérez» es un solo reemplazo, no dos.
    frases = sorted(
        {_frase(candidato) for candidato in _candidatos(usuario, alcance)},
        key=len,
        reverse=True,
    )
    patron = f"(?P<correo>{_CORREO})"
    if frases:
        patron += rf"|(?<!\w)(?:{'|'.join(frases)})(?!\w)"

    # Una sola pasada: un reemplazo ya hecho no vuelve a analizarse.
    partes, fin = [], 0
    for coincidencia in re.finditer(patron, _plano(texto)):
        partes.append(texto[fin : coincidencia.start()])
        partes.append("[correo]" if coincidencia["correo"] else "[usuario]")
        fin = coincidencia.end()
    partes.append(texto[fin:])
    return "".join(partes)
