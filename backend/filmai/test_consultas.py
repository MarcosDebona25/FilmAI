"""Cantidad de queries por endpoint: no crece con la cantidad de filas (N+1).

Cada caso arma el mismo escenario con una fila y con varias, y exige la misma
cantidad de queries. Si alguien quita un `select_related`/`prefetch_related`
o agrega un campo que consulta por fila, la cuenta de «varias» crece y el test
falla nombrando el endpoint (medición del 22/10/2026, ver docs/decisiones.md).
"""

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from catalogo.factories import ProduccionAudiovisualFactory
from catalogo.models import Calificacion, ProduccionTraduccion, Resena, TipoProduccion
from listas.models import Tiene
from usuarios.factories import UsuarioFactory

POCAS, MUCHAS = 1, 8


class QueriesNoCrecenConLasFilasTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        # Con `es` las vistas también buscan la traducción de cada producción.
        self.cliente = APIClient(HTTP_ACCEPT_LANGUAGE="es")
        self.cliente.force_authenticate(self.usuario)
        self.vistas = self.usuario.listas.get(nombre="Vistas")
        self.siguiente_id = 1000

    def _produccion(self):
        self.siguiente_id += 1
        produccion = ProduccionAudiovisualFactory(
            id_tmdb=self.siguiente_id, tipo=TipoProduccion.PELICULA
        )
        ProduccionTraduccion.objects.create(
            produccion=produccion, idioma="es", titulo=f"Título {self.siguiente_id}"
        )
        return produccion

    def _contar(self, url):
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.cliente.get(url)
        self.assertEqual(respuesta.status_code, 200, url)
        return len(consultas)

    def _comparar(self, armar, url):
        """Arma `POCAS` filas, cuenta, completa hasta `MUCHAS` y vuelve a contar."""
        armar(POCAS)
        pocas = self._contar(url)
        armar(MUCHAS - POCAS)
        self.assertEqual(self._contar(url), pocas, f"{url} crece con las filas")

    def test_listas_del_usuario(self):
        def armar(cantidad):
            for _ in range(cantidad):
                Tiene.objects.create(lista=self.vistas, produccion=self._produccion())

        self._comparar(armar, "/api/lists/")

    def test_items_de_una_lista(self):
        def armar(cantidad):
            for _ in range(cantidad):
                Tiene.objects.create(lista=self.vistas, produccion=self._produccion())

        self._comparar(armar, f"/api/lists/{self.vistas.pk}/items/")

    def test_mis_resenas(self):
        def armar(cantidad):
            for _ in range(cantidad):
                calificacion = Calificacion.objects.create(
                    usuario=self.usuario, produccion=self._produccion(), valor=8
                )
                Resena.objects.create(calificacion=calificacion, texto="Buena.")

        self._comparar(armar, "/api/reviews/mias/")

    def test_resenas_de_la_comunidad(self):
        produccion = self._produccion()

        def armar(cantidad):
            for _ in range(cantidad):
                calificacion = Calificacion.objects.create(
                    usuario=UsuarioFactory(), produccion=produccion, valor=7
                )
                Resena.objects.create(calificacion=calificacion, texto="Correcta.")

        self._comparar(armar, f"/api/reviews/?id_tmdb={produccion.id_tmdb}&tipo=movie")
