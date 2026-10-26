"""Auditoría 24/10/2026: las rutas de acceso sin barra final esquivaban F2.

dj-rest-auth registra sus rutas con `/?` (`login/?$`). Las vistas propias, que
llevan los límites de F2, estaban montadas solo con barra final: un `POST` a
`/api/auth/login` (sin barra) caía en la `LoginView` original, sin límite de
intentos, y `/api/auth/password/reset` en la original, sin el límite diario ni la
respuesta genérica. Mismo problema que ya se había resuelto a mano para
`password/change` y `token/refresh`.
"""

from django.core.cache import cache
from django.test import TestCase
from django.urls import resolve
from rest_framework.test import APIClient

from .factories import UsuarioFactory
from .views import LoginView, RecuperarContrasenaView, RestablecerContrasenaView


class RutasSinBarraTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()

    def test_cada_ruta_con_y_sin_barra_resuelve_a_la_misma_vista_propia(self):
        casos = [
            ("/api/auth/login", LoginView),
            ("/api/auth/password/reset", RecuperarContrasenaView),
            ("/api/auth/password/reset/confirm", RestablecerContrasenaView),
        ]
        for ruta, vista in casos:
            for variante in (ruta, f"{ruta}/"):
                with self.subTest(ruta=variante):
                    clase = resolve(variante).func.cls
                    self.assertIs(clase, vista)

    def test_el_login_sin_barra_termina_en_429(self):
        usuario = UsuarioFactory()
        cuerpo = {"email": usuario.correo, "password": "incorrecta"}

        estados = [
            self.client.post("/api/auth/login", cuerpo, format="json").status_code
            for _ in range(12)
        ]

        self.assertEqual(estados[:10], [400] * 10)
        self.assertEqual(estados[10:], [429, 429])

    def test_el_reset_sin_barra_tiene_el_limite_por_correo(self):
        cuerpo = {"email": "alguien@example.com"}

        estados = [
            self.client.post(
                "/api/auth/password/reset", cuerpo, format="json"
            ).status_code
            for _ in range(7)
        ]

        # Mismo comportamiento que con barra: 5 por día por correo.
        self.assertEqual(estados[5:], [429, 429])
