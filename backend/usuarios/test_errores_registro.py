"""Ejercita el registro real, incluidas sus dos etapas de validación."""

from datetime import date, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import ValidationError as ErrorDjango
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .adapter import UsuarioAccountAdapter
from .factories import UsuarioFactory
from .models import Usuario


@override_settings(
    DEBUG=False, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
)
class ErroresRegistroTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()
        self.payload = {
            "correo": "nueva@example.com",
            "nombre_usuario": "nueva123",
            "nombre": "María",
            "apellido": "Pérez",
            "fecha_nacimiento": "1990-01-01",
            "genero": "no_especifica",
            "password1": "NuevaClave456!",
            "password2": "NuevaClave456!",
        }

    def registrar(self, cambios):
        cache.clear()
        return self.client.post(
            "/api/auth/registration/", {**self.payload, **cambios}, format="json"
        )

    def test_duplicados_mantienen_campos_y_http_de_registro(self):
        """A diferencia del perfil, el duplicado detectado en registro sigue siendo 400."""
        usuario = UsuarioFactory()
        for campo, valor, codigo, _mensaje in (
            (
                "correo",
                usuario.correo,
                "email_already_used",
                "El correo ya está registrado.",
            ),
            (
                "nombre_usuario",
                usuario.nombre_usuario,
                "username_already_used",
                "El nombre de usuario ya está registrado.",
            ),
        ):
            with self.subTest(campo=campo):
                response = self.registrar({campo: valor})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["code"], "validation_error")
                self.assertEqual(
                    response.data["errors"],
                    [{"field": campo, "code": codigo, "params": {}}],
                )

    def test_reglas_personales_conservan_codigo_y_limites_en_la_frontera_real(self):
        """Cada regla mantiene su identidad y la configuración que se aplicó."""
        for campo, valor, codigo, parametros in (
            (
                "nombre_usuario",
                "abc",
                "username_invalid",
                {"minLength": 5, "maxLength": 25},
            ),
            ("apellido", "Perez123", "person_name_invalid", {"maxLength": 50}),
            (
                "fecha_nacimiento",
                (date.today() + timedelta(days=1)).isoformat(),
                "birth_date_in_future",
                {},
            ),
            (
                "fecha_nacimiento",
                date.today().isoformat(),
                "minimum_age",
                {"minAge": 13},
            ),
        ):
            with self.subTest(codigo=codigo):
                response = self.registrar({campo: valor})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["errors"],
                    [{"field": campo, "code": codigo, "params": parametros}],
                )
                self.assertIn(
                    campo, {entry["field"] for entry in response.data["errors"]}
                )

    def test_mismatch_heredado_conserva_traduccion_y_non_field_errors(self):
        """El código se asigna por la condición, sin interpretar texto traducido."""
        response = self.registrar({"password2": "OtraClave456!"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(
            response.data["errors"],
            [{"field": None, "code": "passwords_do_not_match", "params": {}}],
        )

    def test_password_django_no_pierde_codigo_ni_caracteres_especiales(self):
        """La validación heredada de password1 conserva metadata de la regla propia."""
        response = self.registrar(
            {"password1": "ZxCvbnm987", "password2": "ZxCvbnm987"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"],
            [
                {
                    "field": "password1",
                    "code": "password_no_special",
                    "params": {"specialCharacters": "@#$%&*!"},
                }
            ],
        )

    def test_segunda_validacion_durante_save_conserva_metadata_y_no_persiste(self):
        """Un fallo que depende del usuario ocurre en save, después de is_valid."""
        original = UsuarioAccountAdapter.clean_password

        def validar(adapter, password, user=None):
            if user is not None:
                raise ErrorDjango(
                    "Rechazo posterior de contraseña.", code="password_no_special"
                )
            return original(adapter, password, user=user)

        with patch.object(UsuarioAccountAdapter, "clean_password", validar):
            response = self.registrar({})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(
            response.data["errors"],
            [
                {
                    "field": None,
                    "code": "password_no_special",
                    "params": {"specialCharacters": "@#$%&*!"},
                }
            ],
        )
        self.assertFalse(Usuario.objects.filter(correo=self.payload["correo"]).exists())
