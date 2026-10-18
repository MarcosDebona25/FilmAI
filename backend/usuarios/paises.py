"""Países de la cuenta: códigos ISO 3166-1 alfa-2 del contrato compartido.

La lista vive en `contracts/enums.json` (clave `paisCodes`), la misma que
copia el frontend; el backend la lee de ahí para validar y no mantiene otra.
"""

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

# Reparto de los usuarios de desarrollo y de las cuentas anteriores al campo:
# determinista (`ROTACION[id % 8]`). CN a propósito: TMDB casi no tiene datos
# de plataformas allí y ejercita el estado «no disponible».
ROTACION = ("AR", "BR", "US", "ES", "GB", "PT", "CN", "MX")


def pais_por_indice(indice):
    return ROTACION[indice % len(ROTACION)]


@lru_cache(maxsize=1)
def codigos_pais():
    archivo = Path(settings.BASE_DIR).parent / "contracts" / "enums.json"
    return tuple(json.loads(archivo.read_text(encoding="utf-8"))["paisCodes"])


def es_pais_valido(valor):
    return isinstance(valor, str) and valor in codigos_pais()
