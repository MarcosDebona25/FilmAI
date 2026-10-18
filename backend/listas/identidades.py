"""Valores públicos y nombres reservados de listas y género."""

from usuarios.models import TipoGenero
from usuarios.paises import codigos_pais
from usuarios.provisioning import LISTAS_PREDETERMINADAS

from .models import ClaveLista

NOMBRES_RESERVADOS = {
    "en": ("Favorites", "Watchlist", "Watched"),
    "es": LISTAS_PREDETERMINADAS,
}


def es_nombre_reservado(nombre):
    return any(
        nombre.casefold() == reservado.casefold()
        for nombres in NOMBRES_RESERVADOS.values()
        for reservado in nombres
    )


def contrato_enums():
    return {
        "defaultListKeys": ClaveLista.values,
        "genderValues": TipoGenero.values,
        "reservedListNames": {
            idioma: list(nombres) for idioma, nombres in NOMBRES_RESERVADOS.items()
        },
        "paisCodes": list(codigos_pais()),
    }
