"""Revisión de seguridad del 24/10/2026: `/admin/login/` sin límite de intentos.

Django no limita el formulario del admin. Con un correo de staff conocido se
podían probar contraseñas sin tope. Ahora usa el mismo bloqueo que el login de
la documentación: 10 fallos por IP bloquean 60 minutos.
"""

from django.core.cache import cache
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase

from filmai.documentation import con_limite_de_intentos
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

        # Sin el reinicio irían 19 intentos: con 9 fallos más tiene que seguir
        # entrando (la primera versión del test pasaba aunque no se reiniciara).
        for _ in range(9):
            self._intentar("incorrecta")
        self.assertEqual(self._intentar("Password123!").status_code, 302)

    def test_el_intento_se_cuenta_antes_de_probar_la_contrasena(self):
        # Es lo que impide que una ráfaga en paralelo pase toda el chequeo:
        # mientras la vista autentica, el intento ya está contado.
        vistos = []

        def vista(request):
            vistos.append(cache.get("admin-login:203.0.113.7"))
            return HttpResponse(status=200)

        pedido = RequestFactory().post(LOGIN_ADMIN, REMOTE_ADDR="203.0.113.7")
        con_limite_de_intentos(vista)(pedido)

        self.assertEqual(vistos, [1])

    def test_el_bloqueo_avisa_cuanto_esperar_y_no_se_cachea(self):
        for _ in range(10):
            self._intentar("incorrecta")

        respuesta = self._intentar("Password123!")

        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(respuesta["Retry-After"], "3600")
        self.assertIn("no-store", respuesta["Cache-Control"])

    def test_un_post_sin_token_csrf_no_cuenta(self):
        # PR-Agent (#133) temía que un sitio ajeno agotara el contador de una IP
        # con POST falsos. El middleware de CSRF los corta con 403 antes de
        # llegar a la vista, así que no suman.
        sin_csrf = Client(enforce_csrf_checks=True)
        for _ in range(15):
            respuesta = sin_csrf.post(
                LOGIN_ADMIN,
                {"username": self.staff.correo, "password": "incorrecta"},
                REMOTE_ADDR="203.0.113.7",
            )
            self.assertEqual(respuesta.status_code, 403)

        self.assertIsNone(cache.get("admin-login:203.0.113.7"))
        self.assertEqual(self._intentar("Password123!").status_code, 302)

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
