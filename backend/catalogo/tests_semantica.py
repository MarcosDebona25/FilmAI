"""Búsqueda semántica (B-06): vectores reales de Ollama y consulta por significado.

Ollama nunca se llama de verdad: `httpx.MockTransport` reemplaza la red y deja
ver qué pedido salió, cuántas veces y con qué timeout.
"""

import json
import logging
import math
from datetime import date, timedelta
from unittest.mock import patch

import httpx
from django.core.cache import cache
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from catalogo.models import (
    EstadoEmbedding,
    ProduccionAudiovisual,
    ProduccionEmbedding,
    TipoProduccion,
)
from catalogo.services.embeddings import (
    MODEL_VERSION,
    EmbeddingProviderError,
    generar_vector,
    modelo_cargado,
)
from catalogo.services.semantica import buscar_semantico, pedir_carga_del_modelo
from catalogo.tasks import (
    CLAVE_CARGA_MODELO,
    backfill_embeddings,
    calentar_modelo,
    generar_embedding,
)

VECTOR = [0.1] * 1024


def respuesta_ollama(vector=VECTOR):
    return httpx.Response(200, json={"model": "bge-m3", "embeddings": [vector]})


@override_settings(OLLAMA_URL="http://ollama.test:11434", OLLAMA_KEEP_ALIVE="30m")
class GenerarVectorTests(SimpleTestCase):
    def llamar(self, responder, **presupuesto):
        self.pedidos = []

        def registrar(request):
            self.pedidos.append(request)
            return responder(request)

        return generar_vector(
            "Title: Moon",
            transport=httpx.MockTransport(registrar),
            **presupuesto,
        )

    def test_pide_el_vector_a_ollama_y_lo_devuelve(self):
        vector = self.llamar(lambda request: respuesta_ollama())

        self.assertEqual(vector, VECTOR)
        pedido = self.pedidos[0]
        self.assertEqual(str(pedido.url), "http://ollama.test:11434/api/embed")
        self.assertEqual(
            json.loads(pedido.content),
            {"model": "bge-m3", "input": "Title: Moon", "keep_alive": "30m"},
        )

    def test_la_version_del_modelo_invalida_los_vectores_del_stub(self):
        self.assertEqual(MODEL_VERSION, "bge-m3")

    def test_sin_presupuesto_usa_el_del_backfill(self):
        self.llamar(lambda request: respuesta_ollama())

        self.assertEqual(self.pedidos[0].extensions["timeout"]["read"], 10)

    def test_backfill_tres_fallos_de_conexion_son_tres_intentos(self):
        def rechazar(request):
            raise httpx.ConnectError("rechazada", request=request)

        with self.assertRaises(EmbeddingProviderError):
            self.llamar(rechazar)

        self.assertEqual(len(self.pedidos), 3)

    def test_un_error_5xx_se_reintenta_y_puede_recuperarse(self):
        respuestas = iter([httpx.Response(503), respuesta_ollama()])

        vector = self.llamar(lambda request: next(respuestas))

        self.assertEqual(vector, VECTOR)
        self.assertEqual(len(self.pedidos), 2)

    def test_un_error_4xx_no_se_reintenta(self):
        # Por ejemplo, 404 si el modelo no está descargado: insistir no lo arregla.
        with self.assertRaises(EmbeddingProviderError):
            self.llamar(lambda request: httpx.Response(404))

        self.assertEqual(len(self.pedidos), 1)

    def test_chat_ollama_colgado_es_un_solo_intento_de_3_segundos(self):
        def colgarse(request):
            raise httpx.ReadTimeout("sin respuesta", request=request)

        with self.assertRaises(EmbeddingProviderError):
            self.llamar(colgarse, timeout=3, reintentos=0)

        self.assertEqual(len(self.pedidos), 1)
        self.assertEqual(self.pedidos[0].extensions["timeout"]["read"], 3)

    def test_una_dimension_inesperada_no_se_acepta(self):
        with self.assertRaises(EmbeddingProviderError):
            self.llamar(lambda request: respuesta_ollama([0.1] * 768))

    def test_una_respuesta_sin_vectores_no_se_acepta(self):
        with self.assertRaises(EmbeddingProviderError):
            self.llamar(lambda request: httpx.Response(200, json={"embeddings": []}))

    def test_un_vector_nulo_no_se_acepta(self):
        with self.assertRaises(EmbeddingProviderError):
            self.llamar(
                lambda request: httpx.Response(200, json={"embeddings": [None]})
            )

    def test_una_respuesta_que_no_es_json_no_se_acepta(self):
        with self.assertRaises(EmbeddingProviderError):
            self.llamar(lambda request: httpx.Response(200, text="<html>"))


