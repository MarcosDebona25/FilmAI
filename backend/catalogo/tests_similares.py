"""Motor de «títulos parecidos» (`catalogo/services/similares.py`).

Diseño en `openspec/changes/recomendaciones-similares/design.md`. Los vectores
se arman a mano, como en `tests_semantica.py`: acá se prueba qué hace el motor
con los vectores (promediar, ordenar, excluir), no qué tan bueno es el modelo.
Ni Ollama ni TMDB se llaman de verdad.
"""

import json
import math
from dataclasses import asdict
from statistics import mean
from unittest.mock import patch

import fakeredis
import httpx
import numpy as np
from django.db import connection
from django.test import SimpleTestCase, TestCase

from catalogo.cache import TMDBClientCache
from catalogo.client import TMDBClient, crear_http_client
from catalogo.exceptions import TMDBNotFound, TMDBServerError
from catalogo.models import (
    EstadoEmbedding,
    ProduccionAudiovisual,
    ProduccionEmbedding,
    ProduccionTraduccion,
    TipoProduccion,
)
from catalogo.presupuesto import contar_llamadas
from catalogo.services.fallback import CatalogoConRespaldo
from catalogo.services.similares import (
    DISTANCIA_MAXIMA,
    MAX_LLAMADAS_TMDB,
    TAMANO_POOL,
    Pool,
    armar_pool,
    candidatos,
    cantidad_de_paginas,
    materializar_mostradas,
    mezclar_con_pesos,
    pagina,
    peso_del_nombre,
    relleno_tmdb,
    vector_semilla,
)

DIMENSIONES = 1024


def eje(indice):
    """Vector unitario sobre una sola dimensión: `eje(0)` y `eje(1)` son perpendiculares."""
    vector = [0.0] * DIMENSIONES
    vector[indice] = 1.0
    return vector


def vector_a(angulo):
    """Vector a `angulo` radianes de `eje(0)`: más ángulo, más lejos."""
    return [math.cos(angulo), math.sin(angulo)] + [0.0] * (DIMENSIONES - 2)


class BaseSimilares(TestCase):
    """Crea producciones con su vector. Por defecto pasan el piso de calidad (D-5)."""

    def setUp(self):
        self.proximo_id = 1

    def produccion(self, titulo, vector, estado=EstadoEmbedding.READY, **campos):
        campos.setdefault("tipo", TipoProduccion.PELICULA)
        campos.setdefault("poster", "/poster.jpg")
        campos.setdefault("calificacion_promedio", 7.0)
        produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=self.proximo_id, titulo=titulo, **campos
        )
        self.proximo_id += 1
        ProduccionEmbedding.objects.create(
            produccion=produccion, vector=vector, estado=estado
        )
        return produccion


class VectorSemillaTests(BaseSimilares):
    """El vector que representa a una lista: el promedio de los de sus títulos."""

    def test_promedia_los_vectores_y_normaliza_el_resultado(self):
        a = self.produccion("A", eje(0))
        b = self.produccion("B", eje(1))

        vector = vector_semilla([a.pk, b.pk])

        # El promedio de (1, 0) y (0, 1) es (0.5, 0.5): mide 0.707, no 1. Al
        # normalizarlo queda (0.707, 0.707), que sí mide 1.
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=5)
        self.assertAlmostEqual(float(vector[0]), math.sqrt(0.5), places=5)
        self.assertAlmostEqual(float(vector[1]), math.sqrt(0.5), places=5)

    def test_saltea_las_semillas_sin_vector_listo(self):
        lista = self.produccion("Lista", eje(0))
        pendiente = self.produccion("Pendiente", None, EstadoEmbedding.PENDING)

        vector = vector_semilla([lista.pk, pendiente.pk])

        self.assertAlmostEqual(float(vector[0]), 1.0, places=5)

    def test_sin_ninguna_semilla_con_vector_no_hay_vector(self):
        pendiente = self.produccion("Pendiente", None, EstadoEmbedding.PENDING)

        self.assertIsNone(vector_semilla([pendiente.pk]))
        self.assertIsNone(vector_semilla([]))
        # El nombre solo no alcanza: sin títulos no hay búsqueda local.
        self.assertIsNone(vector_semilla([pendiente.pk], vector_nombre=eje(1)))

    def test_el_peso_del_nombre_sigue_la_tabla_de_d1(self):
        esperado = {1: 0.50, 2: 0.33, 3: 0.25, 4: 0.20, 5: 0.17, 6: 0.15, 50: 0.15}

        for cantidad, peso in esperado.items():
            with self.subTest(titulos=cantidad):
                self.assertAlmostEqual(peso_del_nombre(cantidad), peso, places=2)

    def test_mezcla_el_nombre_con_el_peso_que_toca_segun_cuantos_titulos_hay(self):
        # Todos los títulos sobre el eje 0 y el nombre sobre el eje 1: en el
        # vector final, la proporción entre las dos coordenadas es w / (1 − w).
        ids = []
        for cantidad in range(1, 8):
            ids.append(self.produccion(f"T{cantidad}", eje(0)).pk)
            with self.subTest(titulos=cantidad):
                vector = vector_semilla(ids, vector_nombre=eje(1))

                peso = max(0.15, 1 / (cantidad + 1))
                self.assertAlmostEqual(
                    float(vector[1] / vector[0]), peso / (1 - peso), places=4
                )
                self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=5)

    def test_con_un_titulo_el_nombre_es_la_mitad_del_vector(self):
        titulo = self.produccion("Titanic", eje(0))

        vector = vector_semilla([titulo.pk], vector_nombre=eje(1))

        self.assertAlmostEqual(float(vector[0]), float(vector[1]), places=5)

    def test_el_nombre_se_normaliza_antes_de_mezclar(self):
        # Un vector de nombre «largo» no puede pesar más por medir más.
        titulo = self.produccion("Titanic", eje(0))
        largo = [valor * 10 for valor in eje(1)]

        vector = vector_semilla([titulo.pk], vector_nombre=largo)

        self.assertAlmostEqual(float(vector[0]), float(vector[1]), places=5)


