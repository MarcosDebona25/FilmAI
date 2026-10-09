"""Construcción del sobre y conservación explícita del cuerpo heredado."""

from copy import deepcopy

from rest_framework.exceptions import ValidationError

from .catalogo import CATALOGO, obtener_codigo
from .validacion import hojas

RESERVADOS = frozenset({"code", "params", "errors", "debug"})
ALIAS_VALIDACION = {
    "max_string_length": "invalid",
    "overflow": "invalid",
    "datetime": "invalid",
}


def entradas_validacion(error, *, estricto=True):
    """Una entrada por hoja; los índices de las listas de mensajes no son campos."""
    if not isinstance(error, ValidationError):
        raise ValueError("Se requiere una excepción de validación.")
    entradas = []
    for ruta, hoja in hojas(error.detail):
        codigo = ALIAS_VALIDACION.get(hoja.code, hoja.code)
        # La adopción de códigos en los módulos se completa en OT-31/OT-32.
        # OT-34 hará obligatorio el rechazo de toda hoja sin registrar.
        if not estricto and codigo not in CATALOGO:
            codigo = "invalid"
        definicion = obtener_codigo(codigo)
        if definicion.contextos.get("validacion") != 400:
            raise ValueError("El código no corresponde a una hoja de validación.")
        parametros = getattr(error, "parametros_por_ruta", {}).get(ruta, {})
        definicion.validar_parametros(parametros)
        campo = list(ruta)
        while campo and isinstance(campo[-1], int):
            campo.pop()
        if campo and campo[-1] == "non_field_errors":
            campo.pop()
        nombre_campo = ".".join(str(segmento) for segmento in campo) or None
        nombre_campo = getattr(error, "campos_por_ruta", {}).get(ruta, nombre_campo)
        entradas.append(
            {
                "field": nombre_campo,
                "code": codigo,
                "params": deepcopy(parametros),
            }
        )
    return entradas


def construir_sobre(
    codigo, estado, *, parametros=None, errores=None, debug=False, mensaje=None
):
    definicion = obtener_codigo(codigo)
    if definicion.categoria != "error" or estado not in definicion.contextos.values():
        raise ValueError("El estado HTTP no corresponde al código de error.")
    parametros = parametros if parametros is not None else {}
    definicion.validar_parametros(parametros)
    errores = errores if errores is not None else []
    if not isinstance(errores, list) or (codigo != "validation_error" and errores):
        raise ValueError("Solo validation_error admite hojas de validación.")
    for error in errores:
        if set(error) != {"field", "code", "params"}:
            raise ValueError("Una hoja debe tener field, code y params.")
        if error["field"] is not None and not isinstance(error["field"], str):
            raise ValueError("El campo debe ser una ruta o nulo.")
        hoja = obtener_codigo(error["code"])
        if hoja.contextos.get("validacion") != 400:
            raise ValueError("El código no es una hoja de validación.")
        hoja.validar_parametros(error["params"])
    sobre = {
        "code": codigo,
        "params": deepcopy(parametros),
        "errors": deepcopy(errores),
    }
    if debug:
        sobre["debug"] = {
            "message": mensaje if mensaje is not None else definicion.mensaje
        }
    return sobre


def agregar_codigo_exito(response, codigo):
    """Emite el código de éxito y preserva datos de máquina sin textos heredados."""
    definicion = obtener_codigo(codigo)
    if definicion.categoria != "success":
        raise ValueError("Se requiere un código de éxito.")
    if response.status_code not in definicion.contextos.values():
        raise ValueError("El estado HTTP no corresponde al código de éxito.")
    if not isinstance(response.data, dict) or "code" in response.data:
        raise ValueError("La respuesta exitosa no admite el campo code.")
    response.data = {
        clave: valor for clave, valor in response.data.items() if clave != "detail"
    }
    response.data["code"] = codigo
    return response


def validar_respuesta_error(estado, cuerpo, *, debug=False):
    """Comprueba que un cuerpo de error cumple el sobre; lanza AssertionError."""
    if not isinstance(cuerpo, dict):
        raise AssertionError(f"El cuerpo de un {estado} no es un objeto: {cuerpo!r}.")
    adicionales = set(cuerpo) - {"code", "params", "errors", "debug"}
    if adicionales:
        raise AssertionError(f"Claves ajenas al contrato: {sorted(adicionales)}.")
    faltantes = {"code", "params", "errors"} - set(cuerpo)
    if faltantes:
        raise AssertionError(f"Falta el sobre ({sorted(faltantes)}) en un {estado}.")
    codigo = cuerpo["code"]
    if codigo not in CATALOGO:
        raise AssertionError(f"Código no registrado en un {estado}: {codigo!r}.")
    definicion = CATALOGO[codigo]
    if definicion.categoria != "error" or estado not in definicion.contextos.values():
        raise AssertionError(f"{codigo} no corresponde al estado HTTP {estado}.")
    definicion.validar_parametros(cuerpo["params"])
    if cuerpo["errors"] and codigo != "validation_error":
        raise AssertionError("Solo validation_error admite hojas.")
    for hoja in cuerpo["errors"]:
        if set(hoja) != {"field", "code", "params"}:
            raise AssertionError(f"Hoja mal formada: {hoja!r}.")
        if hoja["code"] not in CATALOGO:
            raise AssertionError(f"Hoja con código no registrado: {hoja['code']!r}.")
        hoja_def = CATALOGO[hoja["code"]]
        if hoja_def.contextos.get("validacion") != 400:
            raise AssertionError(f"{hoja['code']} no es una hoja de validación.")
        hoja_def.validar_parametros(hoja["params"])
    if ("debug" in cuerpo) != debug:
        raise AssertionError("El campo debug debe existir solo con DEBUG=True.")