@override_settings(OLLAMA_URL="http://ollama.test:11434", OLLAMA_KEEP_ALIVE="-1m")
class KeepAliveTests(SimpleTestCase):
    def test_sale_de_la_configuracion(self):
        pedidos = []

        def responder(request):
            pedidos.append(json.loads(request.content))
            return respuesta_ollama()

        generar_vector("hola", transport=httpx.MockTransport(responder))

        self.assertEqual(pedidos[0]["keep_alive"], "-1m")


@override_settings(OLLAMA_URL="http://ollama.test:11434")
class ModeloCargadoTests(SimpleTestCase):
    def consultar(self, responder):
        self.pedidos = []

        def registrar(request):
            self.pedidos.append(request)
            return responder(request)

        return modelo_cargado(transport=httpx.MockTransport(registrar))

    def test_cargado_si_figura_con_su_etiqueta(self):
        # Forma real de `/api/ps`, consultada el 05/11/2026.
        cargado = self.consultar(
            lambda request: httpx.Response(
                200, json={"models": [{"name": "bge-m3:latest"}]}
            )
        )

        self.assertTrue(cargado)
        self.assertEqual(str(self.pedidos[0].url), "http://ollama.test:11434/api/ps")

    def test_no_cargado_si_no_hay_modelos(self):
        self.assertFalse(
            self.consultar(lambda request: httpx.Response(200, json={"models": []}))
        )

    def test_no_cargado_si_hay_otro_modelo(self):
        self.assertFalse(
            self.consultar(
                lambda request: httpx.Response(
                    200, json={"models": [{"name": "bge-m3-otro:latest"}]}
                )
            )
        )

    def test_otra_variante_del_modelo_no_cuenta_como_cargado(self):
        # `/api/embed` pide `bge-m3`, que es `bge-m3:latest`: otra etiqueta es otra carga.
        self.assertFalse(
            self.consultar(
                lambda request: httpx.Response(
                    200, json={"models": [{"name": "bge-m3:567m"}]}
                )
            )
        )

    def test_una_entrada_sin_nombre_no_decide_el_resultado(self):
        self.assertTrue(
            self.consultar(
                lambda request: httpx.Response(
                    200, json={"models": [{"name": None}, {"name": "bge-m3:latest"}]}
                )
            )
        )

    def test_ollama_colgado_se_detecta_en_un_segundo(self):
        def colgarse(request):
            raise httpx.ReadTimeout("sin respuesta", request=request)

        with self.assertRaises(EmbeddingProviderError):
            self.consultar(colgarse)

        self.assertEqual(self.pedidos[0].extensions["timeout"]["read"], 1)

    def test_una_respuesta_rara_es_un_error_del_proveedor(self):
        for respuesta in (
            httpx.Response(200, text="<html>"),
            httpx.Response(200, json={"error": "algo"}),
            httpx.Response(200, json={"models": None}),
            httpx.Response(200, json={"models": [5]}),
        ):
            with (
                self.subTest(respuesta.text),
                self.assertRaises(EmbeddingProviderError),
            ):
                self.consultar(lambda request, r=respuesta: r)


def vector_a(angulo):
    """Vector a `angulo` radianes de la consulta: más ángulo, más lejos."""
    return [math.cos(angulo), math.sin(angulo)] + [0.0] * 1022


