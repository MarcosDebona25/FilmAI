"""La ruta que el panel llama al abrirse, para que el modelo cargue antes de preguntar."""

from unittest.mock import patch

from django.test import Client
from rest_framework.test import APIClient, APITestCase

from usuarios.factories import UsuarioFactory

URL = "/api/chat/preparar/"


class PrepararChatTests(APITestCase):
    def test_sin_sesion_es_401(self):
        with patch("chatbot.views.pedir_carga_del_modelo") as pedir:
            respuesta = APIClient().post(URL)

        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.data["code"], "not_authenticated")
        pedir.assert_not_called()

    def test_con_sesion_pide_la_carga(self):
        self.client.force_authenticate(UsuarioFactory())

        with patch("chatbot.views.pedir_carga_del_modelo") as pedir:
            respuesta = self.client.post(URL)

        self.assertEqual(respuesta.status_code, 202)
        pedir.assert_called_once_with()

    def test_si_la_cache_falla_igual_responde_202(self):
        self.client.force_authenticate(UsuarioFactory())

        with patch("catalogo.services.semantica.cache") as cache_caida:
            cache_caida.add.side_effect = ConnectionError("redis")
            respuesta = self.client.post(URL)

        self.assertEqual(respuesta.status_code, 202)

    def sesion_real(self):
        """Login de verdad, con cookies y CSRF activo: lo que hace el navegador."""
        usuario = UsuarioFactory(correo="chat@filmai.com")
        usuario.set_password("Password123!")
        usuario.save()
        cliente = Client(enforce_csrf_checks=True)
        cliente.get("/api/auth/csrf/")
        login = cliente.post(
            "/api/auth/login/",
            {"email": "chat@filmai.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, 200)
        return cliente

    def test_con_la_cookie_de_sesion_y_csrf_funciona(self):
        cliente = self.sesion_real()
        csrf = cliente.cookies["csrftoken"].value

        with patch("chatbot.views.pedir_carga_del_modelo") as pedir:
            respuesta = cliente.post(URL, HTTP_X_CSRFTOKEN=csrf)

        self.assertEqual(respuesta.status_code, 202)
        pedir.assert_called_once_with()

    def test_con_la_cookie_y_sin_csrf_se_rechaza_con_json(self):
        cliente = self.sesion_real()

        with patch("chatbot.views.pedir_carga_del_modelo") as pedir:
            respuesta = cliente.post(URL)

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()["code"], "permission_denied")
        pedir.assert_not_called()

    def test_get_no_esta_permitido(self):
        self.client.force_authenticate(UsuarioFactory())

        self.assertEqual(self.client.get(URL).status_code, 405)
