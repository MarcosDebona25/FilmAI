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

_CORREO = r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
# Más cortas no son un nombre: «de» o «la» de «de la Cruz» aparecen en cualquier frase.
_LARGO_MINIMO_DE_PARTE = 3


def _plano(texto):
    """Minúsculas y sin tildes, con exactamente el mismo largo que `texto`.

    Se compara contra esta copia y se reemplaza en el original, así que cada
    posición de una tiene que valer para la otra.
    """
    return "".join(unicodedata.normalize("NFD", c)[0].lower()[0] for c in texto)


def _frase(texto):
    """Patrón de un texto de una o más palabras, con cualquier espacio entre ellas."""
    return r"\s+".join(re.escape(parte) for parte in _plano(texto).split())


def _candidatos(usuario, alcance):
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
