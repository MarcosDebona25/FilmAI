"""Recorte nocturno de las tarjetas del chat y rehidratación al leer (#180, PR 3).

TMDB no deja guardar su contenido más de 180 días sin refrescarlo. Las tarjetas
de un mensaje viejo llevan título y póster copiados de TMDB, así que cada noche se
recortan a `{id_tmdb, tipo}` y el historial las reconstruye desde el catálogo local.
"""

from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from catalogo.factories import ProduccionAudiovisualFactory
from catalogo.models import ProduccionTraduccion, TipoProduccion
from chatbot.eventos import Resultado
from chatbot.models import Mensaje, TipoAutor
from chatbot.prompts import armar_sistema
from chatbot.recorte import recortar
from chatbot.servicio import guardar_turno, sumar_recomendados, titulos_recordados
from usuarios.factories import UsuarioFactory

URL = "/api/chat/messages/"


def tarjeta(id_tmdb, titulo="Moon", tipo="movie", anio=2009):
    return {
        "id_tmdb": id_tmdb,
        "tipo": tipo,
        "titulo": titulo,
        "poster": f"/p{id_tmdb}.jpg",
        "anio": anio,
        "nota_tmdb": 7.8,
    }


def hace(dias):
    return timezone.now() - timedelta(days=dias)


def fecha_hace(dias):
    return (timezone.localdate() - timedelta(days=dias)).isoformat()


class BaseChat:
    def preparar(self):
        self.usuario = UsuarioFactory()
        # El chat lo crea el signal al crear el usuario (doc 03).
        self.chat = self.usuario.chats.get()

    def mensaje(self, dias, tarjetas):
        """Un mensaje del bot de hace `dias` días.

        `auto_now_add` pisa `fecha_hora` al crear: se corrige con `update()`, que
        va directo al SQL.
        """
        mensaje = Mensaje.objects.create(
            chat=self.chat,
            autor=TipoAutor.CHATBOT,
            texto="Probá estas.",
            tarjetas=tarjetas,
        )
        Mensaje.objects.filter(pk=mensaje.pk).update(fecha_hora=hace(dias))
        return mensaje


class RecorteDeMensajesTests(BaseChat, TestCase):
    def setUp(self):
        self.preparar()

    def test_las_tarjetas_de_un_mensaje_viejo_quedan_con_id_y_tipo(self):
        viejo = self.mensaje(181, [tarjeta(1), tarjeta(2, "Alien", "tv")])

        recortar()

        viejo.refresh_from_db()
        self.assertEqual(
            viejo.tarjetas,
            [{"id_tmdb": 1, "tipo": "movie"}, {"id_tmdb": 2, "tipo": "tv"}],
        )

    def test_un_mensaje_reciente_no_se_toca(self):
        reciente = self.mensaje(30, [tarjeta(1)])
        justo = self.mensaje(179, [tarjeta(2)])

        recortar()

        reciente.refresh_from_db()
        justo.refresh_from_db()
        self.assertEqual(reciente.tarjetas, [tarjeta(1)])
        self.assertEqual(justo.tarjetas, [tarjeta(2)])

    def test_una_segunda_corrida_no_cambia_nada(self):
        self.mensaje(200, [tarjeta(1)])
        self.mensaje(10, [tarjeta(2)])

        primera = recortar()
        segunda = recortar()

        self.assertEqual(primera["mensajes"], 1)
        self.assertEqual(segunda["mensajes"], 0)

    def test_un_mensaje_sin_tarjetas_no_cuenta(self):
        self.mensaje(300, [])

        self.assertEqual(recortar()["mensajes"], 0)

    def test_un_mensaje_a_medio_recortar_se_completa(self):
        # Una tarjeta ya recortada no se rompe y la que conserva título sí se recorta.
        viejo = self.mensaje(200, [{"id_tmdb": 1, "tipo": "movie"}, tarjeta(2)])

        recortar()

        viejo.refresh_from_db()
        self.assertEqual(
            viejo.tarjetas,
            [{"id_tmdb": 1, "tipo": "movie"}, {"id_tmdb": 2, "tipo": "movie"}],
        )


