"""Excepción de dominio que conserva códigos y parámetros sin analizar texto."""

from rest_framework.exceptions import APIException

from .catalogo import obtener_codigo


class ExcepcionAPI(APIException):
    def __init__(self, codigo, *, contexto=None, parametros=None, detalle=None):
        definicion = obtener_codigo(codigo)
        if definicion.categoria != "error":
            raise ValueError("Un código de éxito no puede usarse como excepción.")
        if contexto is None:
            if len(definicion.contextos) != 1:
                raise ValueError("El código requiere un contexto HTTP explícito.")
            contexto = next(iter(definicion.contextos))
        if contexto not in definicion.contextos:
            raise ValueError(f"Contexto no permitido: {contexto}.")
        parametros = parametros if parametros is not None else {}
        definicion.validar_parametros(parametros)
        self.parametros = dict(parametros)
        self.status_code = definicion.contextos[contexto]
        self.contexto = contexto
        self.codigo = codigo
        super().__init__(
            detalle if detalle is not None else definicion.mensaje, code=codigo
        )
