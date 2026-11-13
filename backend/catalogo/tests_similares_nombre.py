"""El nombre de la lista en las sugerencias: cuándo «dice algo» y cómo se embebe.

Diseño en `openspec/changes/recomendaciones-similares/design.md` §3 (D-2 y
D-9). Ollama nunca se llama de verdad: `httpx.MockTransport` reemplaza la red y
deja ver qué pedidos salieron, como en `tests_semantica.py`.
"""

import json
from unittest.mock import patch

import httpx
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from catalogo.services import similares
from catalogo.services.similares import (
    CLAVE_OLLAMA_NO,
    nombre_dice_algo,
    normalizar_nombre,
    vector_del_nombre,
)

VECTOR = [0.1] * 1024


class NombreDiceAlgoTests(SimpleTestCase):
    """D-2: una regla fija, que se puede probar sin Ollama."""

    def test_un_nombre_generico_no_dice_nada(self):
        for nombre in (
            "Lista 3",
            "My list",
            "Nueva lista",
            "Mis películas",
            "MIS PELIS",
            "Series 2024",
            "Para ver",
            "Cosas varios",
            "TV",
            "A1 b2",
            "2024",
        ):
            with self.subTest(nombre=nombre):
                self.assertFalse(nombre_dice_algo(nombre))

    def test_un_nombre_con_tema_si(self):
        for nombre in (
            "Sci Fi",
            "Pelis para llorar",
            "Domingo de lluvia",
            "Terror",
            "Películas de terror",
            "Lista de Nolan",
            "Anime 2024",
        ):
            with self.subTest(nombre=nombre):
                self.assertTrue(nombre_dice_algo(nombre))

    def test_hace_falta_una_palabra_de_tres_letras_o_mas(self):
        self.assertFalse(nombre_dice_algo("Mi tv de él"))
        self.assertTrue(nombre_dice_algo("Mi tv del mar"))

    def test_normalizar_saca_mayusculas_tildes_y_espacios_de_mas(self):
        self.assertEqual(
            normalizar_nombre("  Películas   de TERROR "), "peliculas de terror"
        )
        self.assertEqual(normalizar_nombre("Sci Fi"), normalizar_nombre("SCI  fi"))


@override_settings(OLLAMA_URL="http://ollama.test:11434", OLLAMA_KEEP_ALIVE="30m")
class VectorDelNombreTests(SimpleTestCase):
    """D-9: el nombre nunca hace esperar a quien mira su lista."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        parche = patch("catalogo.services.similares.pedir_carga_del_modelo")
        self.pedir_carga = parche.start()
        self.addCleanup(parche.stop)
        self.pedidos = []
        # Lo que responde el Ollama falso; cada test cambia lo que necesita.
        self.modelos = [{"name": "bge-m3:latest"}]
        self.estado = lambda: httpx.Response(200, json={"models": self.modelos})
        self.embeber = lambda: httpx.Response(200, json={"embeddings": [VECTOR]})

    def responder(self, request):
        self.pedidos.append(request)
        return self.estado() if request.url.path == "/api/ps" else self.embeber()

    def pedir(self, nombre):
        return vector_del_nombre(nombre, transport=httpx.MockTransport(self.responder))

    def rutas(self):
        return [pedido.url.path for pedido in self.pedidos]

    def test_con_el_modelo_cargado_embebe_el_nombre_tal_como_se_escribio(self):
        vector = self.pedir("  Pelis para llorar ")

        self.assertEqual(vector, VECTOR)
        self.assertEqual(self.rutas(), ["/api/ps", "/api/embed"])
        # Sin etiqueta ni prefijo, y recortado: bge-m3 no los necesita.
        self.assertEqual(
            json.loads(self.pedidos[1].content)["input"], "Pelis para llorar"
        )
        self.pedir_carga.assert_not_called()

    def test_usa_el_presupuesto_del_chat_tres_segundos_y_sin_reintentos(self):
        self.embeber = lambda: httpx.Response(500)

        self.assertIsNone(self.pedir("Terror"))

        embeds = [p for p in self.pedidos if p.url.path == "/api/embed"]
        self.assertEqual(len(embeds), 1)
        self.assertEqual(embeds[0].extensions["timeout"]["read"], 3)

    def test_el_vector_queda_guardado_por_nombre_normalizado(self):
        self.pedir("Sci Fi")
        self.pedidos.clear()

        # Otro usuario, la misma idea escrita distinto: no se llega a Ollama.
        self.assertEqual(self.pedir("SCI  fi"), VECTOR)
        self.assertEqual(self.pedidos, [])

    def test_el_vector_se_guarda_30_dias_con_el_modelo_en_la_clave(self):
        with patch.object(similares.cache, "set", wraps=similares.cache.set) as guardar:
            self.pedir("Sci Fi")

        (clave, valor, ttl), _ = guardar.call_args
        self.assertRegex(clave, r"^similares:nombre:bge-m3:[0-9a-f]{64}$")
        self.assertEqual((valor, ttl), (VECTOR, 30 * 24 * 3600))

    def test_con_el_modelo_sin_cargar_saltea_el_nombre_y_pide_la_carga(self):
        self.modelos = []

        self.assertIsNone(self.pedir("Terror"))

        # No espera la carga (hasta 20 s en frío): ni intenta embeber.
        self.assertEqual(self.rutas(), ["/api/ps"])
        self.pedir_carga.assert_called_once_with()
        # Ollama responde: no hace falta recordar ninguna caída.
        self.assertIsNone(cache.get(CLAVE_OLLAMA_NO))

    def test_si_ollama_no_responde_lo_recuerda_60_segundos(self):
        def caido():
            raise httpx.ConnectError("sin conexión")

        self.estado = caido

        with patch.object(similares.cache, "set", wraps=similares.cache.set) as guardar:
            self.assertIsNone(self.pedir("Terror"))

        guardar.assert_called_once_with(CLAVE_OLLAMA_NO, True, 60)
        self.pedir_carga.assert_called_once_with()
        self.pedidos.clear()

        # El segundo pedido ni lo intenta: un Ollama caído cuesta 1 s por
        # minuto, no 1 s por pedido.
        self.assertIsNone(self.pedir("Otro nombre"))
        self.assertEqual(self.pedidos, [])

    def test_si_falla_al_embeber_tambien_lo_recuerda(self):
        self.embeber = lambda: httpx.Response(500)

        self.assertIsNone(self.pedir("Terror"))

        self.assertTrue(cache.get(CLAVE_OLLAMA_NO))

    def test_un_fallo_no_deja_un_vector_guardado(self):
        self.embeber = lambda: httpx.Response(500)
        self.pedir("Terror")
        cache.delete(CLAVE_OLLAMA_NO)
        self.embeber = lambda: httpx.Response(200, json={"embeddings": [VECTOR]})

        self.assertEqual(self.pedir("Terror"), VECTOR)

    def test_con_el_vector_guardado_no_importa_que_ollama_este_caido(self):
        self.pedir("Terror")
        cache.set(CLAVE_OLLAMA_NO, True, 60)
        self.pedidos.clear()

        self.assertEqual(self.pedir("terror"), VECTOR)
        self.assertEqual(self.pedidos, [])
