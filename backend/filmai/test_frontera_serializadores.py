"""Ejecuta serializers DRF reales para comprobar la frontera de parámetros."""

from typing import ClassVar

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ErrorDjango
from django.test import SimpleTestCase, override_settings
from rest_framework import serializers
from rest_framework.exceptions import ErrorDetail, ValidationError

from filmai.errores.base import ExcepcionAPI
from filmai.errores.serializadores import FronteraErroresMixin
from filmai.errores.sobre import entradas_validacion
from filmai.errores.validacion import ErrorValidacion


class FronteraSerializadoresTests(SimpleTestCase):
    def test_limites_distintos_y_eleccion_provienen_de_los_campos_reales(self):
        """Dos max_length comparten código pero conservan sus propios límites."""

        class Datos(FronteraErroresMixin, serializers.Serializer):
            corto = serializers.CharField(max_length=2)
            largo = serializers.CharField(max_length=5)
            idioma = serializers.ChoiceField(choices=("en", "es"))

        serializer = Datos(data={"corto": "abc", "largo": "abcdef", "idioma": "fr"})
        with self.assertRaises(ErrorValidacion) as error:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            entradas_validacion(error.exception),
            [
                {"field": "corto", "code": "max_length", "params": {"maxLength": 2}},
                {"field": "largo", "code": "max_length", "params": {"maxLength": 5}},
                {
                    "field": "idioma",
                    "code": "invalid_choice",
                    "params": {"allowedValues": ["en", "es"]},
                },
            ],
        )

    def test_list_serializer_conserva_rutas_y_lista_de_mensajes_no_es_elemento(self):
        """El índice items.0 es del objeto; la restricción de items es del contenedor."""

        class Item(serializers.Serializer):
            nombre = serializers.CharField(max_length=3)

        class Datos(FronteraErroresMixin, serializers.Serializer):
            items = Item(many=True)
            etiquetas = serializers.ListField(
                child=serializers.CharField(), max_length=1
            )

        serializer = Datos(
            data={"items": [{"nombre": "Largo"}], "etiquetas": ["a", "b"]}
        )
        with self.assertRaises(ErrorValidacion) as error:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            entradas_validacion(error.exception),
            [
                {
                    "field": "items.0.nombre",
                    "code": "max_length",
                    "params": {"maxLength": 3},
                },
                {
                    "field": "etiquetas",
                    "code": "max_length",
                    "params": {"maxLength": 1},
                },
            ],
        )

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
                "OPTIONS": {"min_length": 11},
            }
        ]
    )
    def test_password_django_conserva_codigo_y_limite_configurado(self):
        """La longitud 11 sale del validador activo, no del mensaje ni de un default 8."""

        class Datos(FronteraErroresMixin, serializers.Serializer):
            password1 = serializers.CharField()

            def validate_password1(self, value):
                try:
                    validate_password(value)
                except ErrorDjango as error:
                    raise ErrorValidacion.desde_django(error) from error
                return value

        serializer = Datos(data={"password1": "abc"})
        with self.assertRaises(ErrorValidacion) as error:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            entradas_validacion(error.exception),
            [
                {
                    "field": "password1",
                    "code": "password_too_short",
                    "params": {"minLength": 11},
                }
            ],
        )

    def test_errores_generales_y_aliases_conservan_texto_y_sin_metadata_ajena(self):
        """Un error general de validate conserva su código tras el reenvoltorio DRF."""

        class Datos(FronteraErroresMixin, serializers.Serializer):
            valor = serializers.CharField()

            def validate(self, attrs):
                raise ValidationError([ErrorDetail("Texto original", "datetime")])

        serializer = Datos(data={"valor": "x"})
        with self.assertRaises(ErrorValidacion) as error:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(serializer.errors["non_field_errors"], ["Texto original"])
        self.assertEqual(
            entradas_validacion(error.exception),
            [{"field": None, "code": "invalid", "params": {}}],
        )

    def test_lectura_sin_excepcion_y_datos_validos_conservan_api_drf(self):
        """raise_exception=False sigue retornando False y datos válidos quedan intactos."""

        class Datos(FronteraErroresMixin, serializers.Serializer):
            valor = serializers.IntegerField(min_value=2, max_value=4)

        invalidos = Datos(data={"valor": 1})
        self.assertFalse(invalidos.is_valid())
        with self.assertRaises(ErrorValidacion) as error:
            invalidos.is_valid(raise_exception=True)
        self.assertEqual(
            entradas_validacion(error.exception)[0]["params"], {"minValue": 2}
        )
        validos = Datos(data={"valor": 3})
        self.assertTrue(validos.is_valid(raise_exception=True))
        self.assertEqual(validos.validated_data, {"valor": 3})

    def test_codigo_general_configurado_conserva_legacy_sin_convertirse_en_hoja(self):
        """Credenciales inválidas sigue siendo HTTP 400 en login, con su cuerpo anterior."""

        class Datos(FronteraErroresMixin, serializers.Serializer):
            codigos_generales: ClassVar[dict[str, str]] = {
                "invalid_credentials": "login"
            }

            def validate(self, attrs):
                raise ValidationError("Texto anterior", code="invalid_credentials")

        with self.assertRaises(ExcepcionAPI) as error:
            Datos(data={}).is_valid(raise_exception=True)
        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(error.exception.codigo, "invalid_credentials")
        self.assertEqual(
            error.exception.detail, {"non_field_errors": ["Texto anterior"]}
        )

    def test_campo_explicito_no_reestructura_el_error_general_heredado(self):
        """Un token ausente identifica id_token pero conserva non_field_errors original."""

        class Datos(FronteraErroresMixin, serializers.Serializer):
            def validate(self, attrs):
                raise ValidationError("Texto anterior", code="required")

            def campo_error(self, codigo, ruta, campo):
                return "id_token"

        serializer = Datos(data={})
        with self.assertRaises(ErrorValidacion) as error:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(serializer.errors, {"non_field_errors": ["Texto anterior"]})
        self.assertEqual(
            entradas_validacion(error.exception),
            [{"field": "id_token", "code": "required", "params": {}}],
        )
