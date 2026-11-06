"""`GET /api/chat/messages/`: el historial que el panel muestra al abrirse (PR 7)."""

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from chatbot.models import Mensaje, TipoAutor
from usuarios.factories import UsuarioFactory

URL = "/api/chat/messages/"
CAMPOS = {"id", "autor", "texto", "tarjetas", "fecha_hora"}


class HistorialTests(APITestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        # El chat lo crea el signal al crear el usuario (doc 03).
        self.chat = self.usuario.chats.get()
        self.client.force_authenticate(self.usuario)
        self.base = timezone.now() - timedelta(days=1)

    def mensaje(self, texto, minuto, *, chat=None, **campos):
        """Un mensaje con la hora fijada a mano.

        `auto_now_add` pisa cualquier `fecha_hora` que se pase al crear, así que
        se corrige después con `update()`, que va directo al SQL.
        """
        mensaje = Mensaje.objects.create(
            chat=chat or self.chat,
            texto=texto,
            autor=campos.pop("autor", TipoAutor.USUARIO),
            **campos,
        )
        Mensaje.objects.filter(pk=mensaje.pk).update(
            fecha_hora=self.base + timedelta(minutes=minuto)
        )
        return mensaje

    def textos(self, respuesta):
        return [fila["texto"] for fila in respuesta.data["results"]]

    def test_sin_sesion_es_401(self):
        respuesta = APIClient().get(URL)

        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.data["code"], "not_authenticated")

    def test_sin_mensajes_devuelve_una_lista_vacia(self):
        respuesta = self.client.get(URL)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["results"], [])
        self.assertIsNone(respuesta.data["next"])

    def test_van_de_mas_nuevo_a_mas_viejo(self):
        self.mensaje("primero", 1)
        self.mensaje("tercero", 3)
        self.mensaje("segundo", 2)

        respuesta = self.client.get(URL)

        self.assertEqual(self.textos(respuesta), ["tercero", "segundo", "primero"])

    def test_llegan_de_a_20(self):
        for minuto in range(25):
            self.mensaje(f"m{minuto}", minuto)

        respuesta = self.client.get(URL)

        self.assertEqual(len(respuesta.data["results"]), 20)
        self.assertIsNotNone(respuesta.data["next"])

    def test_la_segunda_pagina_trae_el_resto_sin_repetir(self):
        for minuto in range(25):
            self.mensaje(f"m{minuto}", minuto)

        primera = self.client.get(URL)
        segunda = self.client.get(primera.data["next"])

        self.assertEqual(self.textos(segunda), ["m4", "m3", "m2", "m1", "m0"])
        self.assertIsNone(segunda.data["next"])

    def test_un_mensaje_nuevo_entre_paginas_no_hace_repetir_nada(self):
        """La razón del cursor: con offset, la página 2 repetiría «m5»."""
        for minuto in range(25):
            self.mensaje(f"m{minuto}", minuto)
        primera = self.client.get(URL)

        self.mensaje("llegó mientras leías", 100)
        segunda = self.client.get(primera.data["next"])

        self.assertEqual(self.textos(segunda), ["m4", "m3", "m2", "m1", "m0"])

    def test_con_la_misma_hora_desempata_por_id(self):
        pregunta = self.mensaje("pregunta", 5)
        respuesta_bot = self.mensaje("respuesta", 5, autor=TipoAutor.CHATBOT)

        respuesta = self.client.get(URL)

        ids = [fila["id"] for fila in respuesta.data["results"]]
        self.assertEqual(ids, [respuesta_bot.id, pregunta.id])

    def test_solo_los_mensajes_propios(self):
        otro_chat = UsuarioFactory().chats.get()
        self.mensaje("mío", 1)
        self.mensaje("ajeno", 2, chat=otro_chat)

        respuesta = self.client.get(URL)

        self.assertEqual(self.textos(respuesta), ["mío"])

    def test_cada_mensaje_trae_exactamente_sus_campos(self):
        self.mensaje("hola", 1)

        respuesta = self.client.get(URL)

        self.assertEqual(set(respuesta.data["results"][0]), CAMPOS)
        self.assertEqual(respuesta.data["results"][0]["autor"], "usuario")

    def test_las_tarjetas_vuelven_tal_como_se_guardaron(self):
        tarjetas = [
            {
                "id_tmdb": 17431,
                "tipo": "movie",
                "titulo": "Luna",
                "poster": None,
                "anio": 2009,
            }
        ]
        self.mensaje("Mirá esta.", 1, autor=TipoAutor.CHATBOT, tarjetas=tarjetas)

        # En inglés, el título guardado en español no se vuelve a traducir.
        respuesta = self.client.get(URL, HTTP_ACCEPT_LANGUAGE="en")

        self.assertEqual(respuesta.data["results"][0]["tarjetas"], tarjetas)

    def test_la_respuesta_no_trae_total(self):
        respuesta = self.client.get(URL)

        self.assertEqual(set(respuesta.data), {"next", "previous", "results"})