class BuscarSemanticoTests(TestCase):
    """Los vectores se arman a mano: acá se prueba el ranking, no el modelo."""

    def setUp(self):
        parche = patch(
            "catalogo.services.semantica.generar_vector", return_value=vector_a(0)
        )
        self.embeber = parche.start()
        self.addCleanup(parche.stop)
        parche = patch("catalogo.services.semantica.modelo_cargado", return_value=True)
        self.cargado = parche.start()
        self.addCleanup(parche.stop)
        parche = patch("catalogo.services.semantica.pedir_carga_del_modelo")
        self.pedir_carga = parche.start()
        self.addCleanup(parche.stop)
        self.proximo_id = 1

    def produccion(self, titulo, angulo, estado=EstadoEmbedding.READY, **campos):
        campos.setdefault("tipo", TipoProduccion.PELICULA)
        produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=self.proximo_id, titulo=titulo, **campos
        )
        self.proximo_id += 1
        ProduccionEmbedding.objects.create(
            produccion=produccion, vector=vector_a(angulo), estado=estado
        )
        return produccion

    def titulos(self, **filtros):
        return [p.titulo for p in buscar_semantico("algo", **filtros)]

    def test_devuelve_primero_lo_mas_cercano(self):
        self.produccion("Lejos", 1.0)
        self.produccion("Cerca", 0.1)
        self.produccion("Medio", 0.5)

        self.assertEqual(self.titulos(), ["Cerca", "Medio", "Lejos"])

    def test_la_consulta_usa_el_presupuesto_del_chat(self):
        buscar_semantico("viajes en el tiempo")

        self.embeber.assert_called_once_with(
            "viajes en el tiempo", timeout=3, reintentos=0
        )

    def test_si_el_modelo_no_esta_cargado_espera_la_carga(self):
        self.cargado.return_value = False

        buscar_semantico("algo")

        self.embeber.assert_called_once_with("algo", timeout=20, reintentos=0)

    def test_registra_cuanto_espero(self):
        self.cargado.return_value = False

        with self.assertLogs("catalogo.services.semantica", "INFO") as registro:
            buscar_semantico("algo")

        self.assertIn("cargado=False", registro.output[0])
        self.assertRegex(registro.output[0], r"vector_ms=\d+")

    def test_registra_cuanto_espero_tambien_si_falla(self):
        # Es el caso que más importa medir: la espera de 20 s que no alcanzó.
        self.cargado.return_value = False
        self.embeber.side_effect = EmbeddingProviderError("timeout")

        with (
            self.assertLogs("catalogo.services.semantica", "INFO") as registro,
            self.assertRaises(EmbeddingProviderError),
        ):
            buscar_semantico("algo")

        self.assertIn("cargado=False", registro.output[0])

    def test_ollama_que_no_responde_falla_sin_esperar_la_carga(self):
        self.cargado.side_effect = EmbeddingProviderError("colgado")

        with self.assertRaises(EmbeddingProviderError):
            buscar_semantico("algo")

        self.embeber.assert_not_called()

    def test_si_la_carga_no_llega_a_tiempo_sigue_en_segundo_plano(self):
        # Al cortar, Ollama abandona la carga: otra conexión tiene que seguirla.
        self.cargado.return_value = False
        self.embeber.side_effect = EmbeddingProviderError("timeout")

        with self.assertRaises(EmbeddingProviderError):
            buscar_semantico("algo")

        self.pedir_carga.assert_called_once()

    def test_un_fallo_con_el_modelo_cargado_no_pide_cargarlo(self):
        self.embeber.side_effect = EmbeddingProviderError("timeout")

        with self.assertRaises(EmbeddingProviderError):
            buscar_semantico("algo")

        self.pedir_carga.assert_not_called()

    def test_solo_considera_los_embeddings_ready(self):
        self.produccion("Lista", 0.5)
        # `failed` puede conservar el vector viejo: tenerlo no alcanza.
        self.produccion("Pendiente", 0.1, estado=EstadoEmbedding.PENDING)
        self.produccion("Fallida", 0.1, estado=EstadoEmbedding.FAILED)

        self.assertEqual(self.titulos(), ["Lista"])

    def test_filtra_por_genero_con_que_coincida_uno(self):
        self.produccion("About Time", 0.1, generos=["Romance", "Drama"])
        self.produccion("Paddington 2", 0.2, generos=["Family", "Comedy"])
        self.produccion("Moon", 0.3, generos=["Science Fiction"])

        self.assertEqual(self.titulos(generos=["Family"]), ["Paddington 2"])
        self.assertEqual(
            self.titulos(generos=["Family", "Drama"]), ["About Time", "Paddington 2"]
        )

    def test_filtra_por_tipo(self):
        self.produccion("Moon", 0.1, tipo=TipoProduccion.PELICULA)
        self.produccion("Dark", 0.2, tipo=TipoProduccion.SERIE)

        self.assertEqual(self.titulos(tipo="tv"), ["Dark"])

    def test_filtra_por_rango_de_anios(self):
        self.produccion("Vieja", 0.1, fecha_lanzamiento=date(1999, 12, 31))
        self.produccion("Justa", 0.2, fecha_lanzamiento=date(2000, 1, 1))
        self.produccion("Nueva", 0.3, fecha_lanzamiento=date(2011, 1, 1))

        self.assertEqual(self.titulos(anio_desde=2000, anio_hasta=2010), ["Justa"])

    def test_filtra_por_nota_minima(self):
        self.produccion("Mala", 0.1, calificacion_promedio=6.9)
        self.produccion("Buena", 0.2, calificacion_promedio=7.0)

        self.assertEqual(self.titulos(nota_minima=7), ["Buena"])

    def test_filtra_por_duracion_maxima_y_descarta_la_desconocida(self):
        self.produccion("Larga", 0.1, duracion=121)
        self.produccion("Corta", 0.2, duracion=120)
        self.produccion("Sin dato", 0.3, tipo=TipoProduccion.SERIE)

        self.assertEqual(self.titulos(duracion_max=120), ["Corta"])

    def test_basada_en_libro_deja_solo_los_titulos_con_esa_keyword(self):
        # C-04a guarda los keywords de TMDB como nombres en inglés.
        self.produccion("Original", 0.1, keywords=["space"])
        self.produccion("Adaptada", 0.2, keywords=["space", "based on novel or book"])
        self.produccion("Sin dato", 0.3)

        self.assertEqual(self.titulos(basada_en_libro=True), ["Adaptada"])
        self.assertEqual(
            self.titulos(basada_en_libro=False), ["Original", "Adaptada", "Sin dato"]
        )

    def test_excluye_por_id_y_tipo_no_solo_por_id(self):
        # Los ids de TMDB se repiten entre películas y series.
        moon = self.produccion("Moon", 0.1, tipo=TipoProduccion.PELICULA)
        serie = ProduccionAudiovisual.objects.create(
            id_tmdb=moon.id_tmdb, tipo=TipoProduccion.SERIE, titulo="Serie, mismo id"
        )
        ProduccionEmbedding.objects.create(
            produccion=serie, vector=vector_a(0.2), estado=EstadoEmbedding.READY
        )

        self.assertEqual(
            self.titulos(excluir={(moon.id_tmdb, "movie")}), ["Serie, mismo id"]
        )

    def test_devuelve_como_mucho_10(self):
        for i in range(12):
            self.produccion(f"T{i:02}", 0.01 * (i + 1))

        titulos = self.titulos()

        self.assertEqual(titulos, [f"T{i:02}" for i in range(10)])

    def test_los_filtros_corren_despues_de_elegir_los_50_mas_cercanos(self):
        for i in range(50):
            self.produccion(f"T{i:02}", 0.01 * (i + 1), generos=["Drama"])
        self.produccion("La 51", 1.0, generos=["Family"])

        self.assertEqual(self.titulos(generos=["Family"]), [])

    def test_con_el_indice_hnsw_tambien_llegan_50_candidatos(self):
        # Por defecto HNSW mira 40 candidatos: el puesto 46 quedaría afuera sin
        # avisar. Con pocas filas Postgres no usa el índice, así que se lo fuerza.
        for i in range(60):
            self.produccion(
                f"T{i:02}", 0.01 * (i + 1), generos=["Family" if i == 45 else "Drama"]
            )
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL enable_seqscan = off")
            cursor.execute("SET LOCAL enable_bitmapscan = off")
            cursor.execute("SET LOCAL enable_sort = off")

        self.assertEqual(self.titulos(generos=["Family"]), ["T45"])

    def test_si_ollama_falla_no_devuelve_nada_parcial(self):
        self.produccion("Moon", 0.1)
        self.embeber.side_effect = EmbeddingProviderError("caído")

        with self.assertRaises(EmbeddingProviderError):
            buscar_semantico("algo")


