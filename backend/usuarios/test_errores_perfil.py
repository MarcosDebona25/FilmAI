"""Pruebas HTTP separadas del sobre nuevo en perfil y preferencias."""

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .avatares import AVATAR_IDS_VALIDOS
from .factories import UsuarioFactory


@override_settings(DEBUG=False)
class ErroresPerfilTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        self.client = APIClient()
        self.client.force_authenticate(
            self.usuario, token=RefreshToken.for_user(self.usuario).access_token
        )

    def test_nombre_invalido_conserva_mensaje_y_limite_del_validador(self):
        """La conversión Django→DRF conserva código, límite y cuerpo anterior."""
        response = self.client.put("/api/profile/", {"nombre": "Ana123"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(
            response.data["errors"],
            [
                {
                    "field": "nombre",
                    "code": "person_name_invalid",
                    "params": {"maxLength": 50},
                }
            ],
        )
        self.assertNotIn("debug", response.data)

    def test_longitud_y_regex_username_identifican_restricciones_distintas(self):
        """Un máximo del campo y el formato del username no pierden sus límites."""
        for valor, codigo, parametros in (
            ("x" * 26, "max_length", {"maxLength": 25}),
            ("abc", "username_invalid", {"minLength": 5, "maxLength": 25}),
        ):
            with self.subTest(valor=valor):
                response = self.client.put(
                    "/api/profile/", {"nombre_usuario": valor}, format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["errors"],
                    [{"field": "nombre_usuario", "code": codigo, "params": parametros}]
                    + (
                        [
                            {
                                "field": "nombre_usuario",
                                "code": "username_invalid",
                                "params": {"minLength": 5, "maxLength": 25},
                            }
                        ]
                        if codigo == "max_length"
                        else []
                    ),
                )
                self.assertIn(
                    "nombre_usuario",
                    {entry["field"] for entry in response.data["errors"]},
                )

    def test_avatar_devuelve_ids_del_registro_y_el_detalle_anterior(self):
        """Los IDs traducibles salen del registro activo y conservan el texto previo."""
        response = self.client.put("/api/profile/", {"avatar_id": 999}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertEqual(
            response.data["errors"],
            [
                {
                    "field": "avatar_id",
                    "code": "avatar_invalid",
                    "params": {"allowedIds": sorted(AVATAR_IDS_VALIDOS)},
                }
            ],
        )

    def test_username_ocupado_sigue_siendo_conflicto_sin_hojas(self):
        """El conflicto de unicidad mantiene 409 y no se convierte en validación 400."""
        otro = UsuarioFactory()
        response = self.client.put(
            "/api/profile/", {"nombre_usuario": otro.nombre_usuario}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "username_already_used")
        self.assertEqual(response.data["errors"], [])
        self.assertEqual(response.data["code"], "username_already_used")

    def test_preferencias_usa_claves_machine_y_rechaza_null_sin_params(self):
        """Idioma inválido enumera claves soportadas; null conserva su propio código."""
        for valor, codigo, parametros in (
            (
                "fr",
                "invalid_choice",
                {"allowedValues": list(settings.IDIOMAS_SOPORTADOS)},
            ),
            (None, "null", {}),
        ):
            with self.subTest(valor=valor):
                response = self.client.put(
                    "/api/preferences/", {"idioma": valor}, format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["errors"],
                    [{"field": "idioma", "code": codigo, "params": parametros}],
                )
                self.assertIn(
                    "idioma", {entry["field"] for entry in response.data["errors"]}
                )
        self.usuario.refresh_from_db()
        self.assertIsNone(self.usuario.idioma)
