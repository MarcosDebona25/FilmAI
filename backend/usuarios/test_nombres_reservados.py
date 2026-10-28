"""Nombres de usuario reservados (issue #137, 28/10/2026).

Nadie puede registrarse ni cambiarse el nombre a uno que se confunda con una
cuenta del equipo («admin», «Adm1n», «soporteoficial»). El error es
`username_not_allowed`, que no dice que el nombre está reservado.
"""

from typing import ClassVar
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase
from rest_framework_simplejwt.tokens import AccessToken

from .factories import UsuarioFactory
from .models import Usuario
from .validators import es_nombre_usuario_reservado

ERROR = [{"field": "nombre_usuario", "code": "username_not_allowed", "params": {}}]


class ReglaTests(SimpleTestCase):
    def test_rechaza_los_reservados_y_sus_variantes(self):
        for nombre in (
            "admin",
            "ADMIN",
            "Admin2026",
            "Adm1n",
            "4dm1n",
            "1admin",
            "a1dmin",
            "2026staff",
            "r00t",
            "Administrator",
            "superadmin",
            "SysAdmin",
            "theadmin",
            "adminteam",
            "soporteoficial",
            "FilmAI",
            "F1lmA1fan",
            "moderador",
            "noreply",
        ):
            with self.subTest(nombre=nombre):
                self.assertTrue(es_nombre_usuario_reservado(nombre))

    def test_deja_pasar_nombres_comunes_que_se_parecen(self):
        # «badminton» contiene «admin»: por eso «admin» no se busca adentro.
        for nombre in (
            "badminton",
            "theodore",
            "realmadrid",
            "teamrocket",
            "roots",
            "staffy",
            "sistemas",
            "laura",
            "lucas1995",
            "r2d2fan",
            "cine2024",
        ):
            with self.subTest(nombre=nombre):
                self.assertFalse(es_nombre_usuario_reservado(nombre))


class RegistroTests(TestCase):
    PAYLOAD: ClassVar[dict] = {
        "correo": "nuevo@filmai.com",
        "nombre": "Nuevo",
        "apellido": "Usuario",
        "fecha_nacimiento": "1995-05-10",
        "genero": "no_especifica",
        "pais": "AR",
        "acepta_terminos": True,
        "password1": "Password123!",
        "password2": "Password123!",
    }

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def _registrar(self, nombre_usuario):
        return Client().post(
            "/api/auth/registration/",
            {**self.PAYLOAD, "nombre_usuario": nombre_usuario},
            content_type="application/json",
        )

    def test_un_nombre_reservado_es_400_sin_crear_la_cuenta(self):
        respuesta = self._registrar("Adm1n")

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["errors"], ERROR)
        self.assertFalse(Usuario.objects.filter(correo="nuevo@filmai.com").exists())

    def test_un_nombre_comun_se_registra(self):
        respuesta = self._registrar("badminton")

        self.assertEqual(respuesta.status_code, 201, respuesta.content)


class AltaConGoogleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_un_nombre_reservado_es_400_sin_crear_la_cuenta(self):
        with patch(
            "allauth.socialaccount.providers.google.views._verify_and_decode",
            return_value={
                "sub": "sub-reservado",
                "email": "google@example.com",
                "email_verified": True,
            },
        ):
            respuesta = Client().post(
                "/api/auth/google/",
                {
                    "id_token": "token",
                    "nombre_usuario": "soporteoficial",
                    "fecha_nacimiento": "1995-05-05",
                    "genero": "no_especifica",
                    "pais": "AR",
                    "acepta_terminos": True,
                },
                content_type="application/json",
            )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            "username_not_allowed",
            {error["code"] for error in respuesta.json()["errors"]},
        )
        self.assertFalse(Usuario.objects.filter(correo="google@example.com").exists())


class PerfilTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def _cliente(self, usuario):
        cliente = Client()
        cliente.defaults["HTTP_AUTHORIZATION"] = (
            f"Bearer {AccessToken.for_user(usuario)}"
        )
        return cliente

    def test_no_se_puede_cambiar_a_un_nombre_reservado(self):
        usuario = UsuarioFactory(nombre_usuario="cinefilo")

        respuesta = self._cliente(usuario).put(
            "/api/profile/",
            {"nombre_usuario": "admin"},
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["errors"], ERROR)
        usuario.refresh_from_db()
        self.assertEqual(usuario.nombre_usuario, "cinefilo")

    def test_quien_ya_lo_tenia_puede_guardar_el_perfil(self):
        # Cuentas anteriores a la regla: guardar el perfil no las obliga a
        # cambiarse el nombre.
        usuario = UsuarioFactory(nombre_usuario="staff")

        respuesta = self._cliente(usuario).put(
            "/api/profile/",
            {"nombre_usuario": "staff", "nombre": "Ana"},
            content_type="application/json",
        )

        self.assertEqual(respuesta.status_code, 200, respuesta.content)


class DisponibilidadTests(TestCase):
    def test_un_reservado_no_esta_disponible_y_dice_por_que(self):
        # Cinco caracteres o más: «r00t» ya no pasa el largo mínimo, sin llegar a la regla.
        respuesta = Client().get("/api/auth/username-available/", {"username": "Adm1n"})

        self.assertEqual(respuesta.json(), {"disponible": False, "motivo": "reservado"})

    def test_uno_libre_sigue_igual(self):
        respuesta = Client().get(
            "/api/auth/username-available/", {"username": "badminton"}
        )

        self.assertEqual(respuesta.json(), {"disponible": True})
