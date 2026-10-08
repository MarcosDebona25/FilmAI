"""El registro distingue significado, contexto HTTP y parámetros de máquina."""

import re

from django.test import SimpleTestCase

from filmai.errores.base import ExcepcionAPI
from filmai.errores.catalogo import CATALOGO, obtener_codigo


class CatalogoErroresTests(SimpleTestCase):
    def test_cada_codigo_tiene_nombre_mensaje_contextos_y_parametros_validos(self):
        """Cada entrada pública se puede consultar y declara un estado de su categoría."""
        for codigo, definicion in CATALOGO.items():
            with self.subTest(codigo=codigo):
                self.assertRegex(codigo, re.compile(r"^[a-z]+(?:_[a-z]+)*$"))
                self.assertIs(obtener_codigo(codigo), definicion)
                self.assertTrue(definicion.mensaje)
                self.assertTrue(definicion.contextos)
                definicion.validar_parametros({})
                for contexto, estado in definicion.contextos.items():
                    if definicion.categoria == "success":
                        self.assertTrue(200 <= estado < 300)
                    else:
                        error = ExcepcionAPI(codigo, contexto=contexto)
                        self.assertEqual(error.status_code, estado)
                        self.assertEqual(error.detail.code, codigo)
                        self.assertEqual(str(error.detail), definicion.mensaje)

    def test_codigo_desconocido_exito_y_contexto_incorrecto_se_rechazan(self):
        """Un error de configuración no se convierte en un código público inventado."""
        for codigo, contexto in (
            ("inventado", None),
            ("password_updated", None),
            ("invalid_credentials", None),
            ("invalid_credentials", "perfil"),
        ):
            with self.subTest(codigo=codigo, contexto=contexto):
                with self.assertRaises(ValueError):
                    ExcepcionAPI(codigo, contexto=contexto)

    def test_contexto_conserva_estados_distintos_para_el_mismo_significado(self):
        """Login y autenticación conservan 400/401; username conserva 400/409."""
        for codigo, contexto, estado in (
            ("invalid_credentials", "login", 400),
            ("invalid_credentials", "autenticacion", 401),
            ("username_already_used", "validacion", 400),
            ("username_already_used", "perfil", 409),
        ):
            with self.subTest(codigo=codigo, contexto=contexto):
                self.assertEqual(
                    ExcepcionAPI(codigo, contexto=contexto).status_code, estado
                )

    def test_parametros_rechazan_payloads_y_tipos_ajenos_al_contrato(self):
        """No se publican tokens, correos ni un booleano como cantidad de segundos."""
        for parametros in (
            {"token": "secreto"},
            {"retry_after_seconds": True},
            {"retry_after_seconds": -1},
            [("retry_after_seconds", 0)],
        ):
            with self.subTest(parametros=parametros):
                with self.assertRaises(ValueError):
                    ExcepcionAPI("throttled", parametros=parametros)
        error = ExcepcionAPI("throttled", parametros={"retry_after_seconds": 0})
        self.assertEqual(error.parametros, {"retry_after_seconds": 0})
