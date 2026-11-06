"""En qué idioma escribió el usuario su mensaje: español, inglés o «no se sabe».

Por qué está en el código y no en el prompt: con el perfil (sus reseñas) y el
historial en español, el modelo contestaba en español a un mensaje en inglés,
aunque el prompt le pedía seguir el idioma del mensaje. Cuando se le nombra el
idioma («Reply in English.») lo cumple (verificado contra DeepSeek el 06/11/2026).

Es una heurística, no una librería: con dos idiomas alcanza con contar palabras
muy comunes de cada uno, y así es determinista y no suma dependencias. Cada
palabra cuenta una vez, para que un título («The Lord of the Rings») no pese más
que el pedido que lo rodea.

Lo usa: `orquestador._preparar()`, que con `None` usa el idioma del turno.
"""

import re

# Palabras frecuentes que existen en un solo idioma. Las que están en los dos
# («me», «no», «a», «series», «similar») quedan afuera porque no deciden nada.
_ESPANOL = frozenset(
    """el la los las un una unas unos que qué de del y en es son por para con como
    algo pero más mas muy mi tu quiero quisiera recomendame recomendá recomiendas
    recomiendes cuál cual cuáles ver vi película películas peli pelis serie parecida
    parecido parecidas parecidos otra otro otras otros sin este esta estos estas
    hola gracias dale también tiene hay alguna alguno corta corto larga largo
    mostrame dame busca buscá""".split()
)
_INGLES = frozenset(
    """the an and of to in is are for with like something but more very my i want
    would recommend what which watch watched movie movies film films show shows
    another other without this that these those hi hello thanks please some any
    lighter shorter longer short long give find""".split()
)
_SIGNOS_DEL_ESPANOL = re.compile(r"[ñ¿¡áéíóú]")
_PALABRA = re.compile(r"[a-zñáéíóúü']+")


def detectar_idioma(texto):
    """`"es"`, `"en"` o `None` si el mensaje no alcanza para saberlo."""
    texto = texto.lower()
    palabras = set(_PALABRA.findall(texto))
    espanol = len(palabras & _ESPANOL) + bool(_SIGNOS_DEL_ESPANOL.search(texto))
    ingles = len(palabras & _INGLES)
    if espanol > ingles:
        return "es"
    if ingles > espanol:
        return "en"
    return None