class RecorteDeRecomendadosTests(BaseChat, TestCase):
    def setUp(self):
        self.preparar()

    def con_recomendados(self, entradas):
        self.chat.contexto = {"ya_recomendados": entradas}
        self.chat.save(update_fields=["contexto"])

    def entrada(self, id_tmdb, fecha, titulo="Moon"):
        datos = {"id_tmdb": id_tmdb, "tipo": "movie", "titulo": titulo, "anio": 2009}
        if fecha is not None:
            datos["fecha"] = fecha
        return datos

    def test_una_entrada_vieja_pierde_titulo_y_anio_y_conserva_fecha(self):
        self.con_recomendados([self.entrada(1, fecha_hace(181))])

        recortar()

        self.chat.refresh_from_db()
        self.assertEqual(
            self.chat.contexto["ya_recomendados"],
            [{"id_tmdb": 1, "tipo": "movie", "fecha": fecha_hace(181)}],
        )

    def test_una_entrada_sin_fecha_se_trata_como_vieja(self):
        # Las que se escribieron antes de este cambio no tienen fecha.
        self.con_recomendados([self.entrada(1, None)])

        recortar()

        self.chat.refresh_from_db()
        self.assertEqual(
            self.chat.contexto["ya_recomendados"], [{"id_tmdb": 1, "tipo": "movie"}]
        )

    def test_una_entrada_reciente_no_se_toca(self):
        reciente = self.entrada(1, fecha_hace(10))
        self.con_recomendados([reciente])

        recortar()

        self.chat.refresh_from_db()
        self.assertEqual(self.chat.contexto["ya_recomendados"], [reciente])

    def test_solo_se_reescriben_los_chats_que_cambian(self):
        self.con_recomendados([self.entrada(1, fecha_hace(181))])
        otro = UsuarioFactory().chats.get()
        otro.contexto = {"ya_recomendados": [self.entrada(2, fecha_hace(5))]}
        otro.save(update_fields=["contexto"])

        self.assertEqual(recortar()["chats"], 1)
        self.assertEqual(recortar()["chats"], 0)

    def test_relee_el_chat_con_candado_y_no_pisa_un_turno_reciente(self):
        # La primera pasada vio una entrada vieja; antes del candado, un turno del
        # usuario escribió otra reciente. La tarea tiene que partir de lo guardado.
        self.con_recomendados([self.entrada(1, fecha_hace(181))])
        reciente = self.entrada(2, fecha_hace(0))

        def turno_a_mitad_de_corrida(*args, **kwargs):
            self.chat.contexto = {"ya_recomendados": [reciente], "otra": 1}
            self.chat.save(update_fields=["contexto"])
            return [self.chat.pk]

        with patch("chatbot.recorte._candidatos", turno_a_mitad_de_corrida):
            self.assertEqual(recortar()["chats"], 0)

        self.chat.refresh_from_db()
        self.assertEqual(self.chat.contexto, {"ya_recomendados": [reciente], "otra": 1})

    def test_un_chat_sin_contexto_no_falla(self):
        self.assertEqual(recortar()["chats"], 0)


class FechaDeRecomendadosTests(BaseChat, TestCase):
    def setUp(self):
        self.preparar()

    def test_guardar_un_turno_escribe_la_fecha_de_hoy(self):
        guardar_turno(self.chat, "Algo", Resultado("Va.", [tarjeta(1)]))

        self.chat.refresh_from_db()
        self.assertEqual(
            self.chat.contexto["ya_recomendados"],
            [
                {
                    "id_tmdb": 1,
                    "tipo": "movie",
                    "titulo": "Moon",
                    "anio": 2009,
                    "fecha": timezone.localdate().isoformat(),
                }
            ],
        )

    def test_volver_a_mostrar_una_tarjeta_renueva_su_fecha(self):
        vieja = {
            "id_tmdb": 1,
            "tipo": "movie",
            "titulo": "Moon",
            "anio": 2009,
            "fecha": fecha_hace(170),
        }

        lista = sumar_recomendados([vieja], [tarjeta(1)])

        self.assertEqual(lista[0]["fecha"], timezone.localdate().isoformat())

    def test_las_entradas_que_no_se_muestran_conservan_su_fecha(self):
        vieja = {"id_tmdb": 2, "tipo": "movie", "fecha": fecha_hace(170)}

        lista = sumar_recomendados([vieja], [tarjeta(1)])

        self.assertEqual(lista[0], vieja)