class CandidatosTests(BaseSimilares):
    """Los vecinos más cercanos al vector semilla, con las semillas afuera."""

    def titulos(self, **opciones):
        opciones.setdefault("excluir_ids", [])
        encontrados = candidatos(vector_a(0), **opciones)
        por_pk = dict(ProduccionAudiovisual.objects.values_list("pk", "titulo"))
        return [por_pk[candidato.pk] for candidato in encontrados]

    def test_ordena_del_mas_cercano_al_mas_lejano_y_dice_la_distancia(self):
        self.produccion("Lejos", vector_a(1.0))
        self.produccion("Cerca", vector_a(0.1))
        self.produccion("Medio", vector_a(0.5))

        encontrados = candidatos(vector_a(0), excluir_ids=[])

        self.assertEqual(self.titulos(), ["Cerca", "Medio", "Lejos"])
        # Distancia coseno = 1 − coseno del ángulo entre los dos vectores.
        self.assertAlmostEqual(encontrados[0].distancia, 1 - math.cos(0.1), places=5)
        self.assertEqual(
            (encontrados[0].id_tmdb, encontrados[0].tipo), (2, TipoProduccion.PELICULA)
        )

    def test_las_semillas_quedan_afuera(self):
        semilla = self.produccion("Semilla", vector_a(0))
        self.produccion("Vecina", vector_a(0.1))

        self.assertEqual(self.titulos(excluir_ids=[semilla.pk]), ["Vecina"])

    def test_filtra_por_tipo(self):
        self.produccion("Película", vector_a(0.1))
        self.produccion("Serie", vector_a(0.2), tipo=TipoProduccion.SERIE)

        self.assertEqual(self.titulos(tipos=[TipoProduccion.SERIE]), ["Serie"])
        self.assertEqual(self.titulos(tipos=[TipoProduccion.PELICULA]), ["Película"])
        # Sin pedir tipo vienen los dos: el texto embebido no dice el tipo.
        self.assertEqual(self.titulos(), ["Película", "Serie"])

    def test_deja_afuera_lo_que_no_tiene_poster_o_nota(self):
        self.produccion("Completa", vector_a(0.3))
        self.produccion("Sin póster", vector_a(0.1), poster="")
        self.produccion("Sin nota", vector_a(0.1), calificacion_promedio=None)
        # TMDB manda 0 cuando nadie votó.
        self.produccion("Sin votos", vector_a(0.1), calificacion_promedio=0)

        self.assertEqual(self.titulos(), ["Completa"])

    def test_solo_cuentan_los_vectores_listos(self):
        self.produccion("Lista", vector_a(0.2))
        self.produccion("Fallida", vector_a(0.1), EstadoEmbedding.FAILED)

        self.assertEqual(self.titulos(), ["Lista"])

    def test_respeta_el_limite(self):
        for numero in range(5):
            self.produccion(f"T{numero}", vector_a(0.1 * numero))

        self.assertEqual(self.titulos(limite=2), ["T0", "T1"])

    def _muchas(self, cantidad):
        """`cantidad` producciones, cada una un poco más lejos que la anterior."""
        producciones = ProduccionAudiovisual.objects.bulk_create(
            ProduccionAudiovisual(
                id_tmdb=numero + 1,
                tipo=TipoProduccion.PELICULA,
                titulo=f"T{numero}",
                poster="/poster.jpg",
                calificacion_promedio=7.0,
            )
            for numero in range(cantidad)
        )
        ProduccionEmbedding.objects.bulk_create(
            ProduccionEmbedding(
                produccion=produccion,
                vector=vector_a(0.001 * numero),
                estado=EstadoEmbedding.READY,
            )
            for numero, produccion in enumerate(producciones)
        )
        return producciones

    def test_excluir_mil_vecinos_igual_devuelve_cien(self):
        """La trampa de HNSW con `WHERE` (design §4).

        El índice mira `ef_search` candidatos y recién después aplica el filtro:
        si los 1 000 más cercanos están excluidos, sin `iterative_scan` devuelve
        cero filas sin avisar.
        """
        producciones = self._muchas(1100)
        en_la_lista = [produccion.pk for produccion in producciones[:1000]]
        with connection.cursor() as cursor:
            # Con 1 100 filas Postgres prefiere recorrer la tabla entera, y ahí
            # el problema no aparece: esto lo obliga a usar el índice, como va a
            # pasar cuando el catálogo crezca.
            cursor.execute("SET LOCAL enable_seqscan = off")
            cursor.execute("SET LOCAL enable_sort = off")

        encontrados = candidatos(vector_a(0), excluir_ids=en_la_lista, limite=100)

        self.assertEqual(len(encontrados), 100)
        self.assertFalse({candidato.pk for candidato in encontrados} & set(en_la_lista))

    def test_la_consulta_corre_con_los_ajustes_del_indice(self):
        self.produccion("Una", vector_a(0.1))
        with connection.cursor() as cursor:
            cursor.execute("SHOW hnsw.iterative_scan")
            self.assertEqual(cursor.fetchone()[0], "off")

        candidatos(vector_a(0), excluir_ids=[])

        # `SET LOCAL` dura hasta el fin de la transacción, y cada test corre
        # dentro de una: por eso el valor todavía se puede leer acá.
        with connection.cursor() as cursor:
            cursor.execute("SHOW hnsw.iterative_scan")
            self.assertEqual(cursor.fetchone()[0], "relaxed_order")
            cursor.execute("SHOW hnsw.ef_search")
            self.assertEqual(cursor.fetchone()[0], "100")