class RegistroDeLaMedicionTests(SimpleTestCase):
    def test_la_configuracion_real_deja_salir_la_medicion(self):
        # `assertLogs` arma su propio nivel y handler: sin esto, la medición podía
        # no salir nunca y los tests seguir pasando.
        registro = logging.getLogger("catalogo.services.semantica")

        self.assertTrue(registro.isEnabledFor(logging.INFO))
        self.assertTrue(registro.handlers)


class CalentarModeloTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_no_guarda_resultado(self):
        # Con resultado, un broker caído bloqueaba 19 s antes de fallar.
        self.assertTrue(calentar_modelo.ignore_result)

    def test_si_falla_libera_el_pedido_para_que_otro_la_reintente(self):
        cache.set(CLAVE_CARGA_MODELO, True, 60)

        with patch(
            "catalogo.tasks.generar_vector", side_effect=EmbeddingProviderError("x")
        ):
            calentar_modelo()

        self.assertIsNone(cache.get(CLAVE_CARGA_MODELO))

    def test_carga_el_modelo_sin_apuro(self):
        with patch("catalogo.tasks.generar_vector") as generar:
            calentar_modelo()

        generar.assert_called_once()
        self.assertEqual(generar.call_args.kwargs["timeout"], 60)
        self.assertEqual(generar.call_args.kwargs["reintentos"], 0)

    def test_si_ollama_falla_no_reintenta_en_loop(self):
        with patch(
            "catalogo.tasks.generar_vector", side_effect=EmbeddingProviderError("x")
        ):
            calentar_modelo()


class PedirCargaTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_encola_la_carga_con_vencimiento(self):
        # Sin worker, los pedidos viejos no deben acumularse ni correr horas después.
        with patch(
            "catalogo.services.semantica.calentar_modelo.apply_async"
        ) as encolar:
            pedir_carga_del_modelo()

        encolar.assert_called_once_with(expires=60)

    def test_el_intervalo_entre_cargas_es_un_minuto(self):
        with (
            patch("catalogo.services.semantica.cache.add", return_value=False) as add,
            patch("catalogo.services.semantica.calentar_modelo.apply_async"),
        ):
            pedir_carga_del_modelo()

        add.assert_called_once_with(CLAVE_CARGA_MODELO, True, 60)

    def test_abrir_el_panel_varias_veces_encola_una_sola(self):
        with patch(
            "catalogo.services.semantica.calentar_modelo.apply_async"
        ) as encolar:
            pedir_carga_del_modelo()
            pedir_carga_del_modelo()

        encolar.assert_called_once()

    def test_si_el_broker_falla_no_rompe_y_se_puede_reintentar(self):
        with patch(
            "catalogo.services.semantica.calentar_modelo.apply_async",
            side_effect=[ConnectionError("broker"), None],
        ) as encolar:
            pedir_carga_del_modelo()
            pedir_carga_del_modelo()

        self.assertEqual(encolar.call_count, 2)

    def test_si_la_cache_falla_no_rompe_y_no_encola(self):
        # En producción la caché es Redis: puede caerse igual que el broker.
        with (
            patch("catalogo.services.semantica.cache") as cache_caida,
            patch("catalogo.services.semantica.calentar_modelo.apply_async") as encolar,
            self.assertLogs("catalogo.services.semantica", "ERROR"),
        ):
            cache_caida.add.side_effect = ConnectionError("redis")
            pedir_carga_del_modelo()

        encolar.assert_not_called()

    def test_si_fallan_el_broker_y_despues_la_cache_no_rompe(self):
        with (
            patch("catalogo.services.semantica.cache") as cache_caida,
            patch(
                "catalogo.services.semantica.calentar_modelo.apply_async",
                side_effect=ConnectionError("broker"),
            ),
            self.assertLogs("catalogo.services.semantica", "ERROR"),
        ):
            cache_caida.add.return_value = True
            cache_caida.delete.side_effect = ConnectionError("redis")
            pedir_carga_del_modelo()

    def test_si_la_cache_falla_la_busqueda_conserva_el_error_de_ollama(self):
        # `tool_failed` depende de que el error de Ollama no se pierda.
        with (
            patch("catalogo.services.semantica.modelo_cargado", return_value=False),
            patch(
                "catalogo.services.semantica.generar_vector",
                side_effect=EmbeddingProviderError("timeout"),
            ),
            patch("catalogo.services.semantica.cache") as cache_caida,
            self.assertLogs("catalogo.services.semantica", "ERROR"),
        ):
            cache_caida.add.side_effect = ConnectionError("redis")
            with self.assertRaises(EmbeddingProviderError):
                buscar_semantico("algo")


