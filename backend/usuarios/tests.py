"""Tests de usuarios: disponibilidad de username (A-05) y confirmación de
cuenta por email (CU-002) con sus errores diferenciados."""

import re
from typing import ClassVar
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.core import mail
from django.test import TestCase

from .factories import UsuarioFactory
from .models import EstadoCuenta


class UsernameDisponibleTests(TestCase):
    def setUp(self):
        self.url = "/api/auth/username-available/"
        self.usuario = UsuarioFactory(nombre_usuario="usuario123")

    def test_disponible_cuando_no_existe(self):
        response = self.client.get(self.url, {"username": "nuevousuario"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"disponible": True})

    def test_no_disponible_cuando_existe(self):
        response = self.client.get(self.url, {"username": "usuario123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"disponible": False})

    def test_insensible_a_mayusculas(self):
        response = self.client.get(self.url, {"username": "USUARIO123"})
        self.assertEqual(response.json(), {"disponible": False})

    def test_formato_invalido_reporta_no_disponible(self):
        for username in ("abc", "a" * 26, "con espacio!", ""):
            with self.subTest(username=username):
                response = self.client.get(self.url, {"username": username})
                self.assertEqual(response.json(), {"disponible": False})


class ConfirmarCorreoTests(TestCase):
    """Flujo CU-002 completo sobre el backend real (emails en outbox local).

    El registro envía el correo vía allauth con nuestros templates en español;
    la key se extrae del `activate_url` del cuerpo capturado.
    """

    PAYLOAD: ClassVar[dict] = {
        "correo": "confirmar@filmai.com",
        "nombre_usuario": "usuarioconf",
        "nombre": "Confirmar",
        "apellido": "Correo",
        "fecha_nacimiento": "1995-05-10",
        "genero": "no_especifica",
        "password1": "Password123!",
        "password2": "Password123!",
    }

    def _registrar(self) -> str:
        response = self.client.post(
            "/api/auth/registration/", self.PAYLOAD, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        # El subject sale de nuestro template (prefijo global vacío).
        self.assertEqual(mail.outbox[0].subject, "[FilmAI] Confirmación de cuenta")
        # La key viaja en el enlace .../confirmar-correo/<key>/
        match = re.search(r"/confirmar-correo/([^/\s\"<]+)/", mail.outbox[0].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def _confirmar(self, key: str):
        return self.client.post(
            "/api/auth/registration/verify-email/",
            {"key": key},
            content_type="application/json",
        )

    def _estado_cuenta(self):
        from .models import EstadoCuenta, Usuario

        usuario = Usuario.objects.get(correo=self.PAYLOAD["correo"])
        email_address = EmailAddress.objects.get(email=self.PAYLOAD["correo"])
        return usuario, email_address, EstadoCuenta

    def test_flujo_completo_registro_confirmacion_login(self):
        key = self._registrar()

        usuario, email_address, EstadoCuenta = self._estado_cuenta()
        self.assertEqual(usuario.estado, EstadoCuenta.PENDIENTE)
        self.assertFalse(email_address.verified)

        # Saludo del email de confirmación con nombre + apellido.
        self.assertIn("Hola Confirmar Correo,", mail.outbox[0].body)

        response = self._confirmar(key)
        self.assertEqual(response.status_code, 200)

        usuario, email_address, _ = self._estado_cuenta()
        self.assertEqual(usuario.estado, EstadoCuenta.ACTIVA)
        self.assertTrue(email_address.verified)

        login = self.client.post(
            "/api/auth/login/",
            {"email": self.PAYLOAD["correo"], "password": "Password123!"},
            content_type="application/json",
        )
        self.assertIn("access", login.json())

    def test_key_reusada_reporta_ya_confirmada(self):
        key = self._registrar()
        self.assertEqual(self._confirmar(key).status_code, 200)

        response = self._confirmar(key)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "ya_confirmada"})

    def test_key_corrupta_reporta_invalido(self):
        response = self._confirmar("key-totalmente-falsa")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "invalido"})

    def test_key_expirada_reporta_expirado(self):
        key = self._registrar()

        # Adelantamos el reloj 25 horas: django.core.signing usa time.time()
        # para validar el timestamp firmado.
        import time as time_module

        real_time = time_module.time()
        with patch("django.core.signing.time.time", return_value=real_time + 25 * 3600):
            response = self._confirmar(key)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "expirado"})


