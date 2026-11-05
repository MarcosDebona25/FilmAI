"""Texto a embeber, su huella y la llamada al proveedor (C-04a, B-06).

El vector de una producción se calcula a partir de un texto: este módulo
decide cuál es ese texto, cómo detectar que quedó viejo y cómo pedirle a Ollama
(modelo bge-m3) que lo convierta en vector.
"""

import hashlib

import httpx
from django.conf import settings

# Identifica qué modelo produjo cada vector: vectores de modelos distintos no
# son comparables entre sí, así que un cambio acá obliga a regenerarlos. Es
# también el nombre del modelo en Ollama.
MODEL_VERSION = "bge-m3"

# Lo que mide `ProduccionEmbedding.vector`: otro tamaño no se puede comparar.
_DIMENSIONES = 1024

# Una consulta del chat tiene a una persona esperando: si Ollama se cuelga, se
# pierde como máximo este tiempo. El backfill usa los valores por defecto de
# `generar_vector`, porque nadie lo espera y un fallo pasajero se puede reintentar.
PRESUPUESTO_CHAT = {"timeout": 3, "reintentos": 0}
# Con el modelo sin cargar: la carga midió entre 2 y 24 s según la memoria libre.
# Cortar antes es peor que esperar, porque Ollama abandona la carga. Deja lugar
# dentro de los 25 s del turno para el resto de la respuesta.
PRESUPUESTO_CARGA = {"timeout": 20, "reintentos": 0}
# Solo para saber si el modelo está cargado: si esto no responde, Ollama está caído.
_TIMEOUT_ESTADO = 1

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


def _extraer_vector(respuesta):
    """Saca el vector de la respuesta de Ollama, o falla si no sirve."""
    if respuesta.status_code != httpx.codes.OK:
        raise EmbeddingProviderError(f"Ollama respondió {respuesta.status_code}")
    try:
        vector = respuesta.json()["embeddings"][0]
        dimensiones = len(vector)
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise EmbeddingProviderError("Ollama respondió sin un vector") from error
    if dimensiones != _DIMENSIONES:
        raise EmbeddingProviderError(
            f"Ollama devolvió {dimensiones} dimensiones, no {_DIMENSIONES}"
        )
    return vector


def modelo_cargado(*, transport=None):
    """Dice si el modelo ya está en memoria, para saber cuánto vale la pena esperar.

    Distingue un modelo cargándose de un Ollama colgado: si esta consulta
    liviana no responde, no tiene sentido esperar la carga.
    """
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/ps"
    try:
        with httpx.Client(timeout=_TIMEOUT_ESTADO, transport=transport) as cliente:
            modelos = cliente.get(url).json()["models"]
        # `/api/embed` pide el modelo sin etiqueta, que Ollama entiende como `latest`.
        nombres = (MODEL_VERSION, f"{MODEL_VERSION}:latest")
        return any(m.get("name") in nombres for m in modelos)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise EmbeddingProviderError("No se pudo consultar a Ollama") from error


def generar_vector(texto, *, timeout=10, reintentos=2, transport=None):
    """Convierte texto en un vector de 1024 dimensiones usando Ollama.

    Reintenta solo lo pasajero (conexión, timeout y errores 5xx). Un 4xx o una
    respuesta inválida no se arreglan insistiendo, así que fallan enseguida.
    Cualquier fallo de Ollama o de la red termina en `EmbeddingProviderError`.

    `transport` existe para los tests: reemplaza la red por una respuesta falsa.
    """
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/embed"
    cuerpo = {
        "model": MODEL_VERSION,
        "input": texto,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
    }

    with httpx.Client(timeout=timeout, transport=transport) as cliente:
        for intento in range(reintentos + 1):
            es_el_ultimo = intento == reintentos
            try:
                respuesta = cliente.post(url, json=cuerpo)
            except httpx.TransportError as error:
                if es_el_ultimo:
                    raise EmbeddingProviderError(
                        "No se pudo hablar con Ollama"
                    ) from error
                continue
            if respuesta.is_server_error and not es_el_ultimo:
                continue
            return _extraer_vector(respuesta)
