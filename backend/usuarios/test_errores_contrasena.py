"""Comprueba códigos y parámetros de contraseña sin cambiar oráculos anteriores."""

from allauth.account.forms import default_token_generator
from allauth.account.utils import user_pk_to_url_str
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import UsuarioFactory


@override_settings(DEBUG=False)
class ErroresContrasenaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.usuario = UsuarioFactory()
        self.usuario.set_password("Password123!")
        self.usuario.save(update_fields=["password"])
        self.client = APIClient()
        self.client.force_authenticate(
            self.usuario, token=RefreshToken.for_user(self.usuario).access_token
        )
        self.payload = {
            "old_password": "Password123!",
            "password1": "OtraClave456!",
            "password2": "OtraClave456!",
        }

    def cambiar(self, cambios):
        return self.client.post(
            "/api/profile/change-password/", {**self.payload, **cambios}, format="json"
        )

    def test_password_actual_y_mismatch_conservan_detalle_y_campos(self):
        """Los rechazos propios mantienen sus listas y la contraseña persistida."""
        for cambios, campo, codigo, detalle in (
            (
                {"old_password": "Incorrecta!"},
                "old_password",
                "current_password_incorrect",
                "La contraseña actual es incorrecta.",
            ),
            (
                {"password2": "Distinta123!"},
                "password2",
                "passwords_do_not_match",
                "Las contraseñas no coinciden.",
            ),
        ):
            with self.subTest(codigo=codigo):
                response = self.cambiar(cambios)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data[campo], [detalle])
                self.assertEqual(
                    response.data["errors"],
                    [{"field": campo, "code": codigo, "params": {}}],
                )
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("Password123!"))

    def test_cuenta_google_sin_password_conserva_indicacion_de_recuperacion(self):
        """La ausencia de contraseña local tiene código propio, sin cambiar HTTP."""
        self.usuario.set_unusable_password()
        self.usuario.save(update_fields=["password"])
        self.client.force_authenticate(
            self.usuario, token=RefreshToken.for_user(self.usuario).access_token
        )
        response = self.cambiar({})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"],
            [
                {
                    "field": "old_password",
                    "code": "local_password_unavailable",
                    "params": {},
                }
            ],
        )
        self.assertIn(
            "mediante recuperación por correo.", response.data["old_password"][0]
        )

    def test_limites_y_caracteres_salen_del_validador_aplicado(self):
        """Django y la regla propia conservan todas las hojas, incluidas sus métricas."""
        for password, esperados in (
            (
                "Abc1!",
                [
                    {
                        "field": "password1",
                        "code": "password_too_short",
                        "params": {"minLength": 8},
                    },
                    {
                        "field": "password1",
                        "code": "password_too_short_or_long",
                        "params": {"minLength": 8, "maxLength": 20},
                    },
                ],
            ),
            (
                "ZxCvbnm987",
                [
                    {
                        "field": "password1",
                        "code": "password_no_special",
                        "params": {"specialCharacters": "@#$%&*!"},
                    }
                ],
            ),
        ):
            with self.subTest(password=password):
                response = self.cambiar({"password1": password, "password2": password})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["errors"], esperados)
                self.assertIn("password1", response.data)

    def test_reset_valida_enlace_real_y_conserva_mismatch(self):
        """La confirmación distingue password2 y conserva su mensaje anterior."""
        response = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "uid": user_pk_to_url_str(self.usuario),
                "token": default_token_generator.make_token(self.usuario),
                "password1": "OtraClave456!",
                "password2": "Distinta123!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["password2"], ["Las contraseñas no coinciden."])
        self.assertEqual(
            response.data["errors"],
            [{"field": "password2", "code": "passwords_do_not_match", "params": {}}],
        )

    def test_recuperacion_email_invalido_usa_codigo_del_campo(self):
        """La solicitud anónima rechaza formato sin buscar ni revelar una cuenta."""
        response = APIClient().post(
            "/api/auth/password/reset/", {"email": "invalido"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"],
            [{"field": "email", "code": "invalid", "params": {}}],
        )
        self.assertIn("email", response.data)

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
                "OPTIONS": {"min_length": 11},
            }
        ]
    )
    def test_reset_con_enlace_firmado_usa_limite_django_configurado(self):
        """El enlace se valida antes de fallar la política configurada en 11."""
        response = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "uid": user_pk_to_url_str(self.usuario),
                "token": default_token_generator.make_token(self.usuario),
                "password1": "Abcdefg1!",
                "password2": "Abcdefg1!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["errors"],
            [
                {
                    "field": "password1",
                    "code": "password_too_short",
                    "params": {"minLength": 11},
                },
            ],
        )
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("Password123!"))
