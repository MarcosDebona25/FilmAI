"""Metadatos por hoja: DRF conserva el código pero descarta parámetros Django."""

from rest_framework.exceptions import ValidationError

from .catalogo import obtener_codigo


def hojas(detalle, ruta=()):
    """Recorre el árbol real sin depender de la traducción de sus mensajes."""
    if isinstance(detalle, dict):
        for nombre, valor in detalle.items():
            yield from hojas(valor, (*ruta, nombre))
    elif isinstance(detalle, (list, tuple)):
        for indice, valor in enumerate(detalle):
            yield from hojas(valor, (*ruta, indice))
    else:
        yield ruta, detalle


class ErrorValidacion(ValidationError):
    def __init__(self, detalle, codigo="invalid", *, parametros_por_ruta=None):
        super().__init__(detalle, code=codigo)
        self.parametros_por_ruta = {}
        pendientes = dict(parametros_por_ruta or {})
        for ruta, hoja in hojas(self.detail):
            definicion = obtener_codigo(hoja.code)
            if definicion.contextos.get("validacion") != 400:
                raise ValueError("La hoja debe tener un código de validación.")
            parametros = pendientes.pop(ruta, {})
            definicion.validar_parametros(parametros)
            self.parametros_por_ruta[ruta] = dict(parametros)
        if pendientes:
            raise ValueError(
                "Hay parámetros sin una hoja de validación correspondiente."
            )

    @classmethod
    def desde_django(cls, error, *, parametros_por_codigo=None):
        """Convierte error_list antes de que DRF pierda códigos y parámetros."""
        from rest_framework.exceptions import ErrorDetail

        detalle = []
        parametros = {}
        for indice, hoja in enumerate(error.error_list):
            codigo = hoja.code or "invalid"
            definicion = obtener_codigo(codigo)
            # La configuración explícita completa límites que Django no publica
            # con nombres del contrato. Nunca se copian value/show_value ni PII.
            valores = dict((parametros_por_codigo or {}).get(codigo, {}))
            for nombre in definicion.parametros:
                if nombre in (hoja.params or {}):
                    valores[nombre] = hoja.params[nombre]
            detalle.append(ErrorDetail(hoja.messages[0], codigo))
            parametros[(indice,)] = valores
        return cls(detalle, parametros_por_ruta=parametros)
