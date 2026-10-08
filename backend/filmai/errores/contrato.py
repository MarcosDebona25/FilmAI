"""Contrato público de códigos: lo que el frontend necesita, sin textos internos."""

import json

from .catalogo import CATALOGO

VERSION_CONTRATO = 1


def contrato_errores():
    """Derivado del catálogo; el mensaje interno en español nunca se publica."""
    codigos = {}
    for codigo in sorted(CATALOGO):
        definicion = CATALOGO[codigo]
        entrada = {
            "category": definicion.categoria,
            "contexts": dict(sorted(definicion.contextos.items())),
            "params": dict(sorted(definicion.parametros.items())),
        }
        if definicion.minimos:
            entrada["minimums"] = dict(sorted(definicion.minimos.items()))
        codigos[codigo] = entrada
    return {"version": VERSION_CONTRATO, "codes": codigos}


def serializar_contrato():
    return json.dumps(contrato_errores(), ensure_ascii=False, indent=2) + "\n"
