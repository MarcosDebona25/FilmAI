"""Revisión de seguridad del 24/10/2026: `/admin/login/` sin límite de intentos.

Django no limita el formulario del admin. Con un correo de staff conocido se
podían probar contraseñas sin tope. Ahora usa el mismo bloqueo que el login de
la documentación: 10 fallos por IP bloquean 60 minutos.
"""

from django.core.cache import cache
from django.test import Client, TestCase

from usuarios.factories import UsuarioFactory

LOGIN_ADMIN = "/admin/login/"


class LimiteLoginAdminTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.staff = UsuarioFactory(is_staff=True)
        self.client = Client()

    def _intentar(self, password, ip="203.0.113.7"):
        return self.client.post(
            LOGIN_ADMIN,
            {"username": self.staff.correo, "password": password},
            REMOTE_ADDR=ip,
        )

    def test_diez_fallos_bloquean_y_ni_la_contrasena_correcta_entra(self):
        estados = [self._intentar("incorrecta").status_code for _ in range(10)]

        # Django responde 200 con el formulario y el error en cada fallo.
        self.assertEqual(estados, [200] * 10)
        self.assertEqual(self._intentar("Password123!").status_code, 429)

    def test_un_ingreso_correcto_reinicia_el_contador(self):
        for _ in range(9):
            self._intentar("incorrecta")

        self.assertEqual(self._intentar("Password123!").status_code, 302)
        self.client.logout()
        self.assertEqual(self._intentar("incorrecta").status_code, 200)

    def test_el_bloqueo_es_por_ip(self):
        for _ in range(10):
            self._intentar("incorrecta")

        self.assertEqual(
            self._intentar("Password123!", ip="198.51.100.2").status_code, 302
        )

    def test_ver_el_formulario_no_cuenta(self):
        for _ in range(15):
            self.client.get(LOGIN_ADMIN, REMOTE_ADDR="203.0.113.7")

        self.assertEqual(self._intentar("Password123!").status_code, 302)
