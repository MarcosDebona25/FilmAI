"""Endurecimiento del acceso tras la segunda revisión de seguridad (26/10/2026).

Cada clase cubre un hallazgo verificado:

- Modelos de terceros en el admin (allauth, simplejwt, `Group`) solo para
  superusuarios: con permisos parciales, un staff podía escalar a superusuario.
- El login de la app no abre una sesión de Django (`SESSION_LOGIN`).
- El acceso acepta solo JSON (login CSRF con formularios).
- Una cuenta nueva con Google exige el correo verificado por Google.
- Un solo contador por cuenta en el login, se la nombre por correo o usuario.
- El logout sin barra responde con su código.
"""

from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import Client, TestCase
from rest_framework.test import APIClient

from .factories import UsuarioFactory
from .models import Usuario

PAYLOAD_GOOGLE = {
    "id_token": "google-verificado",
    "nombre_usuario": "nuevagoogle",
    "fecha_nacimiento": "1995-05-05",
    "genero": "no_especifica",
    "pais": "AR",
    "acepta_terminos": True,
}


class AdminDeTercerosTests(TestCase):
    RUTAS = (
        ("socialaccount", "socialaccount", "/admin/socialaccount/socialaccount/"),
        (
            "token_blacklist",
            "outstandingtoken",
            "/admin/token_blacklist/outstandingtoken/",
        ),
        ("auth", "group", "/admin/auth/group/"),
    )

    def test_un_staff_con_permisos_no_entra_a_los_modelos_de_terceros(self):
        staff = UsuarioFactory(is_staff=True)
        for app, modelo, _ in self.RUTAS:
            staff.user_permissions.add(
                *Permission.objects.filter(
                    content_type__app_label=app, content_type__model=modelo
                )
            )
        cliente = Client()
        cliente.force_login(staff)

        for _, _, ruta in self.RUTAS:
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 403)

    def test_un_superusuario_si_entra(self):
        superusuario = UsuarioFactory(is_staff=True, is_superuser=True)
        cliente = Client()
        cliente.force_login(superusuario)

        for _, _, ruta in self.RUTAS:
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 200)


class LoginDeLaAppTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.usuario = UsuarioFactory()

    def test_no_abre_una_sesion_de_django(self):
        respuesta = Client().post(
            "/api/auth/login/",
            {"email": self.usuario.correo, "password": "Password123!"},
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("sessionid", respuesta.cookies)

    def test_un_formulario_es_415(self):
        respuesta = Client().post(
            "/api/auth/login/",
            {"email": self.usuario.correo, "password": "Password123!"},
        )

        self.assertEqual(respuesta.status_code, 415)
        self.assertEqual(respuesta.json()["code"], "unsupported_media_type")

    def test_correo_y_usuario_comparten_el_contador_de_la_cuenta(self):
        cliente = Client()
        estados = []
        for numero in range(11):
            campo, valor = (
                ("email", self.usuario.correo)
                if numero % 2
                else ("username", self.usuario.nombre_usuario)
            )
            estados.append(
                cliente.post(
                    "/api/auth/login/",
                    {campo: valor, "password": "incorrecta"},
                    content_type="application/json",
                ).status_code
            )

        # Antes, 6 por un lado y 5 por el otro: ninguno llegaba a 10.
        self.assertEqual(estados[10], 429)

    def test_el_logout_sin_barra_responde_igual_que_con_barra(self):
        # Como `test_logout` de `test_codigos_exito_estado`: con las cookies del
        # login, que traen el refresh que el logout pone en la blacklist.
        for ruta in ("/api/auth/logout/", "/api/auth/logout"):
            with self.subTest(ruta=ruta):
                cliente = APIClient()
                cliente.post(
                    "/api/auth/login/",
                    {"email": self.usuario.correo, "password": "Password123!"},
                    format="json",
                )
                respuesta = cliente.post(ruta)

                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.json()["code"], "logged_out")


class GoogleCorreoVerificadoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def _alta(self, verificado):
        with patch(
            "allauth.socialaccount.providers.google.views._verify_and_decode",
            return_value={
                "sub": "sub-nuevo",
                "email": "nueva@example.com",
                "email_verified": verificado,
            },
        ):
            return Client().post(
                "/api/auth/google/", PAYLOAD_GOOGLE, content_type="application/json"
            )

    def test_una_cuenta_nueva_sin_correo_verificado_se_rechaza(self):
        respuesta = self._alta(verificado=False)

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            "google_authentication_failed",
            {error["code"] for error in respuesta.json()["errors"]},
        )
        self.assertFalse(Usuario.objects.filter(correo="nueva@example.com").exists())

    def test_con_el_correo_verificado_se_crea(self):
        respuesta = self._alta(verificado=True)

        self.assertIn(respuesta.status_code, (200, 201), respuesta.content)
        self.assertTrue(Usuario.objects.filter(correo="nueva@example.com").exists())


class GoogleContadorPropioTests(TestCase):
    """Google y el login con contraseña no comparten el contador por IP."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_agotar_el_login_no_bloquea_google(self):
        from rest_framework.throttling import SimpleRateThrottle

        usuario = UsuarioFactory()
        with patch.dict(SimpleRateThrottle.THROTTLE_RATES, {"login_ip": "2/min"}):
            cliente = Client()
            estados = [
                cliente.post(
                    "/api/auth/login/",
                    {"email": usuario.correo, "password": "mala"},
                    content_type="application/json",
                ).status_code
                for _ in range(3)
            ]
            with patch(
                "allauth.socialaccount.providers.google.views._verify_and_decode",
                return_value={
                    "sub": "x",
                    "email": "g@example.com",
                    "email_verified": True,
                },
            ):
                google = cliente.post(
                    "/api/auth/google/", PAYLOAD_GOOGLE, content_type="application/json"
                )

        self.assertEqual(estados[2], 429)
        self.assertNotEqual(google.status_code, 429)
