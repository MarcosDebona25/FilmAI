"""La ruta que el panel llama al abrirse, para que el modelo cargue antes de preguntar."""

from unittest.mock import patch

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

    def test_con_sesion_pide_la_carga_y_no_espera(self):
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

    def test_get_no_esta_permitido(self):
        self.client.force_authenticate(UsuarioFactory())

        self.assertEqual(self.client.get(URL).status_code, 405)
