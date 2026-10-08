"""Frontera final de DRF: recupera parámetros de configuración, sin leer texto."""

from typing import ClassVar

from django.contrib.auth.password_validation import (
    MinimumLengthValidator,
    get_default_password_validators,
)
from rest_framework.exceptions import ErrorDetail

from .base import ExcepcionAPI
from .sobre import ALIAS_VALIDACION
from .validacion import ErrorValidacion, hojas


def _normalizar_codigos(detalle):
    if isinstance(detalle, dict):
        return {clave: _normalizar_codigos(valor) for clave, valor in detalle.items()}
    if isinstance(detalle, (list, tuple)):
        return [_normalizar_codigos(valor) for valor in detalle]
    return ErrorDetail(str(detalle), ALIAS_VALIDACION.get(detalle.code, detalle.code))


def _campo_en_ruta(serializer, detalle, ruta):
    """Distingue un índice de elemento de un índice en la lista de mensajes."""
    campo = serializer
    nodo = detalle
    for segmento in ruta:
        if segmento == "non_field_errors":
            return None
        if isinstance(segmento, str):
            campo = getattr(campo, "fields", {}).get(segmento)
            nodo = nodo[segmento]
        else:
            son_mensajes = isinstance(nodo, (list, tuple)) and all(
                not isinstance(valor, (dict, list, tuple)) for valor in nodo
            )
            if not son_mensajes:
                campo = getattr(campo, "child", None)
            nodo = nodo[segmento]
        if campo is None:
            return None
    return campo


class FronteraErroresMixin:
    """Adjunta metadata después de que Serializer.is_valid reconstruye errores."""

    codigos_generales: ClassVar[dict[str, str]] = {}

    def campo_error(self, codigo, ruta, campo):
        """Permite identificar un campo sin alterar la forma del cuerpo heredado."""
        return None

    def parametros_error(self, codigo, campo):
        parametros = {}
        limites = {
            "min_length": ("minLength", "min_length"),
            "max_length": ("maxLength", "max_length"),
            "min_value": ("minValue", "min_value"),
            "max_value": ("maxValue", "max_value"),
        }
        if codigo in limites and campo is not None:
            nombre, atributo = limites[codigo]
            valor = getattr(campo, atributo, None)
            if valor is not None:
                parametros[nombre] = valor
        elif codigo == "invalid_choice" and campo is not None:
            valores = list(getattr(campo, "choices", {}))
            if valores and all(isinstance(valor, str) for valor in valores):
                parametros["allowedValues"] = valores
        elif codigo.startswith("password_"):
            for validador in get_default_password_validators():
                parametros.update(
                    getattr(validador, "parametros_por_codigo", {}).get(codigo, {})
                )
                if codigo == "password_too_short" and isinstance(
                    validador, MinimumLengthValidator
                ):
                    parametros["minLength"] = validador.min_length
        return parametros

    def is_valid(self, *, raise_exception=False):
        valido = super().is_valid(raise_exception=False)
        if valido or not raise_exception:
            return valido
        detalle = _normalizar_codigos(self.errors)
        codigos = {hoja.code for _, hoja in hojas(detalle)}
        if len(codigos) == 1:
            codigo = next(iter(codigos))
            if codigo in self.codigos_generales:
                raise ExcepcionAPI(
                    codigo, contexto=self.codigos_generales[codigo], detalle=detalle
                )
        campos = {}
        for ruta, hoja in hojas(detalle):
            campo = self.campo_error(
                hoja.code, ruta, _campo_en_ruta(self, detalle, ruta)
            )
            if campo is not None:
                campos[ruta] = campo
        parametros = {
            ruta: self.parametros_error(hoja.code, _campo_en_ruta(self, detalle, ruta))
            for ruta, hoja in hojas(detalle)
        }
        raise ErrorValidacion(
            detalle, parametros_por_ruta=parametros, campos_por_ruta=campos
        )