class TitulosRecordadosTests(TestCase):
    def test_resuelve_en_una_sola_query_los_titulos_recortados(self):
        a = ProduccionAudiovisualFactory(
            id_tmdb=10, tipo=TipoProduccion.PELICULA, titulo="Moon"
        )
        b = ProduccionAudiovisualFactory(
            id_tmdb=11, tipo=TipoProduccion.SERIE, titulo="Fargo"
        )
        recortadas = [
            {"id_tmdb": a.id_tmdb, "tipo": "movie", "fecha": "2026-01-01"},
            {"id_tmdb": b.id_tmdb, "tipo": "tv", "fecha": "2026-01-01"},
        ]

        with self.assertNumQueries(1):
            titulos = titulos_recordados(recortadas)

        self.assertEqual(
            [t["titulo"] for t in titulos],
            ["Moon", "Fargo"],
        )

    def test_las_que_conservan_titulo_no_consultan_la_base(self):
        completas = [{"id_tmdb": 1, "tipo": "movie", "titulo": "Moon", "anio": 2009}]

        with self.assertNumQueries(0):
            titulos = titulos_recordados(completas)

        self.assertEqual(titulos, [{"titulo": "Moon", "anio": 2009}])

    def test_un_id_que_no_esta_en_el_catalogo_se_deja_afuera(self):
        recortadas = [{"id_tmdb": 99999, "tipo": "movie"}]

        self.assertEqual(titulos_recordados(recortadas), [])

    def test_una_lapida_se_deja_afuera(self):
        ProduccionAudiovisualFactory(
            id_tmdb=12,
            tipo=TipoProduccion.PELICULA,
            titulo="",
            disponible_en_tmdb=False,
        )

        self.assertEqual(titulos_recordados([{"id_tmdb": 12, "tipo": "movie"}]), [])

    def test_el_prompt_nombra_las_recortadas_y_las_completas(self):
        ProduccionAudiovisualFactory(
            id_tmdb=10,
            tipo=TipoProduccion.PELICULA,
            titulo="Moon",
            fecha_lanzamiento="2009-06-12",
        )
        entradas = [
            {"id_tmdb": 10, "tipo": "movie"},
            {"id_tmdb": 5, "tipo": "movie", "titulo": "Alien", "anio": 1979},
            {"id_tmdb": 99999, "tipo": "movie"},
        ]

        sistema = armar_sistema("", titulos_recordados(entradas), "es")

        self.assertIn("Ya recomendados: Moon (2009), Alien (1979)\n", sistema)
        self.assertNotIn("99999", sistema)


