"""En qué idioma escribió el usuario su mensaje: español, inglés o «no se sabe».

Por qué está en el código y no en el prompt: con el perfil (sus reseñas) y el
historial en español, el modelo contestaba en español a un mensaje en inglés,
aunque el prompt le pedía seguir el idioma del mensaje. Cuando se le nombra el
idioma («Reply in English.») lo cumple (verificado contra DeepSeek el 06/11/2026).

El producto solo escribe en español o en inglés, así que al detector le alcanza con
reconocer esos dos de forma positiva. Cualquier otra cosa (portugués, italiano,
francés, un título suelto, un «jaja») es «no se sabe» y el chatbot responde en el
idioma de la cuenta. La primera versión contaba palabras comunes de cada idioma y
tomaba un mensaje en portugués por español (22/11/2026); mantener listas por idioma
no escala, así que ahora decide un modelo de fastText (`fast-langdetect`).

Lo usa: `orquestador._preparar()`, que con `None` usa el idioma del turno.
Modelo y benchmark: `docs/decisiones.md`, entrada del 22/11/2026.
"""

import logging
from functools import cache

from fast_langdetect import LangDetectConfig, LangDetector

logger = logging.getLogger(__name__)

# Con menos confianza que esto el modelo está adivinando: es preferible caer al
# idioma de la cuenta que contestar en el idioma equivocado. 0,5 dio 75 aciertos de
# 78 mensajes etiquetados, con un solo error grave.
UMBRAL_DE_CONFIANZA = 0.5
_IDIOMAS_SOPORTADOS = frozenset({"es", "en"})


@cache
def _detector():
    """Un único detector por proceso, creado en el primer uso.

    Cargar el modelo tarda ~0,18 s y ocupa ~26 MB de RAM: se paga una vez, no por
    mensaje, y no al importar el módulo (así `manage.py` y los tests que no lo usan
    no cargan nada). `@cache` hace de singleton perezoso.

    `max_input_length=None` desactiva el recorte a 80 caracteres que trae la
    librería (y su log INFO en cada mensaje largo). Medido: mismos aciertos. El
    mensaje ya llega acotado por `LARGO_MAXIMO_DEL_MENSAJE` (500) en el serializer.
    """
    return LangDetector(LangDetectConfig(max_input_length=None))


def detectar_idioma(texto):
    """`"es"`, `"en"` o `None` si el mensaje no alcanza para saberlo.

    `None` no es un error: significa «usá el idioma de la cuenta».
    """
    if not texto or not texto.strip():
        return None
    try:
        # `model="lite"` es obligatorio: el valor por defecto («auto») descarga el
        # modelo completo de 126 MB. Con `k=1` vuelve solo el idioma más probable.
        mejor = _detector().detect(texto, model="lite", k=1)[0]
    except Exception as error:
        # La detección es una ayuda: nunca puede romper un turno. Se loguea solo el
        # tipo de error: ni el texto ni el mensaje de la excepción, que podría
        # citarlo, porque es del usuario.
        logger.warning(
            "No se pudo detectar el idioma del mensaje (%s)", type(error).__name__
        )
        return None
    if mejor["lang"] in _IDIOMAS_SOPORTADOS and mejor["score"] >= UMBRAL_DE_CONFIANZA:
        return mejor["lang"]
    return None