def item_tmdb(id_tmdb, titulo=None, **campos):
    """Una película de `/recommendations` con lo que el motor lee."""
    return {
        "id": id_tmdb,
        "title": f"Película {id_tmdb}" if titulo is None else titulo,
        "poster_path": f"/{id_tmdb}.jpg",
        "release_date": "2014-11-05",
        "vote_average": 8.4,
        "vote_count": 500,
        "adult": False,
        **campos,
    }


def serie_tmdb(id_tmdb, titulo=None, **campos):
    """Una serie: TMDB usa `name` y `first_air_date` en vez de `title` y `release_date`."""
    return {
        "id": id_tmdb,
        "name": f"Serie {id_tmdb}" if titulo is None else titulo,
        "poster_path": f"/{id_tmdb}.jpg",
        "first_air_date": "2008-01-20",
        "vote_average": 8.9,
        "vote_count": 15000,
        **campos,
    }


class ServicioFalso:
    """Hace de `TMDBClientCache`: responde lo que se le cargó y anota qué se pidió."""

    def __init__(self, respuestas):
        self.respuestas = respuestas
        self.pedidos = []

    def get_recommendations(self, id_tmdb, tipo):
        self.pedidos.append((id_tmdb, tipo))
        respuesta = self.respuestas.get((id_tmdb, tipo), [])
        if isinstance(respuesta, Exception):
            raise respuesta
        return {"results": respuesta}


