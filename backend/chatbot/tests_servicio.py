"""`guardar_turno()`: la pregunta, la respuesta y lo recomendado, todo o nada."""

from unittest.mock import patch

from django.db import DatabaseError
from django.test import SimpleTestCase, TestCase

from chatbot.eventos import Resultado
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.prompts import armar_sistema
from chatbot.servicio import guardar_turno, sumar_recomendados
from usuarios.factories import UsuarioFactory


def tarjeta(id_tmdb, titulo="Moon", tipo="movie", anio=2009):
    return {
        "id_tmdb": id_tmdb,
        "tipo": tipo,
        "titulo": titulo,
        "poster": f"/p{id_tmdb}.jpg",
        "anio": anio,
    }


def recordada(id_tmdb, titulo="Moon", tipo="movie", anio=2009):
    """Lo que queda en `ya_recomendados`: la tarjeta sin el póster."""
    return {"id_tmdb": id_tmdb, "tipo": tipo, "titulo": titulo, "anio": anio}


class GuardarTurnoTests(TestCase):
    def setUp(self):
        # El chat lo crea el signal al crear el usuario (doc 03): no hay que
        # crearlo, y crear otro chocaría con el único por usuario.
        self.chat = UsuarioFactory().chats.get()

    def test_guarda_la_pregunta_y_la_respuesta(self):
        tarjetas = [tarjeta(17431), tarjeta(348, "Alien", anio=1979)]

        pregunta, respuesta = guardar_turno(
            self.chat, "Algo como Moon", Resultado("Probá estas.", tarjetas)
        )

        self.assertEqual(pregunta.autor, TipoAutor.USUARIO)
        self.assertEqual(pregunta.texto, "Algo como Moon")
        self.assertEqual(pregunta.tarjetas, [])
        self.assertEqual(respuesta.autor, TipoAutor.CHATBOT)
        self.assertEqual(respuesta.texto, "Probá estas.")
        self.assertEqual(respuesta.tarjetas, tarjetas)
        self.assertEqual(Mensaje.objects.filter(chat=self.chat).count(), 2)

    def test_la_pregunta_queda_antes_que_la_respuesta(self):
        pregunta, respuesta = guardar_turno(self.chat, "Hola", Resultado("Hola."))

        historial = list(Mensaje.objects.order_by("-fecha_hora", "-id"))

        self.assertEqual(historial, [respuesta, pregunta])

    def test_un_mensaje_sin_tarjetas_queda_con_lista_vacia(self):
        mensaje = Mensaje.objects.create(
            chat=self.chat, texto="Hola", autor=TipoAutor.USUARIO
        )

        mensaje.refresh_from_db()
        self.assertEqual(mensaje.tarjetas, [])

    def test_suma_las_tarjetas_a_ya_recomendados_sin_poster(self):
        guardar_turno(self.chat, "Ciencia ficción", Resultado("Esta.", [tarjeta(1)]))

        self.chat.refresh_from_db()
        self.assertEqual(self.chat.contexto["ya_recomendados"], [recordada(1)])

    def test_conserva_las_otras_claves_del_contexto(self):
        Chat.objects.filter(pk=self.chat.pk).update(contexto={"otra": "clave"})

        guardar_turno(self.chat, "Ciencia ficción", Resultado("Esta.", [tarjeta(1)]))

        self.chat.refresh_from_db()
        self.assertEqual(self.chat.contexto["otra"], "clave")

    def test_sin_tarjetas_no_cambia_ya_recomendados(self):
        previas = [recordada(1)]
        Chat.objects.filter(pk=self.chat.pk).update(
            contexto={"ya_recomendados": previas}
        )

        guardar_turno(self.chat, "¿Cuánto dura?", Resultado("Dos horas."))

        self.chat.refresh_from_db()
        self.assertEqual(self.chat.contexto["ya_recomendados"], previas)
        self.assertEqual(Mensaje.objects.filter(chat=self.chat).count(), 2)

    def test_si_falla_el_ultimo_paso_no_queda_nada(self):
        previas = [recordada(1)]
        Chat.objects.filter(pk=self.chat.pk).update(
            contexto={"ya_recomendados": previas}
        )

        # El último paso es guardar el contexto: cuando falla, los dos INSERT ya
        # corrieron. Si después no hay mensajes, el ROLLBACK los deshizo.
        with patch.object(Chat, "save", side_effect=DatabaseError("caída")):
            with self.assertRaises(DatabaseError):
                guardar_turno(self.chat, "Hola", Resultado("Esta.", [tarjeta(2)]))

        self.assertEqual(Mensaje.objects.filter(chat=self.chat).count(), 0)
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.contexto["ya_recomendados"], previas)

    def test_lo_guardado_le_sirve_al_prompt_del_motor(self):
        """El formato que escribe el Canal es el que lee el Motor (PR 3)."""
        guardar_turno(self.chat, "Algo raro", Resultado("Esta.", [tarjeta(17431)]))

        self.chat.refresh_from_db()
        sistema = armar_sistema("", self.chat.contexto["ya_recomendados"], "es")

        self.assertIn("Ya recomendados: Moon (2009)", sistema)
        self.assertNotIn("17431", sistema)


