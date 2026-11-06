"""La aplicación ASGI responde igual que bajo WSGI (PR 5 del chatbot, tarea 5.2).

`manage.py test` no levanta un servidor, y los e2e de Playwright mockean la API: sin
estos tests, pasar `runserver` a `daphne` podría romper un endpoint de DRF sin que
nada avise. Se llama a `get_asgi_application()` a mano, con el protocolo ASGI.
"""

import json

from django.conf import settings
from django.test import Client, TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from filmai.pruebas_asgi import pedir
from usuarios.factories import UsuarioFactory


class AplicacionASGITests(TransactionTestCase):
    def test_la_configuracion_apunta_a_la_aplicacion_asgi(self):
        self.assertEqual(settings.ASGI_APPLICATION, "filmai.asgi.application")
        self.assertEqual(settings.INSTALLED_APPS[0], "daphne")

    async def test_una_lectura_publica_de_drf_responde_como_en_wsgi(self):
        respuesta = await pedir("GET", "/api/auth/csrf/")

        self.assertEqual(respuesta.estado, 200)
        self.assertEqual(respuesta.json()["code"], "csrf_ready")
        self.assertIn("csrftoken", respuesta.encabezados["set-cookie"])

    async def test_una_ruta_protegida_sin_sesion_es_401_con_el_sobre(self):
        respuesta = await pedir("GET", "/api/profile/")

        self.assertEqual(respuesta.estado, 401)
        self.assertEqual(respuesta.json()["code"], "not_authenticated")

    def sesion(self):
        usuario = UsuarioFactory()
        csrf = Client().get("/api/auth/csrf/").cookies["csrftoken"].value
        acceso = str(RefreshToken.for_user(usuario).access_token)
        return csrf, f"access={acceso}; csrftoken={csrf}"

    async def test_una_escritura_autenticada_con_csrf_funciona(self):
        from asgiref.sync import sync_to_async

        csrf, cookies = await sync_to_async(self.sesion)()
        cuerpo = json.dumps({"idioma": "en"}).encode()

        respuesta = await pedir(
            "PUT",
            "/api/profile/",
            cuerpo=cuerpo,
            encabezados={
                "content-type": "application/json",
                "cookie": cookies,
                "x-csrftoken": csrf,
            },
        )

        self.assertEqual(respuesta.estado, 200, respuesta.cuerpo)

    async def test_una_escritura_sin_csrf_es_403_en_json(self):
        from asgiref.sync import sync_to_async

        _, cookies = await sync_to_async(self.sesion)()

        respuesta = await pedir(
            "PUT",
            "/api/profile/",
            cuerpo=b'{"idioma": "en"}',
            encabezados={"content-type": "application/json", "cookie": cookies},
        )

        self.assertEqual(respuesta.estado, 403)
        self.assertEqual(respuesta.json()["code"], "permission_denied")
