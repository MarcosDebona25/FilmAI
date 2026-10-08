"""OT-33: espera del 429, códigos de éxito y estados de cuenta en el login."""

from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import Throttled
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from filmai.exceptions import filmai_exception_handler
from usuarios.factories import UsuarioFactory
from usuarios.models import EstadoCuenta

GENERICO = "No tenés permisos para realizar esta acción."


class EsperaDelLimiteTests(SimpleTestCase):
    def test_throttled_informa_la_espera_en_sobre_y_encabezado(self):
        respuesta = filmai_exception_handler(Throttled(wait=41.2), {})
        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(respuesta.data["code"], "throttled")
        self.assertEqual(respuesta.data["params"], {"retry_after_seconds": 42})
        self.assertIn("Retry-After", respuesta)
        self.assertIn("detail", respuesta.data)

    def test_sin_espera_conocida_no_hay_parametros(self):
        respuesta = filmai_exception_handler(Throttled(), {})
        self.assertEqual(respuesta.data["params"], {})


@override_settings(DEBUG=False)
class EstadosDeCuentaEnLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.cliente = APIClient()

    def _login(self, usuario, campo, password):
        valor = usuario.correo if campo == "email" else usuario.nombre_usuario
        return self.cliente.post(
            "/api/auth/login/", {campo: valor, "password": password}, format="json"
        )

    def test_credencial_correcta_distingue_baja_y_pendiente(self):
        for estado, codigo in (
            (EstadoCuenta.BAJA, "account_deactivated"),
            (EstadoCuenta.PENDIENTE, "account_pending_confirmation"),
        ):
            usuario = UsuarioFactory(estado=estado)
            for campo in ("email", "username"):
                with self.subTest(estado=estado, campo=campo):
                    r = self._login(usuario, campo, "Password123!")
                    self.assertEqual(r.status_code, 403)
                    self.assertEqual(r.json()["code"], codigo)
                    self.assertEqual(r.json()["detail"], GENERICO)

    def test_credencial_incorrecta_nunca_revela_el_estado(self):
        activo = UsuarioFactory()
        for estado in (EstadoCuenta.BAJA, EstadoCuenta.PENDIENTE):
            usuario = UsuarioFactory(estado=estado)
            for campo in ("email", "username"):
                with self.subTest(estado=estado, campo=campo):
                    r = self._login(usuario, campo, "Incorrecta123!")
                    self.assertEqual(r.status_code, 400)
                    self.assertEqual(r.json()["code"], "invalid_credentials")
        referencia = self._login(activo, "email", "Incorrecta123!")
        self.assertEqual(referencia.status_code, 400)
        self.assertEqual(referencia.json()["code"], "invalid_credentials")

    def test_cuenta_activa_sigue_ingresando(self):
        usuario = UsuarioFactory()
        self.assertEqual(self._login(usuario, "email", "Password123!").status_code, 200)


@override_settings(DEBUG=False)
class CodigosDeExitoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.cliente = APIClient()

    def _autenticar(self, usuario):
        self.cliente.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(usuario)}"
        )

    def test_csrf(self):
        r = self.cliente.get("/api/auth/csrf/")
        self.assertEqual((r.json()["detail"], r.json()["code"]), ("ok", "csrf_ready"))

    def test_recuperacion_conserva_intentos_restantes(self):
        r = self.cliente.post(
            "/api/auth/password/reset/", {"email": "nadie@example.com"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["code"], "password_reset_requested")
        self.assertIn("intentos_restantes", r.json())
        self.assertIn("detail", r.json())

    def test_baja_de_cuenta(self):
        usuario = UsuarioFactory()
        self._autenticar(usuario)
        r = self.cliente.post("/api/account/deactivate/", {}, format="json")
        self.assertEqual(r.json()["code"], "account_deactivated_successfully")
        self.assertIn("detail", r.json())

    def test_registro_y_reenvio(self):
        r = self.cliente.post(
            "/api/auth/registration/",
            {
                "correo": "nueva@example.com",
                "nombre_usuario": "nueva123",
                "nombre": "María",
                "apellido": "Pérez",
                "fecha_nacimiento": "1990-01-01",
                "genero": "no_especifica",
                "password1": "NuevaClave456!",
                "password2": "NuevaClave456!",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["code"], "registration_pending_confirmation")
        self.assertIn("detail", r.json())
        self.assertEqual(len(mail.outbox), 1)
        r = self.cliente.post(
            "/api/auth/registration/resend-email/",
            {"email": "nueva@example.com"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["code"], "confirmation_email_sent")

    def test_logout(self):
        usuario = UsuarioFactory()
        self.cliente.post(
            "/api/auth/login/",
            {"email": usuario.correo, "password": "Password123!"},
            format="json",
        )
        r = self.cliente.post("/api/auth/logout/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["code"], "logged_out")
        self.assertIn("detail", r.json())


class ConfirmacionDeCorreoTests(TestCase):
    def test_confirmacion_exitosa_lleva_codigo(self):
        from allauth.account.models import EmailConfirmationHMAC

        usuario = UsuarioFactory(estado=EstadoCuenta.PENDIENTE)
        direccion = EmailAddress.objects.create(
            user=usuario, email=usuario.correo, primary=True, verified=False
        )
        clave = EmailConfirmationHMAC(direccion).key
        r = APIClient().post(
            "/api/auth/registration/verify-email/", {"key": clave}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["code"], "email_confirmed")
