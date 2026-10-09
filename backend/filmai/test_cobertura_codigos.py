"""OT-34: cada código del catálogo se emite con un sobre válido."""

from django.test import SimpleTestCase, override_settings
from rest_framework.response import Response

from filmai.errores.base import ExcepcionAPI
from filmai.errores.catalogo import CATALOGO
from filmai.errores.sobre import (
    agregar_codigo_exito,
    entradas_validacion,
    validar_respuesta_error,
)
from filmai.errores.validacion import ErrorValidacion
from filmai.exceptions import filmai_exception_handler

HOJAS = sorted(
    c
    for c, d in CATALOGO.items()
    if d.categoria == "error" and d.contextos.get("validacion") == 400
)
ERRORES = sorted(c for c, d in CATALOGO.items() if d.categoria == "error")
EXITOS = sorted(c for c, d in CATALOGO.items() if d.categoria == "success")


@override_settings(DEBUG=False)
class CadaCodigoCumpleElSobreTests(SimpleTestCase):
    def test_error_por_contexto_pasa_por_el_manejador(self):
        for codigo in ERRORES:
            for contexto, estado in CATALOGO[codigo].contextos.items():
                if codigo == "validation_error":
                    continue  # se cubre por hojas
                with self.subTest(codigo=codigo, contexto=contexto):
                    respuesta = filmai_exception_handler(
                        ExcepcionAPI(codigo, contexto=contexto), {}
                    )
                    self.assertEqual(respuesta.status_code, estado)
                    self.assertEqual(respuesta.data["code"], codigo)
                    validar_respuesta_error(estado, respuesta.data)

    def test_cada_hoja_de_validacion_se_emite_como_validation_error(self):
        for codigo in HOJAS:
            with self.subTest(codigo=codigo):
                error = ErrorValidacion({"campo": "texto"}, codigo)
                respuesta = filmai_exception_handler(error, {})
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(respuesta.data["code"], "validation_error")
                self.assertEqual(respuesta.data["errors"][0]["code"], codigo)
                validar_respuesta_error(400, respuesta.data)

    def test_cada_exito_acepta_su_codigo_solo_en_su_estado(self):
        for codigo in EXITOS:
            for estado in CATALOGO[codigo].contextos.values():
                with self.subTest(codigo=codigo):
                    respuesta = agregar_codigo_exito(
                        Response({"detail": "x"}, status=estado), codigo
                    )
                    self.assertEqual(respuesta.data["code"], codigo)
                    self.assertNotIn("detail", respuesta.data)
                    with self.assertRaises(ValueError):
                        agregar_codigo_exito(Response({}, status=404), codigo)


class CodigosNoRegistradosTests(SimpleTestCase):
    def test_hoja_sin_registrar_se_rechaza_en_modo_estricto(self):
        error = ErrorValidacion.__new__(ErrorValidacion)
        from rest_framework.exceptions import ValidationError

        ValidationError.__init__(error, {"campo": "x"}, code="inventado")
        with self.assertRaises(ValueError):
            entradas_validacion(error)

    def test_excepcion_sin_registrar_falla_en_modo_estricto(self):
        from rest_framework.exceptions import APIException

        class Ajena(APIException):
            default_code = "codigo_ajeno"

        with override_settings(FILMAI_SOBRE_ESTRICTO=True):
            with self.assertRaises(ValueError):
                filmai_exception_handler(Ajena(), {})

    @override_settings(FILMAI_SOBRE_ESTRICTO=False, DEBUG=False)
    def test_en_produccion_degrada_a_un_codigo_generico_del_estado(self):
        from rest_framework.exceptions import APIException

        class Ajena(APIException):
            status_code = 403
            default_code = "codigo_ajeno"

        respuesta = filmai_exception_handler(Ajena(), {})
        self.assertEqual(respuesta.data["code"], "permission_denied")
        validar_respuesta_error(403, respuesta.data)


class ValidadorDeRespuestasTests(SimpleTestCase):
    def test_rechaza_cuerpos_sin_sobre_o_con_debug_inesperado(self):
        base = {"code": "not_found", "params": {}, "errors": []}
        validar_respuesta_error(404, base)
        for estado, cuerpo, debug in (
            (404, {"detail": "x"}, False),
            (404, {**base, "code": "inventado"}, False),
            (400, base, False),
            (404, {**base, "debug": {"message": "x"}}, False),
            (404, base, True),
            (404, {**base, "errors": [{"field": None}]}, False),
        ):
            with self.subTest(cuerpo=cuerpo, debug=debug):
                with self.assertRaises(AssertionError):
                    validar_respuesta_error(estado, cuerpo, debug=debug)


class SinColisionConElSobreTests(SimpleTestCase):
    def test_ningun_serializer_declara_campos_con_nombres_del_sobre(self):
        """`code`, `params`, `errors` y `debug` pertenecen al sobre de errores."""
        from rest_framework.serializers import BaseSerializer

        from filmai.errores.sobre import RESERVADOS

        def subclases(base):
            for clase in base.__subclasses__():
                yield clase
                yield from subclases(clase)

        for clase in set(subclases(BaseSerializer)):
            if not clase.__module__.startswith(
                ("usuarios", "catalogo", "listas", "filmai")
            ):
                continue
            try:
                campos = set(clase().fields)
            except Exception:  # requieren contexto propio
                campos = set(getattr(clase, "_declared_fields", {}))
            with self.subTest(serializer=clase.__qualname__):
                self.assertFalse(campos & RESERVADOS)
