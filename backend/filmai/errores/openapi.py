"""Publica el sobre de errores en el esquema OpenAPI (post-procesamiento)."""

from .catalogo import CATALOGO

_ERRORES = sorted(c for c, d in CATALOGO.items() if d.categoria == "error")
_HOJAS = sorted(
    c
    for c, d in CATALOGO.items()
    if d.categoria == "error" and d.contextos.get("validacion") == 400
)
_REF = {"$ref": "#/components/schemas/ErrorEnvelope"}


def _esquemas():
    parametros = {
        "type": "object",
        "description": "Valores de máquina; nunca texto para mostrar.",
        "additionalProperties": True,
    }
    return {
        "ErrorEntry": {
            "type": "object",
            "description": "Una hoja de validación por campo.",
            "properties": {
                "field": {"type": "string", "nullable": True},
                "code": {"type": "string", "enum": _HOJAS},
                "params": parametros,
            },
            "required": ["field", "code", "params"],
        },
        "ErrorEnvelope": {
            "type": "object",
            "description": (
                "Sobre definitivo de toda respuesta 4xx/5xx; sin texto de interfaz."
            ),
            "properties": {
                "code": {"type": "string", "enum": _ERRORES},
                "params": parametros,
                "errors": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/ErrorEntry"},
                },
                "debug": {
                    "type": "object",
                    "description": "Solo con DEBUG=True; el frontend no lo lee.",
                    "properties": {"message": {"type": "string"}},
                },
            },
            "required": ["code", "params", "errors"],
            "additionalProperties": False,
        },
    }


def agregar_sobre_de_errores(result, generator, request, public):
    """Declara `ErrorEnvelope` y lo asocia a los rangos 4XX/5XX de cada operación."""
    result.setdefault("components", {}).setdefault("schemas", {}).update(_esquemas())
    cuerpo = {
        "description": "Error con el sobre de códigos estables.",
        "content": {"application/json": {"schema": _REF}},
    }
    for operaciones in result.get("paths", {}).values():
        for metodo, operacion in operaciones.items():
            if metodo not in {"get", "post", "put", "patch", "delete"}:
                continue
            respuestas = operacion.setdefault("responses", {})
            respuestas.setdefault("4XX", cuerpo)
            respuestas.setdefault("5XX", cuerpo)
    return result