class RellenoTMDBTests(SimpleTestCase):
    """Lo que completa TMDB `/recommendations` cuando hay pocos vecinos locales."""

    def rellenar(self, respuestas, semillas, excluir=()):
        self.servicio = ServicioFalso(respuestas)
        return relleno_tmdb(semillas, servicio=self.servicio, excluir_pares=excluir)

    def test_arma_tarjetas_con_la_forma_de_un_item_de_lista(self):
        relleno = self.rellenar(
            {(27205, "movie"): [item_tmdb(157336, "Interstellar")]}, [(27205, "movie")]
        )

        self.assertEqual(
            relleno.tarjetas,
            [
                {
                    "id_tmdb": 157336,
                    "tipo": "movie",
                    "titulo": "Interstellar",
                    "poster": "/157336.jpg",
                    "anio": 2014,
                    "calificacion_promedio": 8.4,
                    "campos_en_ingles": [],
                    "origen": "tmdb",
                }
            ],
        )
        self.assertTrue(relleno.completo)

    def test_una_serie_usa_name_y_first_air_date(self):
        serie = serie_tmdb(1396, "Breaking Bad")

        tarjeta = self.rellenar({(60059, "tv"): [serie]}, [(60059, "tv")]).tarjetas[0]

        self.assertEqual(
            (tarjeta["tipo"], tarjeta["titulo"], tarjeta["anio"]),
            ("tv", "Breaking Bad", 2008),
        )

    def test_marca_el_titulo_que_quedo_en_ingles(self):
        # `CatalogoConRespaldo` anota en `campos_en_ingles` lo que completó.
        item = item_tmdb(1, "Moon", campos_en_ingles=["title", "overview"])

        tarjeta = self.rellenar({(9, "movie"): [item]}, [(9, "movie")]).tarjetas[0]

        self.assertEqual(tarjeta["campos_en_ingles"], ["titulo"])

    def test_usa_como_mucho_tres_semillas(self):
        semillas = [(numero, "movie") for numero in range(1, 6)]

        self.rellenar({}, semillas)

        self.assertEqual(self.servicio.pedidos, semillas[:3])

    def test_intercala_una_de_cada_semilla(self):
        respuestas = {
            (1, "movie"): [item_tmdb(11), item_tmdb(12), item_tmdb(13)],
            (2, "movie"): [item_tmdb(21)],
            (3, "tv"): [serie_tmdb(31), serie_tmdb(32)],
        }

        relleno = self.rellenar(respuestas, list(respuestas))

        # Una de cada semilla por vuelta: así una sola no se queda con todo.
        self.assertEqual(
            [(t["id_tmdb"], t["tipo"]) for t in relleno.tarjetas],
            [
                (11, "movie"),
                (21, "movie"),
                (31, "tv"),
                (12, "movie"),
                (32, "tv"),
                (13, "movie"),
            ],
        )

    def test_descarta_adulto_pocos_votos_y_sin_poster(self):
        respuestas = {
            (1, "movie"): [
                item_tmdb(10, adult=True),
                item_tmdb(11, vote_count=9),
                item_tmdb(12, poster_path=None),
                item_tmdb(13, poster_path=""),
                item_tmdb(14, vote_count=10),
            ]
        }

        relleno = self.rellenar(respuestas, [(1, "movie")])

        self.assertEqual([t["id_tmdb"] for t in relleno.tarjetas], [14])

    def test_descarta_las_semillas_lo_excluido_y_los_repetidos(self):
        respuestas = {
            (1, "movie"): [item_tmdb(2), item_tmdb(50), item_tmdb(60), item_tmdb(70)],
            (2, "movie"): [item_tmdb(1), item_tmdb(60), item_tmdb(80)],
        }

        relleno = self.rellenar(
            respuestas, [(1, "movie"), (2, "movie")], excluir={(50, "movie")}
        )

        # 1 y 2 son las semillas, 50 ya estaba (en la lista o entre los
        # candidatos locales) y 60 vino dos veces.
        self.assertEqual([t["id_tmdb"] for t in relleno.tarjetas], [60, 80, 70])

    def test_el_mismo_id_en_pelicula_y_en_serie_son_dos_titulos(self):
        respuestas = {(1, "tv"): [serie_tmdb(50)]}

        relleno = self.rellenar(respuestas, [(1, "tv")], excluir={(50, "movie")})

        self.assertEqual([t["id_tmdb"] for t in relleno.tarjetas], [50])

    def test_si_tmdb_falla_devuelve_lo_que_tenia_y_avisa_que_quedo_incompleto(self):
        respuestas = {
            (1, "movie"): [item_tmdb(11)],
            (2, "movie"): TMDBServerError("502"),
            (3, "movie"): [item_tmdb(31)],
        }

        relleno = self.rellenar(respuestas, list(respuestas))

        self.assertEqual([t["id_tmdb"] for t in relleno.tarjetas], [11])
        self.assertFalse(relleno.completo)
        # Con TMDB caído no se insiste con la semilla que falta.
        self.assertEqual(len(self.servicio.pedidos), 2)

    def test_una_semilla_que_tmdb_no_conoce_se_saltea(self):
        respuestas = {
            (1, "movie"): TMDBNotFound("404"),
            (2, "movie"): [item_tmdb(21)],
        }

        relleno = self.rellenar(respuestas, list(respuestas))

        self.assertEqual([t["id_tmdb"] for t in relleno.tarjetas], [21])
        self.assertTrue(relleno.completo)

    def test_sin_semillas_no_llama_a_tmdb(self):
        relleno = self.rellenar({}, [])

        self.assertEqual((relleno.tarjetas, self.servicio.pedidos), ([], []))


