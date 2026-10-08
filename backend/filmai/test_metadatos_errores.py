"""Los códigos y parámetros se conservan aunque DRF convierta las hojas."""

from django.core.exceptions import ValidationError as ErrorDjango
from django.test import SimpleTestCase
from rest_framework.exceptions import ErrorDetail

from filmai.errores.catalogo import CATALOGO, obtener_codigo
from filmai.errores.validacion import ErrorValidacion, hojas


class MetadatosErroresTests(SimpleTestCase):
    def test_catalogo_cubre_cada_hoja_con_su_contexto_de_validacion(self):
        """Una prueba por entrada de validación detecta definiciones inutilizables."""
        for codigo, definicion in CATALOGO.items():
            if definicion.contextos.get("validacion") != 400:
                continue
            with self.subTest(codigo=codigo):
                error = ErrorValidacion({"campo": ["Texto interno"]}, codigo)
                self.assertEqual(error.detail["campo"][0].code, codigo)
                self.assertEqual(error.parametros_por_ruta, {("campo", 0): {}})

    def test_codigos_distintos_y_parametros_por_hoja_sobreviven_conversion_drf(self):
        """Dos fallos del mismo campo conservan códigos, límites y orden propios."""
        error = ErrorValidacion(
            {
                "items": [
                    {
                        "nombre": [
                            ErrorDetail("Largo", "max_length"),
                            ErrorDetail("Vacío", "blank"),
                        ]
                    }
                ]
            },
            parametros_por_ruta={("items", 0, "nombre", 0): {"maxLength": 50}},
        )
        self.assertEqual(
            [hoja.code for _, hoja in hojas(error.detail)], ["max_length", "blank"]
        )
        self.assertEqual(
            error.parametros_por_ruta[("items", 0, "nombre", 0)], {"maxLength": 50}
        )
        self.assertEqual(error.parametros_por_ruta[("items", 0, "nombre", 1)], {})

    def test_parametros_sin_hoja_y_codigos_no_validacion_se_rechazan(self):
        """No se cuelga metadata de un campo ajeno ni se usa un error general como hoja."""
        with self.assertRaises(ValueError):
            ErrorValidacion("Texto", parametros_por_ruta={("ajeno",): {}})
        with self.assertRaises(ValueError):
            ErrorValidacion("Texto", "server_error")

    def test_parametros_numericos_y_listas_excluyen_no_finitos_y_booleanos(self):
        """Los límites y IDs provienen de configuración válida, sin NaN/infinito."""
        for codigo, parametros in (
            ("min_value", {"minValue": float("nan")}),
            ("max_value", {"maxValue": float("inf")}),
            ("avatar_invalid", {"allowedIds": [1, True]}),
            ("invalid_choice", {"allowedValues": [1]}),
        ):
            with self.subTest(codigo=codigo):
                with self.assertRaises(ValueError):
                    obtener_codigo(codigo).validar_parametros(parametros)
        obtener_codigo("max_value").validar_parametros({"maxValue": 10})
        obtener_codigo("avatar_invalid").validar_parametros({"allowedIds": [1, 2]})

    def test_conversion_django_conserva_cada_codigo_sin_copiar_datos_sensibles(self):
        """La lista de fallos Django mantiene límites explícitos y excluye value."""
        original = ErrorDjango(
            [
                ErrorDjango(
                    "Corto", code="password_too_short", params={"value": "secreto"}
                ),
                ErrorDjango("Largo", code="max_length", params={"maxLength": 25}),
            ]
        )
        error = ErrorValidacion.desde_django(
            original, parametros_por_codigo={"password_too_short": {"minLength": 8}}
        )
        self.assertEqual(
            [hoja.code for hoja in error.detail], ["password_too_short", "max_length"]
        )
        self.assertEqual(
            error.parametros_por_ruta, {(0,): {"minLength": 8}, (1,): {"maxLength": 25}}
        )
        self.assertEqual([str(hoja) for hoja in error.detail], ["Corto", "Largo"])
