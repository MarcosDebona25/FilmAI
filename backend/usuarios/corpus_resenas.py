"""Corpus de reseñas del seed masivo: formato, validación y lectura/escritura.

El corpus vive en `backend/seed_data/resenas.jsonl.gz`: una línea JSON por
(producción, idioma, banda de nota) con la forma

    {"id_tmdb": 603, "tipo": "movie", "idioma": "es", "banda": "alta",
     "textos": ["...", "..."]}

Las reseñas las redacta un modelo aparte y se compilan con
`compilar_corpus_resenas`; `seed_masivo` las lee con `cargar_corpus`.
El archivo se escribe ordenado y con la cabecera gzip fija (`mtime=0`) para que
volver a compilar lo mismo dé los mismos bytes y los diffs de git sean chicos.
"""

import functools
import gzip
import io
import json
import os
from pathlib import Path

from django.conf import settings

TIPOS = ("movie", "tv")
IDIOMAS = ("es", "en")
BANDAS = ("baja", "media", "alta")
MINIMO_TEXTOS = 2
LARGO_MINIMO = 20
LARGO_MAXIMO = 400

# Tipo del corpus (el de TMDB) <-> `TipoProduccion` del modelo.
TIPO_CORPUS_A_MODELO = {"movie": "pelicula", "tv": "serie"}
TIPO_MODELO_A_CORPUS = {v: k for k, v in TIPO_CORPUS_A_MODELO.items()}


def ruta_corpus():
    """Ruta del corpus; función y no constante para poder parchearla en tests."""
    return Path(settings.BASE_DIR) / "seed_data" / "resenas.jsonl.gz"


def banda_de_nota(valor):
    """Banda de una nota: 1 a 4 baja, 5 a 7 media, 8 a 10 alta."""
    return "alta" if valor >= 8 else "media" if valor >= 5 else "baja"


def clave(entrada):
    return (entrada["id_tmdb"], entrada["tipo"], entrada["idioma"], entrada["banda"])


def validar_entrada(entrada):
    """Devuelve la entrada normalizada (textos sin espacios en los bordes).

    Lanza `ValueError` con el motivo si no cumple el formato.
    """
    if not isinstance(entrada, dict):
        raise ValueError("la línea no es un objeto JSON")
    faltan = {"id_tmdb", "tipo", "idioma", "banda", "textos"} - entrada.keys()
    if faltan:
        raise ValueError(f"faltan campos: {', '.join(sorted(faltan))}")
    id_tmdb = entrada["id_tmdb"]
    if type(id_tmdb) is not int or id_tmdb <= 0:
        raise ValueError("id_tmdb debe ser un entero positivo")
    if entrada["tipo"] not in TIPOS:
        raise ValueError(f"tipo inválido: {entrada['tipo']!r}")
    if entrada["idioma"] not in IDIOMAS:
        raise ValueError(f"idioma inválido: {entrada['idioma']!r}")
    if entrada["banda"] not in BANDAS:
        raise ValueError(f"banda inválida: {entrada['banda']!r}")
    textos = entrada["textos"]
    if not isinstance(textos, list) or not all(isinstance(t, str) for t in textos):
        raise ValueError("textos debe ser una lista de cadenas")
    textos = [t.strip() for t in textos]
    if len(textos) < MINIMO_TEXTOS or not all(textos):
        raise ValueError(f"hacen falta {MINIMO_TEXTOS}+ textos no vacíos")
    for texto in textos:
        if not LARGO_MINIMO <= len(texto) <= LARGO_MAXIMO:
            raise ValueError(
                f"cada texto debe tener entre {LARGO_MINIMO} y {LARGO_MAXIMO} "
                f"caracteres (hay uno de {len(texto)})"
            )
    if len(set(textos)) != len(textos):
        raise ValueError("hay textos duplicados dentro de la entrada")
    return {
        "id_tmdb": id_tmdb,
        "tipo": entrada["tipo"],
        "idioma": entrada["idioma"],
        "banda": entrada["banda"],
        "textos": textos,
    }


def cargar_corpus(ruta=None):
    """Lee el corpus como `{(id_tmdb, tipo, idioma, banda): [textos]}`.

    Si el archivo no existe devuelve `{}`: `seed_masivo` cae entonces a las
    plantillas de `seed_real`. Las líneas dañadas se ignoran.
    """
    ruta = Path(ruta) if ruta else ruta_corpus()
    if not ruta.exists():
        return {}
    corpus = {}
    with gzip.open(ruta, "rt", encoding="utf-8") as archivo:
        for linea in archivo:
            if not linea.strip():
                continue
            try:
                entrada = validar_entrada(json.loads(linea))
            except ValueError:
                continue
            corpus[clave(entrada)] = entrada["textos"]
    return corpus


def escribir_corpus(entradas, ruta=None):
    """Escribe `{clave: textos}` ordenado y determinista (gzip con mtime=0)."""
    ruta = Path(ruta) if ruta else ruta_corpus()
    lineas = []
    for (id_tmdb, tipo, idioma, banda), textos in sorted(entradas.items()):
        lineas.append(
            json.dumps(
                {
                    "id_tmdb": id_tmdb,
                    "tipo": tipo,
                    "idioma": idioma,
                    "banda": banda,
                    "textos": textos,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    contenido = ("\n".join(lineas) + "\n" if lineas else "").encode("utf-8")
    buffer = io.BytesIO()
    # `filename=""` y `mtime=0`: sin nombre ni fecha en la cabecera.
    with gzip.GzipFile(
        filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9
    ) as gz:
        gz.write(contenido)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_bytes(buffer.getvalue())
    os.replace(temporal, ruta)


def producciones_cubiertas(corpus):
    """Pares (id_tmdb, tipo) con las seis entradas (2 idiomas por 3 bandas)."""
    cuenta = {}
    for id_tmdb, tipo, _idioma, _banda in corpus:
        cuenta[(id_tmdb, tipo)] = cuenta.get((id_tmdb, tipo), 0) + 1
    return {par for par, n in cuenta.items() if n >= len(IDIOMAS) * len(BANDAS)}


def ruta_plantillas_genero():
    return Path(settings.BASE_DIR) / "seed_data" / "plantillas_genero.json"


@functools.cache
def plantillas_genero():
    """`{id_genero_tmdb: {idioma: {banda: [textos]}}}`, o `{}` si falta el archivo.

    Son frases por género que valen para cualquier título: el respaldo de las
    reseñas que no están en el corpus por título.
    """
    ruta = ruta_plantillas_genero()
    if not ruta.exists():
        return {}
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return {int(g): v for g, v in crudo.items() if g.isdigit()}