class PresupuestoDelRellenoTests(SimpleTestCase):
    """El relleno no puede costar más de 6 llamadas a TMDB por pedido.

    Acá el cliente de TMDB es el real y lo falso es la red (`MockTransport`):
    así cuenta el mismo contador que usa producción, reintentos incluidos.
    """

    def servicio(self, responder):
        self.urls = []

        def registrar(request):
            self.urls.append(str(request.url))
            return responder(request)

        http = crear_http_client(
            base_url="https://tmdb.test/3", transport=httpx.MockTransport(registrar)
        )
        redis = fakeredis.FakeRedis(decode_responses=True)
        return CatalogoConRespaldo(
            TMDBClientCache(TMDBClient(api_key="k", idioma="es-MX", http_client=http), redis),
            TMDBClientCache(TMDBClient(api_key="k", http_client=http), redis),
        )

    def test_tres_semillas_con_respaldo_en_ingles_son_seis_llamadas(self):
        def responder(request):
            # En español el título llega vacío: obliga a pedir la página en inglés.
            titulo = "" if request.url.params["language"] == "es-MX" else "Moon"
            return httpx.Response(200, json={"results": [item_tmdb(17431, titulo)]})

        servicio = self.servicio(responder)
        with contar_llamadas() as contador:
            relleno = relleno_tmdb(
                [(1, "movie"), (2, "movie"), (3, "movie"), (4, "movie")],
                servicio=servicio,
                excluir_pares=(),
            )

        self.assertEqual(contador.total, 6)
        self.assertEqual(MAX_LLAMADAS_TMDB, 6)
        self.assertEqual(relleno.tarjetas[0]["titulo"], "Moon")
        self.assertEqual(relleno.tarjetas[0]["campos_en_ingles"], ["titulo"])

    @patch("catalogo.client.time.sleep")
    def test_los_reintentos_tambien_cuentan_y_nunca_pasan_de_seis(self, _dormir):
        intentos = iter(range(100))

        def responder(request):
            # Falla una de cada dos: cada llamada cuesta dos pedidos HTTP.
            if next(intentos) % 2 == 0:
                return httpx.Response(503, json={})
            titulo = "" if request.url.params["language"] == "es-MX" else "Moon"
            return httpx.Response(200, json={"results": [item_tmdb(17431, titulo)]})

        servicio = self.servicio(responder)
        with contar_llamadas() as contador:
            relleno = relleno_tmdb(
                [(1, "movie"), (2, "movie"), (3, "movie")],
                servicio=servicio,
                excluir_pares=(),
            )

        self.assertEqual(len(self.urls), 6)
        # El intento 7 se corta antes de salir a la red, pero queda contado.
        self.assertLessEqual(contador.total, 7)
        self.assertFalse(relleno.completo)

    def test_el_tope_del_relleno_no_le_quita_presupuesto_al_resto_del_pedido(self):
        servicio = self.servicio(
            lambda request: httpx.Response(200, json={"results": []})
        )
        with contar_llamadas() as contador:
            relleno_tmdb([(1, "movie")], servicio=servicio, excluir_pares=())
            # Después del relleno, el pedido vuelve a su tope de siempre (30).
            for id_tmdb in range(10, 20):
                servicio.get_recommendations(id_tmdb, "movie")

        self.assertEqual(contador.total, 11)


# Ángulos a un lado y al otro del umbral: distancia coseno = 1 − cos(ángulo).
CERCA = 0.5  # distancia 0.12
LEJOS = 1.2  # distancia 0.64


class MezclaConPesosTests(SimpleTestCase):
    """La mezcla del pool: al azar, pero favoreciendo a los más cercanos."""

    def test_la_misma_semilla_da_el_mismo_orden(self):
        entradas = list(range(60))

        self.assertEqual(
            mezclar_con_pesos(entradas, "firma-a"),
            mezclar_con_pesos(entradas, "firma-a"),
        )

    def test_otra_semilla_da_otro_orden_con_los_mismos_elementos(self):
        entradas = list(range(60))

        una = mezclar_con_pesos(entradas, "firma-a")
        otra = mezclar_con_pesos(entradas, "firma-b")

        self.assertNotEqual(una, otra)
        self.assertEqual(sorted(una), entradas)
        self.assertEqual(sorted(otra), entradas)

    def test_la_primera_pagina_trae_sobre_todo_a_los_mas_cercanos(self):
        # Cada entrada es su puesto por distancia (0 = el más cercano). Al azar
        # puro, el promedio de cualquier página sería 29.5. Se promedian 200
        # mezclas para que el test no dependa de la suerte de una sola.
        entradas = list(range(60))
        mezclas = [mezclar_con_pesos(entradas, f"firma-{n}") for n in range(200)]

        primera = mean(mean(mezcla[:10]) for mezcla in mezclas)
        ultima = mean(mean(mezcla[-10:]) for mezcla in mezclas)

        self.assertLess(primera, 25)
        self.assertGreater(ultima, 34)

    def test_no_es_el_orden_exacto_por_distancia(self):
        entradas = list(range(60))

        self.assertNotEqual(mezclar_con_pesos(entradas, "firma-a")[:10], entradas[:10])


