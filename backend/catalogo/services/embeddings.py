"""Texto a embeber, su huella, y el punto de enchufe del proveedor (C-04a).

El vector de una producción se calcula a partir de un texto: este módulo
decide cuál es ese texto y cómo detectar que quedó viejo. La llamada al
proveedor que convierte texto en vector (Ollama/bge-m3) es lo único que falta,
y queda aislada en `generar_vector()` para que B-06 la reemplace sin tocar
nada más.
"""

import hashlib

# Identifica qué modelo produjo cada vector: vectores de modelos distintos no
# son comparables entre sí, así que un cambio acá obliga a regenerarlos.
# B-06 lo reemplaza por el identificador real (p. ej. "bge-m3").
MODEL_VERSION = "stub-v1"

# Etiquetas en inglés y en orden fijo: el corpus de TMDB está en inglés y
# bge-m3 fue entrenado con texto etiquetado de esta forma (decisión
# 08/09/2026). Cambiar una etiqueta cambia el hash de TODAS las producciones.
_SECCIONES = ("Title", "Genres", "Directors", "Cast", "Keywords", "Synopsis")


class EmbeddingProviderError(Exception):
    """El proveedor de embeddings no pudo generar el vector."""


def _lista_normalizada(valores):
    """Ordena alfabéticamente y descarta vacíos.

    TMDB no garantiza un orden estable entre respuestas: sin esto, dos
    respuestas con el mismo contenido producirían hashes distintos y el
    sistema regeneraría embeddings para siempre.
    """
    limpios = [str(v).strip() for v in (valores or []) if str(v).strip()]
    return ", ".join(sorted(limpios))


def construir_texto_canonico(produccion):
    """Arma el texto que representa a la producción para la búsqueda semántica.

    Recibe cualquier objeto con los atributos de `ProduccionAudiovisual`, así
    que no necesita base de datos para probarse.
    """
    valores = (
        (produccion.titulo or "").strip(),
        _lista_normalizada(produccion.generos),
        _lista_normalizada(produccion.directores),
        _lista_normalizada(produccion.reparto),
        _lista_normalizada(produccion.keywords),
        (produccion.sinopsis or "").strip(),
    )
    return "\n".join(
        f"{etiqueta}: {valor}"
        for etiqueta, valor in zip(_SECCIONES, valores, strict=True)
    )


def calcular_source_hash(texto):
    """Huella del texto embebido (SHA-256 hexadecimal, 64 caracteres).

    Se guarda junto al vector: si el hash del texto actual no coincide con el
    guardado, el vector quedó viejo y hay que regenerarlo.
    """
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def generar_vector(texto):
    """Convierte texto en un vector de 1024 dimensiones.

    PUNTO DE EXTENSIÓN PARA B-06 (Marcos): reemplazar el cuerpo por la llamada
    al cliente de Ollama con el modelo `bge-m3`. El resto del pipeline
    (materialización, tarea de Celery, estados, hash) ya está implementado y
    no necesita cambios.

    Mientras no haya proveedor, falla a propósito: `generar_embedding` captura
    la excepción y deja el embedding en estado `failed`, sin afectar la
    visibilidad de la producción en el catálogo.
    """
    raise NotImplementedError(
        "Proveedor de embeddings no implementado todavía (B-06): "
        "falta conectar Ollama/bge-m3."
    )