class PrecalentarTarjetasTests(TestCase):
    """Las tarjetas del chat encolan la materialización de sus títulos.

    Entrar a la ficha desde el chat era siempre en frío: la tarjeta nunca
    pasaba por un listado del catálogo, así que nadie había pedido a TMDB el
    detalle ni los créditos (medido el 13/11/2026: 0,4 a 1,1 s). Encolarlos al
    emitir las tarjetas deja la caché de Redis lista antes del clic.
    """

    ENCOLAR = "chatbot.servicio.materializar_listado_en_segundo_plano"

    def setUp(self):
        self.chat = UsuarioFactory().chats.get()

    def test_encola_los_titulos_de_las_tarjetas(self):
        tarjetas = [tarjeta(17431), tarjeta(1399, "GoT", tipo="tv", anio=2011)]

        with patch(self.ENCOLAR) as encolar:
            guardar_turno(self.chat, "Algo", Resultado("Estas.", tarjetas))

        # Mismo formato que un listado de TMDB: `id` y `media_type` por ítem.
        encolar.assert_called_once_with(
            [
                {"id": 17431, "media_type": "movie"},
                {"id": 1399, "media_type": "tv"},
            ]
        )

    def test_sin_tarjetas_no_encola_nada(self):
        with patch(self.ENCOLAR) as encolar:
            guardar_turno(self.chat, "¿Cuánto dura?", Resultado("Dos horas."))

        encolar.assert_not_called()

    def test_si_el_broker_falla_el_turno_se_guarda_igual(self):
        # Celery o Redis caídos no pueden costarle el turno al usuario.
        with patch(self.ENCOLAR, side_effect=ConnectionError("broker")):
            with self.assertLogs("chatbot.servicio", level="ERROR"):
                pregunta, respuesta = guardar_turno(
                    self.chat, "Algo", Resultado("Esta.", [tarjeta(1)])
                )

        self.assertEqual(respuesta.tarjetas, [tarjeta(1)])
        self.assertEqual(Mensaje.objects.filter(chat=self.chat).count(), 2)

    def test_si_el_guardado_falla_no_se_encola_nada(self):
        # Las tarjetas de un turno que se deshizo nunca se le mostraron al usuario.
        with patch(self.ENCOLAR) as encolar:
            with patch.object(Chat, "save", side_effect=DatabaseError("caída")):
                with self.assertRaises(DatabaseError):
                    guardar_turno(self.chat, "Hola", Resultado("Esta.", [tarjeta(2)]))

        encolar.assert_not_called()


class SumarRecomendadosTests(SimpleTestCase):
    """La regla de la lista, sin base: es una función pura."""

    def test_un_repetido_pasa_al_final_sin_duplicarse(self):
        previas = [recordada(1), recordada(2, "Alien"), recordada(3, "Solaris")]

        lista = sumar_recomendados(previas, [tarjeta(1)])

        self.assertEqual([t["id_tmdb"] for t in lista], [2, 3, 1])

    def test_un_repetido_dentro_del_mismo_turno_queda_una_vez(self):
        lista = sumar_recomendados([], [tarjeta(1), tarjeta(1)])

        self.assertEqual(lista, [recordada(1)])

    def test_la_misma_id_en_pelicula_y_serie_son_dos_titulos(self):
        # TMDB numera películas y series por separado: 1399 puede ser las dos.
        previas = [recordada(1399, "Una película")]

        lista = sumar_recomendados(previas, [tarjeta(1399, "Una serie", tipo="tv")])

        self.assertEqual(len(lista), 2)

    def test_el_tope_de_30_conserva_las_mas_recientes(self):
        previas = [recordada(i, f"Viejo {i}") for i in range(29)]

        lista = sumar_recomendados(previas, [tarjeta(100), tarjeta(101), tarjeta(102)])

        self.assertEqual(len(lista), 30)
        self.assertEqual(lista[0]["id_tmdb"], 2)  # se fueron la 0 y la 1
        self.assertEqual([t["id_tmdb"] for t in lista[-3:]], [100, 101, 102])

    def test_anio_desconocido_se_guarda_como_none(self):
        lista = sumar_recomendados([], [tarjeta(5, anio=None)])

        self.assertIsNone(lista[0]["anio"])
