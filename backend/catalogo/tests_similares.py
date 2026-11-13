"""Motor de «títulos parecidos» (`catalogo/services/similares.py`).

Diseño en `openspec/changes/recomendaciones-similares/design.md`. Los vectores
se arman a mano, como en `tests_semantica.py`: acá se prueba qué hace el motor
con los vectores (promediar, ordenar, excluir), no qué tan bueno es el modelo.
Ni Ollama ni TMDB se llaman de verdad.
"""

import math

import numpy as np
from django.db import connection
from django.test import TestCase

from catalogo.models import (
    EstadoEmbedding,
    ProduccionAudiovisual,
    ProduccionEmbedding,
    TipoProduccion,
)
from catalogo.services.similares import candidatos, peso_del_nombre, vector_semilla

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