class VencimientoDeProcessingTests(TestCase):
    """Q-09: una fila abandonada en `processing` se recupera; una en curso, no."""

    def setUp(self):
        self.produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=1, tipo=TipoProduccion.PELICULA, titulo="Moon"
        )
        ProduccionEmbedding.objects.create(
            produccion=self.produccion, estado=EstadoEmbedding.PROCESSING
        )
        parche = patch("catalogo.tasks.generar_vector", return_value=VECTOR)
        self.embeber = parche.start()
        self.addCleanup(parche.stop)

    def reclamada_hace(self, minutos):
        ProduccionEmbedding.objects.filter(produccion=self.produccion).update(
            fecha_actualizacion=timezone.now() - timedelta(minutes=minutos)
        )

    def estado(self):
        return ProduccionEmbedding.objects.get(produccion=self.produccion).estado

    def test_la_tarea_recupera_una_fila_vencida(self):
        self.reclamada_hace(6)

        generar_embedding(self.produccion.id)

        self.assertEqual(self.estado(), EstadoEmbedding.READY)

    def test_la_tarea_no_toca_una_fila_en_curso(self):
        self.reclamada_hace(4)

        generar_embedding(self.produccion.id)

        self.embeber.assert_not_called()
        self.assertEqual(self.estado(), EstadoEmbedding.PROCESSING)

    def test_reclamar_renueva_la_fecha_para_que_otro_no_la_tome_enseguida(self):
        self.reclamada_hace(6)
        fechas = []

        def medir(texto):
            fechas.append(
                ProduccionEmbedding.objects.get(
                    produccion=self.produccion
                ).fecha_actualizacion
            )
            return VECTOR

        self.embeber.side_effect = medir

        generar_embedding(self.produccion.id)

        self.assertGreater(fechas[0], timezone.now() - timedelta(minutes=1))

    def test_el_backfill_recupera_una_fila_vencida_con_la_tarea_real(self):
        # Con la tarea real: el backfill renueva la fecha al reencolar, y eso no
        # puede dejar a la tarea creyendo que la fila sigue en curso.
        self.reclamada_hace(6)

        with patch(
            "catalogo.tasks.generar_embedding.delay", side_effect=generar_embedding
        ):
            estadisticas = backfill_embeddings()

        self.assertEqual(estadisticas["reencolados"], 1)
        self.assertEqual(self.estado(), EstadoEmbedding.READY)

    def test_el_backfill_no_toca_una_fila_en_curso(self):
        self.reclamada_hace(4)

        with patch("catalogo.tasks.generar_embedding.delay") as encolar:
            estadisticas = backfill_embeddings()

        encolar.assert_not_called()
        self.assertEqual(estadisticas["reencolados"], 0)
        self.assertEqual(self.estado(), EstadoEmbedding.PROCESSING)
