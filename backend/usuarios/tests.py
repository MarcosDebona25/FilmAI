"""Tests de disponibilidad de nombre de usuario (A-05)."""

from django.test import TestCase

from .factories import UsuarioFactory


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