class ArmarPoolTests(BaseSimilares):
    """De las semillas al pool: locales cercanos, relleno de TMDB y locales lejanos."""

    def armar(self, semillas, respuestas=None, **opciones):
        self.servicio = ServicioFalso(respuestas or {})
        opciones.setdefault("semillas_tmdb", [(s.id_tmdb, "movie") for s in semillas])
        opciones.setdefault("semilla_azar", "firma")
        return armar_pool(
            [semilla.pk for semilla in semillas], servicio=self.servicio, **opciones
        )

    def sin_mezclar(self):
        """Deja el pool en el orden en que se armó, para poder mirarlo."""
        parche = patch(
            "catalogo.services.similares.mezclar_con_pesos",
            side_effect=lambda entradas, semilla: entradas,
        )
        parche.start()
        self.addCleanup(parche.stop)

    def test_el_umbral_de_cercania_es_el_del_diseno(self):
        self.assertEqual(DISTANCIA_MAXIMA, 0.40)
        self.assertEqual(TAMANO_POOL, 60)

    def test_con_veinte_cercanos_no_se_llama_a_tmdb(self):
        semilla = self.produccion("Semilla", vector_a(0))
        for numero in range(20):
            self.produccion(f"C{numero}", vector_a(0.01 * numero))

        pool = self.armar([semilla])

        self.assertEqual(self.servicio.pedidos, [])
        self.assertEqual((pool.cercanos, pool.de_tmdb, len(pool.entradas)), (20, 0, 20))
        self.assertTrue(pool.completo)

    def test_con_menos_de_veinte_cercanos_tmdb_completa_en_el_medio(self):
        self.sin_mezclar()
        semilla = self.produccion("Semilla", vector_a(0))
        cerca = self.produccion("Cerca", vector_a(CERCA))
        lejos = self.produccion("Lejos", vector_a(LEJOS))

        pool = self.armar(
            [semilla], {(semilla.id_tmdb, "movie"): [item_tmdb(900), item_tmdb(901)]}
        )

        # Primero lo local cercano, después TMDB, al final lo local lejano.
        self.assertEqual(
            [(e["origen"], e["id_tmdb"]) for e in pool.entradas],
            [
                ("catalogo", cerca.id_tmdb),
                ("tmdb", 900),
                ("tmdb", 901),
                ("catalogo", lejos.id_tmdb),
            ],
        )
        self.assertEqual((pool.cercanos, pool.de_tmdb), (1, 2))
        self.assertTrue(pool.completo)

    def test_tmdb_no_repite_lo_que_ya_vino_del_catalogo_ni_las_semillas(self):
        semilla = self.produccion("Semilla", vector_a(0))
        otra_semilla = self.produccion("Otra", vector_a(0.1))
        cerca = self.produccion("Cerca", vector_a(CERCA))
        lejos = self.produccion("Lejos", vector_a(LEJOS))
        respuestas = {
            (semilla.id_tmdb, "movie"): [
                item_tmdb(cerca.id_tmdb),
                item_tmdb(lejos.id_tmdb),
                item_tmdb(otra_semilla.id_tmdb),
                item_tmdb(900),
            ]
        }

        pool = self.armar(
            [semilla, otra_semilla],
            respuestas,
            semillas_tmdb=[(semilla.id_tmdb, "movie")],
        )

        self.assertEqual(
            [e["id_tmdb"] for e in pool.entradas if e["origen"] == "tmdb"], [900]
        )

    def test_el_pool_tiene_sesenta_como_mucho(self):
        semilla = self.produccion("Semilla", vector_a(0))
        for numero in range(70):
            self.produccion(f"C{numero}", vector_a(0.001 * numero))

        self.assertEqual(len(self.armar([semilla]).entradas), 60)

    def test_el_orden_depende_solo_de_la_semilla_de_azar(self):
        semilla = self.produccion("Semilla", vector_a(0))
        for numero in range(30):
            self.produccion(f"C{numero}", vector_a(0.01 * numero))

        una = self.armar([semilla], semilla_azar="a").entradas
        igual = self.armar([semilla], semilla_azar="a").entradas
        otra = self.armar([semilla], semilla_azar="b").entradas

        self.assertEqual(una, igual)
        self.assertNotEqual(una, otra)

    def test_una_semilla_sin_vector_deja_el_pool_incompleto(self):
        lista = self.produccion("Lista", vector_a(0))
        pendiente = self.produccion("Pendiente", None, EstadoEmbedding.PENDING)
        for numero in range(20):
            self.produccion(f"C{numero}", vector_a(0.01 * numero))

        pool = self.armar([lista, pendiente])

        # Cuando su vector esté listo la firma no cambia: por eso dura poco.
        self.assertFalse(pool.completo)
        self.assertEqual(pool.semillas_con_vector, 1)
        self.assertEqual(len(pool.entradas), 20)

    def test_sin_ninguna_semilla_con_vector_el_pool_es_solo_de_tmdb(self):
        pendiente = self.produccion("Pendiente", None, EstadoEmbedding.PENDING)
        self.produccion("Vecina", vector_a(0.1))

        pool = self.armar([pendiente], {(pendiente.id_tmdb, "movie"): [item_tmdb(900)]})

        self.assertEqual([e["origen"] for e in pool.entradas], ["tmdb"])
        self.assertFalse(pool.completo)

    def test_un_titulo_que_no_esta_en_el_catalogo_se_arma_solo_con_tmdb(self):
        pool = self.armar(
            [],
            {(27205, "movie"): [item_tmdb(900)]},
            semillas_tmdb=[(27205, "movie")],
        )

        self.assertEqual([e["id_tmdb"] for e in pool.entradas], [900])
        self.assertFalse(pool.completo)

    def test_si_tmdb_falla_queda_lo_local_y_el_pool_incompleto(self):
        semilla = self.produccion("Semilla", vector_a(0))
        cerca = self.produccion("Cerca", vector_a(CERCA))

        pool = self.armar([semilla], {(semilla.id_tmdb, "movie"): TMDBServerError("x")})

        self.assertEqual([e["id_tmdb"] for e in pool.entradas], [cerca.id_tmdb])
        self.assertFalse(pool.completo)

    def test_filtra_los_candidatos_por_tipo(self):
        semilla = self.produccion("Semilla", vector_a(0), tipo=TipoProduccion.SERIE)
        self.produccion("Película", vector_a(0.1))
        serie = self.produccion("Serie", vector_a(0.2), tipo=TipoProduccion.SERIE)

        pool = self.armar([semilla], tipos=[TipoProduccion.SERIE], semillas_tmdb=[])

        self.assertEqual(
            [(e["id_tmdb"], e["tipo"]) for e in pool.entradas], [(serie.id_tmdb, "tv")]
        )

    def test_el_nombre_inclina_el_vector_y_queda_anotado(self):
        self.sin_mezclar()
        semilla = self.produccion("Semilla", vector_a(0))
        del_tema = self.produccion("Del tema", vector_a(1.0))
        del_otro_lado = self.produccion("Del otro lado", vector_a(-0.9))

        sin_nombre = self.armar([semilla], semillas_tmdb=[])
        con_nombre = self.armar(
            [semilla], semillas_tmdb=[], vector_nombre=vector_a(1.0)
        )

        self.assertFalse(sin_nombre.nombre_usado)
        self.assertEqual(sin_nombre.entradas[0]["id_tmdb"], del_otro_lado.id_tmdb)
        self.assertTrue(con_nombre.nombre_usado)
        self.assertEqual(con_nombre.entradas[0]["id_tmdb"], del_tema.id_tmdb)

    def test_un_nombre_que_no_se_pudo_embeber_deja_el_pool_incompleto(self):
        semilla = self.produccion("Semilla", vector_a(0))
        for numero in range(20):
            self.produccion(f"C{numero}", vector_a(0.01 * numero))

        pool = self.armar([semilla], nombre_omitido=True)

        self.assertFalse(pool.nombre_usado)
        self.assertFalse(pool.completo)

    def test_el_pool_se_puede_guardar_como_json(self):
        # La caché de Redis del proyecto serializa con JSON (`filmai/cache.py`).
        semilla = self.produccion("Semilla", vector_a(0))
        self.produccion("Cerca", vector_a(CERCA))
        pool = self.armar([semilla], {(semilla.id_tmdb, "movie"): [item_tmdb(900)]})

        ida_y_vuelta = Pool(**json.loads(json.dumps(asdict(pool))))

        self.assertEqual(ida_y_vuelta, pool)