class RehidratacionDelHistorialTests(BaseChat, APITestCase):
    def setUp(self):
        self.preparar()
        self.client.force_authenticate(self.usuario)
        self.moon = ProduccionAudiovisualFactory(
            id_tmdb=10,
            tipo=TipoProduccion.PELICULA,
            titulo="Moon",
            poster="/moon-en.jpg",
            fecha_lanzamiento="2009-06-12",
            calificacion_promedio=7.84,
        )
        ProduccionTraduccion.objects.create(
            produccion=self.moon, idioma="es", titulo="Luna", poster="/luna-es.jpg"
        )

    def tarjetas_de(self, respuesta):
        return [t for fila in respuesta.data["results"] for t in fila["tarjetas"]]

    def test_una_tarjeta_recortada_vuelve_con_el_titulo_en_el_idioma_de_quien_lee(
        self,
    ):
        self.mensaje(200, [{"id_tmdb": 10, "tipo": "movie"}])

        en_es = self.client.get(URL, headers={"Accept-Language": "es"})
        en_en = self.client.get(URL, headers={"Accept-Language": "en"})

        self.assertEqual(
            self.tarjetas_de(en_es),
            [
                {
                    "id_tmdb": 10,
                    "tipo": "movie",
                    "titulo": "Luna",
                    "poster": "/luna-es.jpg",
                    "anio": 2009,
                    "nota_tmdb": 7.8,
                }
            ],
        )
        self.assertEqual(self.tarjetas_de(en_en)[0]["titulo"], "Moon")
        self.assertEqual(self.tarjetas_de(en_en)[0]["poster"], "/moon-en.jpg")

    def test_una_tarjeta_completa_se_devuelve_como_se_guardo(self):
        completa = tarjeta(10, "Luna de entonces")
        self.mensaje(5, [completa])

        respuesta = self.client.get(URL)

        self.assertEqual(self.tarjetas_de(respuesta), [completa])

    def test_una_produccion_que_falta_da_titulo_nulo(self):
        self.mensaje(200, [{"id_tmdb": 424242, "tipo": "movie"}])

        respuesta = self.client.get(URL)

        self.assertEqual(
            self.tarjetas_de(respuesta),
            [
                {
                    "id_tmdb": 424242,
                    "tipo": "movie",
                    "titulo": None,
                    "poster": None,
                    "anio": None,
                    "nota_tmdb": None,
                }
            ],
        )

    def test_una_lapida_da_titulo_nulo(self):
        ProduccionAudiovisualFactory(
            id_tmdb=11,
            tipo=TipoProduccion.PELICULA,
            titulo="",
            disponible_en_tmdb=False,
        )
        self.mensaje(200, [{"id_tmdb": 11, "tipo": "movie"}])

        respuesta = self.client.get(URL)

        self.assertIsNone(self.tarjetas_de(respuesta)[0]["titulo"])

    def test_la_misma_id_en_serie_y_pelicula_no_se_confunde(self):
        # TMDB numera películas y series por separado: 10 puede ser las dos.
        self.mensaje(200, [{"id_tmdb": 10, "tipo": "tv"}])

        respuesta = self.client.get(URL)

        self.assertIsNone(self.tarjetas_de(respuesta)[0]["titulo"])

    def test_las_queries_son_fijas_sin_importar_cuantas_tarjetas_hay(self):
        # Tres queries: los mensajes de la página, las producciones de todas sus
        # tarjetas recortadas y las traducciones de esas producciones. No una por
        # tarjeta: 6 tarjetas cuestan lo mismo que 1.
        for dias in range(200, 205):
            otra = ProduccionAudiovisualFactory(id_tmdb=100 + dias)
            tipo = "movie" if otra.tipo == TipoProduccion.PELICULA else "tv"
            self.mensaje(dias, [{"id_tmdb": otra.id_tmdb, "tipo": tipo}])
        self.mensaje(300, [{"id_tmdb": 10, "tipo": "movie"}])

        with self.assertNumQueries(3):
            respuesta = self.client.get(URL, headers={"Accept-Language": "es"})

        self.assertEqual(len(self.tarjetas_de(respuesta)), 6)

    def test_no_llama_a_tmdb(self):
        self.mensaje(200, [{"id_tmdb": 10, "tipo": "movie"}])

        with (
            patch("catalogo.services.tmdb.get_catalog_service") as servicio,
            patch("catalogo.services.materialization.materializar") as materializar,
        ):
            self.client.get(URL)

        servicio.assert_not_called()
        materializar.assert_not_called()

    def test_leer_no_modifica_lo_guardado(self):
        viejo = self.mensaje(200, [{"id_tmdb": 10, "tipo": "movie"}])

        self.client.get(URL)

        viejo.refresh_from_db()
        self.assertEqual(viejo.tarjetas, [{"id_tmdb": 10, "tipo": "movie"}])


class CronogramaTests(TestCase):
    def test_la_tarea_corre_a_las_0430_despues_del_refresco(self):
        from celery.schedules import crontab

        entrada = settings.CELERY_BEAT_SCHEDULE["recortar-tarjetas"]

        self.assertEqual(entrada["task"], "chatbot.recortar_tarjetas")
        self.assertEqual(entrada["schedule"], crontab(hour=4, minute=30))

    def test_la_tarea_esta_registrada_en_celery(self):
        from filmai.celery import app

        # Fuerza el descubrimiento de `chatbot/tasks.py`.
        app.loader.import_default_modules()

        self.assertIn("chatbot.recortar_tarjetas", app.tasks)

    def test_la_tarea_devuelve_lo_que_recorto(self):
        from chatbot.tasks import recortar_tarjetas

        self.assertEqual(recortar_tarjetas(), {"mensajes": 0, "chats": 0})
