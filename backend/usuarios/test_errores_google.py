"""El sobre se comprueba aparte usando los mismos escenarios reales de F0."""

from datetime import date

from django.db import transaction
from django.test import TestCase, override_settings

from filmai import tests_contrato
from filmai.errores.sobre import entradas_validacion
from filmai.errores.validacion import ErrorValidacion

from .avatares import validar_avatar_id
from .factories import UsuarioFactory
from .serializers import GoogleSocialLoginSerializer


@override_settings(DEBUG=False)
class ErroresGoogleTests(TestCase):
    # Compartir preparación evita duplicar mocks de Google; no hereda tests F0.
    google = tests_contrato.ContratoErroresAPITests.google
    serializar = tests_contrato.ContratoErroresAPITests.serializar

    def setUp(self):
        self.usuario = UsuarioFactory()

    def test_token_requerido_tiene_campo_explicito_sin_cambiar_legacy(self):
        """El origen identifica id_token aunque el cuerpo anterior sea no-field."""
        response = self.google("token")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(
            response.data["errors"],
            [{"field": "id_token", "code": "required", "params": {}}],
        )

    def test_campos_faltantes_conservan_mensajes_y_rutas(self):
        """Los tres campos del perfil faltante se mantienen separados."""
        response = self.google("faltantes")
        self.assertEqual(response.status_code, 400)
        for campo in ("nombre_usuario", "fecha_nacimiento", "genero"):
            self.assertIn(campo, {entry["field"] for entry in response.data["errors"]})
        self.assertEqual(
            response.data["errors"],
            [
                {"field": campo, "code": "required", "params": {}}
                for campo in ("nombre_usuario", "fecha_nacimiento", "genero")
            ],
        )

    def test_alta_sin_aceptar_terminos_se_rechaza_con_su_codigo(self):
        """Una cuenta nueva de Google exige la aceptación antes de crearse."""
        response = self.google("sin_terminos")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(
            response.data["errors"],
            [{"field": "acepta_terminos", "code": "terms_not_accepted", "params": {}}],
        )

    def test_fallos_operativos_y_carrera_de_integridad_tienen_codigos(self):
        """Las fallas aisladas de transporte/login y la carrera conservan HTTP 400."""
        for caso, codigo in (
            ("verificar", "google_authentication_failed"),
            ("completar", "google_authentication_failed"),
            ("respuesta", "google_authentication_failed"),
            ("carrera", "email_or_username_already_used"),
            ("correo", "email_already_used"),
        ):
            with self.subTest(caso=caso), transaction.atomic():
                # Cada escenario F0 prepara el mismo correo de Google.
                response = self.google(caso)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["errors"],
                    [{"field": None, "code": codigo, "params": {}}],
                )
                self.assertEqual(response.data["code"], "validation_error")
                transaction.set_rollback(True)

    def test_edad_google_recupera_limite_tras_validacion_de_campos(self):
        """La fecha inválida falla antes de consultar Google y conserva minAge."""
        serializer = GoogleSocialLoginSerializer(
            data={"fecha_nacimiento": date.today().isoformat()}
        )
        with self.assertRaises(ErrorValidacion) as error:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            entradas_validacion(error.exception),
            [
                {
                    "field": "fecha_nacimiento",
                    "code": "minimum_age",
                    "params": {"minAge": 13},
                }
            ],
        )
        self.assertEqual(
            error.exception.detail["fecha_nacimiento"],
            ["Debés tener al menos 13 años."],
        )

    def test_validador_modelo_avatar_asigna_codigo_sin_cambiar_mensaje(self):
        """El validador Django usado por modelo/Admin conserva su contrato propio."""
        from django.core.exceptions import ValidationError as ErrorDjango

        with self.assertRaises(ErrorDjango) as error:
            validar_avatar_id(999)
        self.assertEqual(error.exception.code, "avatar_invalid")
        self.assertEqual(error.exception.messages, ["Elegí un avatar disponible."])
