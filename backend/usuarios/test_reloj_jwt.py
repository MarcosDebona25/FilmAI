"""Tokens emitidos justo antes de que el reloj retroceda.

En WSL2 (y en servidores mal sincronizados) el reloj puede saltar hacia atrás
un par de segundos. Sin tolerancia, PyJWT rechazaba con 401 (Unauthorized) un
token recién emitido porque su `iat` quedaba "en el futuro"; eso hacía fallar
tests de `test_perfil` y `test_cuenta` al azar bajo carga.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import UsuarioFactory


class RelojJWTTests(TestCase):
    def emitido_adelantado(self, segundos):
        """Token emitido con el reloj `segundos` por delante del actual."""
        adelantado = timezone.now() + timedelta(seconds=segundos)
        with patch(
            "rest_framework_simplejwt.tokens.aware_utcnow", return_value=adelantado
        ):
            return RefreshToken.for_user(UsuarioFactory()).access_token

    def perfil(self, token):
        return self.client.get("/api/profile/", HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_un_retroceso_de_pocos_segundos_no_invalida_el_token(self):
        self.assertEqual(self.perfil(self.emitido_adelantado(3)).status_code, 200)

    def test_un_token_emitido_muy_en_el_futuro_se_sigue_rechazando(self):
        respuesta = self.perfil(self.emitido_adelantado(60))
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["code"], "invalid_token")