class PaginaTests(BaseSimilares):
    """Cada página es un corte del pool, sin lo que el usuario ya vio."""

    def pool(self, cantidad, tmdb=()):
        self.producciones = [
            self.produccion(
                f"T{numero}", vector_a(0), fecha_lanzamiento="2010-07-16"
            )
            for numero in range(cantidad)
        ]
        entradas = [
            {
                "origen": "catalogo",
                "pk": p.pk,
                "id_tmdb": p.id_tmdb,
                "tipo": "movie",
            }
            for p in self.producciones
        ]
        return Pool(
            entradas=[*entradas, *tmdb],
            nombre_usado=False,
            completo=True,
            semillas_con_vector=1,
            cercanos=cantidad,
            de_tmdb=len(tmdb),
        )

    def test_una_tarjeta_local_tiene_la_forma_de_un_item_de_lista(self):
        pool = self.pool(1)

        self.assertEqual(
            pagina(pool),
            [
                {
                    "id_tmdb": self.producciones[0].id_tmdb,
                    "tipo": "movie",
                    "titulo": "T0",
                    "poster": "/poster.jpg",
                    "anio": 2010,
                    "calificacion_promedio": 7.0,
                    "campos_en_ingles": [],
                    "origen": "catalogo",
                }
            ],
        )

    def test_corta_de_a_diez_y_respeta_el_orden_del_pool(self):
        pool = self.pool(25)

        self.assertEqual(
            [t["titulo"] for t in pagina(pool, numero=1)],
            [f"T{n}" for n in range(10)],
        )
        self.assertEqual(
            [t["titulo"] for t in pagina(pool, numero=3)],
            [f"T{n}" for n in range(20, 25)],
        )
        self.assertEqual(cantidad_de_paginas(pool), 3)

    def test_pasada_la_ultima_pagina_no_hay_resultados(self):
        self.assertEqual(pagina(self.pool(5), numero=2), [])

    def test_el_tamano_de_la_pagina_se_puede_pedir(self):
        self.assertEqual(len(pagina(self.pool(25), tamano=20)), 20)

    def test_saca_lo_excluido_antes_de_cortar(self):
        pool = self.pool(12)
        vistas = {(self.producciones[0].id_tmdb, "movie")}

        primera = pagina(pool, excluir_pares=vistas)

        # La página sigue teniendo 10: el lugar de la vista lo ocupa la siguiente.
        self.assertEqual([t["titulo"] for t in primera], [f"T{n}" for n in range(1, 11)])
        self.assertEqual(cantidad_de_paginas(pool, excluir_pares=vistas), 2)
        self.assertEqual(
            [t["titulo"] for t in pagina(pool, excluir_pares=vistas, numero=2)], ["T11"]
        )

    def test_las_tarjetas_de_tmdb_van_como_llegaron_y_tambien_se_excluyen(self):
        tarjeta = {
            "id_tmdb": 900,
            "tipo": "tv",
            "titulo": "De TMDB",
            "poster": "/900.jpg",
            "anio": 2020,
            "calificacion_promedio": 8.0,
            "campos_en_ingles": [],
            "origen": "tmdb",
        }
        pool = self.pool(1, tmdb=[tarjeta])

        self.assertEqual(pagina(pool)[1], tarjeta)
        self.assertEqual(len(pagina(pool, excluir_pares={(900, "tv")})), 1)
        # El mismo id en película es otro título: no la saca.
        self.assertEqual(len(pagina(pool, excluir_pares={(900, "movie")})), 2)

    def test_localiza_el_titulo_y_marca_lo_que_quedo_en_ingles(self):
        pool = self.pool(2)
        ProduccionTraduccion.objects.create(
            produccion=self.producciones[0], idioma="es", titulo="El origen"
        )

        en_espanol = pagina(pool, idioma="es")

        self.assertEqual(en_espanol[0]["titulo"], "El origen")
        # Sin póster traducido, el póster es el canónico (en inglés).
        self.assertEqual(en_espanol[0]["campos_en_ingles"], ["poster"])
        self.assertEqual(en_espanol[1]["titulo"], "T1")
        self.assertEqual(en_espanol[1]["campos_en_ingles"], ["titulo", "poster"])

    def test_no_hace_una_consulta_por_tarjeta(self):
        pool = self.pool(10)

        # Una para las producciones y otra para sus traducciones.
        with self.assertNumQueries(2):
            pagina(pool, idioma="es")

    def test_una_produccion_borrada_despues_de_armar_el_pool_se_saltea(self):
        pool = self.pool(3)
        self.producciones[1].delete()

        self.assertEqual([t["titulo"] for t in pagina(pool)], ["T0", "T2"])


class MaterializarMostradasTests(SimpleTestCase):
    """Lo que TMDB aportó y se mostró entra al catálogo, para la próxima vez."""

    TARJETAS = (
        {"id_tmdb": 1, "tipo": "movie", "origen": "catalogo"},
        {"id_tmdb": 900, "tipo": "tv", "origen": "tmdb"},
    )

    @patch("catalogo.services.similares.materializar_listado_en_segundo_plano")
    def test_encola_solo_las_tarjetas_de_tmdb(self, encolar):
        materializar_mostradas(self.TARJETAS)

        encolar.assert_called_once_with([{"id": 900, "media_type": "tv"}])

    @patch("catalogo.services.similares.materializar_listado_en_segundo_plano")
    def test_sin_tarjetas_de_tmdb_no_encola_nada(self, encolar):
        materializar_mostradas(self.TARJETAS[:1])

        encolar.assert_not_called()

    @patch(
        "catalogo.services.similares.materializar_listado_en_segundo_plano",
        side_effect=RuntimeError("broker caído"),
    )
    def test_si_no_se_puede_encolar_la_respuesta_sigue(self, _encolar):
        with self.assertLogs("catalogo.services.similares", "ERROR"):
            materializar_mostradas(self.TARJETAS)