class RecuperarContrasenaTests(TestCase):
    """Recuperación de contraseña (CU-020 / A-07).

    Cubre: envío del email con enlace al frontend, no revelación de
    existencia de cuentas, exclusión de cuentas no activas, cambio efectivo
    de contraseña, rechazo de enlaces inválidos y de contraseñas débiles,
    y rate limit de 1 solicitud por minuto por IP.
    """

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def _crear_usuario_activo(self, correo: str = "recuperar@filmai.com"):
        usuario = UsuarioFactory(
            nombre_usuario="usuarioreset",
            correo=correo,
            nombre="Recuperar",
            apellido="Contrasena",
        )  # el factory ya crea la cuenta ACTIVA
        usuario.set_password("ViejaPass1!")
        usuario.save()
        return usuario

    def _solicitar(self, email: str):
        return self.client.post(
            "/api/auth/password/reset/",
            {"email": email},
            content_type="application/json",
        )

    def test_solicitud_envia_email_con_enlace_al_frontend(self):
        self._crear_usuario_activo()

        response = self._solicitar("recuperar@filmai.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[FilmAI] Restablecimiento de contraseña")
        match = re.search(r"/restablecer-contrasena/([^/]+)/([^/]+)/", mail.outbox[0].body)
        self.assertIsNotNone(match)
        self.assertIn("válido durante 1 hora", mail.outbox[0].body)
        # El saludo muestra nombre + apellido (docs/decisiones.md 24/08/2026).
        self.assertIn("Hola Recuperar Contrasena,", mail.outbox[0].body)

    def test_saludo_fallback_sin_nombre(self):
        """Sin nombre ni apellido, el saludo es "Hola usuario"."""
        UsuarioFactory(
            nombre_usuario="usuariosenombre",
            correo="sinnombre@filmai.com",
            nombre="",
            apellido="",
        )

        self._solicitar("sinnombre@filmai.com")

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Hola usuario,", mail.outbox[0].body)

    def test_solicitud_email_inexistente_no_revela_y_no_envia(self):
        response = self._solicitar("fantasma@filmai.com")

        self.assertEqual(response.status_code, 200)
        # Misma respuesta que para un correo existente (docs/02 CU-020 obs.).
        self.assertIn("detail", response.json())
        self.assertEqual(len(mail.outbox), 0)

    def test_solicitud_cuenta_pendiente_o_baja_no_envia_email(self):
        pendiente = UsuarioFactory(
            nombre_usuario="usuariopend",
            correo="pendiente@filmai.com",
            estado=EstadoCuenta.PENDIENTE,
        )
        assert pendiente.estado == EstadoCuenta.PENDIENTE

        response = self._solicitar("pendiente@filmai.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmar_actualiza_contraseña_y_permite_login(self):
        self._crear_usuario_activo()
        self._solicitar("recuperar@filmai.com")
        match = re.search(
            r"/restablecer-contrasena/([^/]+)/([^/]+)/", mail.outbox[0].body
        )

        response = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "uid": match.group(1),
                "token": match.group(2),
                "password1": "NuevaPass456!",
                "password2": "NuevaPass456!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        viejo = self.client.post(
            "/api/auth/login/",
            {"email": "recuperar@filmai.com", "password": "ViejaPass1!"},
            content_type="application/json",
        )
        nuevo = self.client.post(
            "/api/auth/login/",
            {"email": "recuperar@filmai.com", "password": "NuevaPass456!"},
            content_type="application/json",
        )
        self.assertEqual(viejo.status_code, 400)
        self.assertEqual(nuevo.status_code, 200)
        self.assertIn("access", nuevo.json())

    def test_confirmar_enlace_invalido_devuelve_codigo(self):
        response = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "uid": "AAAA",
                "token": "token-falso",
                "password1": "NuevaPass456!",
                "password2": "NuevaPass456!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "invalido"})

    def test_confirmar_token_expirado_devuelve_invalido(self):
        import datetime as dt_mod
        from unittest.mock import patch as mock_patch

        from django.contrib.auth.tokens import PasswordResetTokenGenerator

        self._crear_usuario_activo()
        self._solicitar("recuperar@filmai.com")
        match = re.search(
            r"/restablecer-contrasena/([^/]+)/([^/]+)/", mail.outbox[0].body
        )

        futuro = dt_mod.datetime.now() + dt_mod.timedelta(hours=2)
        with mock_patch.object(
            PasswordResetTokenGenerator, "_now", return_value=futuro
        ):
            response = self.client.post(
                "/api/auth/password/reset/confirm/",
                {
                    "uid": match.group(1),
                    "token": match.group(2),
                    "password1": "NuevaPass456!",
                    "password2": "NuevaPass456!",
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"codigo": "invalido"})

    def test_confirmar_politica_debil_rechazada(self):
        self._crear_usuario_activo()
        self._solicitar("recuperar@filmai.com")
        match = re.search(
            r"/restablecer-contrasena/([^/]+)/([^/]+)/", mail.outbox[0].body
        )

        response = self.client.post(
            "/api/auth/password/reset/confirm/",
            {
                "uid": match.group(1),
                "token": match.group(2),
                "password1": "abc123",
                "password2": "abc123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password1", response.json())

    def test_rate_limit_segunda_solicitud_429(self):
        self._crear_usuario_activo()

        primera = self._solicitar("recuperar@filmai.com")
        segunda = self._solicitar("recuperar@filmai.com")

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 429)
