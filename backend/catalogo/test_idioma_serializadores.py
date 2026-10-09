"""OT-63: listas, reseñas y géneros responden en el idioma efectivo."""

from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.factories import CalificacionFactory, ProduccionAudiovisualFactory
from catalogo.models import ProduccionTraduccion
from listas.models import ClaveLista, Tiene
from usuarios.factories import UsuarioFactory


class TitulosPorIdiomaTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory(idioma=None)
        self.traducida = ProduccionAudiovisualFactory(
            titulo="Fight Club", poster="/en.jpg"
        )
        ProduccionTraduccion.objects.create(
            produccion=self.traducida,
            idioma="es",
            titulo="El club de la pelea",
            poster="/es.jpg",
        )
        self.sin_traducir = ProduccionAudiovisualFactory(titulo="Cure", poster="/c.jpg")
        self.lista = self.usuario.listas.get(clave=ClaveLista.FAVORITOS)
        for produccion in (self.traducida, self.sin_traducir):
            Tiene.objects.create(lista=self.lista, produccion=produccion)
            CalificacionFactory(usuario=self.usuario, produccion=produccion)
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)

    def _titulos(self, url, idioma):
        datos = self.cliente.get(url, HTTP_ACCEPT_LANGUAGE=idioma).json()
        return {(item["titulo"], item["poster"]) for item in datos["results"]}

    def test_items_de_lista_respetan_el_idioma_con_respaldo_canonico(self):
        url = f"/api/lists/{self.lista.pk}/items/"
        self.assertEqual(
            self._titulos(url, "es"),
            {("El club de la pelea", "/es.jpg"), ("Cure", "/c.jpg")},
        )
        self.assertEqual(
            self._titulos(url, "en"), {("Fight Club", "/en.jpg"), ("Cure", "/c.jpg")}
        )

    def test_mis_resenas_respetan_el_idioma(self):
        self.assertEqual(
            self._titulos("/api/reviews/mias/", "es"),
            {("El club de la pelea", "/es.jpg"), ("Cure", "/c.jpg")},
        )
        self.assertEqual(
            self._titulos("/api/reviews/mias/", "en"),
            {("Fight Club", "/en.jpg"), ("Cure", "/c.jpg")},
        )

    def test_listas_y_resenas_marcan_respaldo_por_campo_sin_marcar_ingles_nativo(self):
        """Solo los campos sin traducción llevan marca; inglés nativo no es un respaldo."""
        ProduccionTraduccion.objects.filter(
            produccion=self.traducida, idioma="es"
        ).update(poster="")
        for url in (f"/api/lists/{self.lista.pk}/items/", "/api/reviews/mias/"):
            with self.subTest(url=url):
                filas = self.cliente.get(url, HTTP_ACCEPT_LANGUAGE="es").json()[
                    "results"
                ]
                por_titulo = {fila["titulo"]: fila for fila in filas}
                self.assertEqual(
                    por_titulo["El club de la pelea"]["campos_en_ingles"], ["poster"]
                )
                self.assertEqual(
                    por_titulo["Cure"]["campos_en_ingles"], ["titulo", "poster"]
                )
                for fila in self.cliente.get(url, HTTP_ACCEPT_LANGUAGE="en").json()[
                    "results"
                ]:
                    self.assertNotIn("campos_en_ingles", fila)

    def test_el_idioma_guardado_de_la_cuenta_gana_al_encabezado(self):
        self.usuario.idioma = "es"
        self.usuario.save(update_fields=["idioma"])
        titulos = self._titulos(f"/api/lists/{self.lista.pk}/items/", "en")
        self.assertIn(("El club de la pelea", "/es.jpg"), titulos)

    def test_previews_de_listas_usan_el_poster_del_idioma(self):
        def previews(idioma):
            datos = self.cliente.get("/api/lists/", HTTP_ACCEPT_LANGUAGE=idioma).json()
            lista = next(item for item in datos if item["id"] == self.lista.pk)
            return set(lista["preview_posters"])

        self.assertEqual(previews("es"), {"/es.jpg", "/c.jpg"})
        self.assertEqual(previews("en"), {"/en.jpg", "/c.jpg"})

    def test_el_listado_no_consulta_traducciones_por_fila(self):
        for _ in range(5):
            produccion = ProduccionAudiovisualFactory()
            ProduccionTraduccion.objects.create(
                produccion=produccion, idioma="es", titulo="T"
            )
            Tiene.objects.create(lista=self.lista, produccion=produccion)
        url = f"/api/lists/{self.lista.pk}/items/"
        antes = self._consultas(url)
        for _ in range(5):
            produccion = ProduccionAudiovisualFactory()
            Tiene.objects.create(lista=self.lista, produccion=produccion)
        # Más filas, las mismas consultas: las traducciones llegan en un prefetch.
        self.assertEqual(self._consultas(url), antes)

    def _consultas(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as consultas:
            self.cliente.get(url, HTTP_ACCEPT_LANGUAGE="es")
        return len(consultas)


class GenerosPorIdiomaTests(TestCase):
    def setUp(self):
        self.servicios = {}
        parche = patch("catalogo.views.get_catalog_service", side_effect=self._servicio)
        parche.start()
        self.addCleanup(parche.stop)

    def _servicio(self, idioma=None):
        idioma = idioma or "en-US"
        if idioma not in self.servicios:
            servicio = Mock()
            servicio.get_genres.return_value = {
                "genres": [
                    {
                        "id": 16,
                        "name": "Animation" if idioma == "en-US" else "Animación",
                    },
                    {"id": 99, "name": "Documentary" if idioma == "en-US" else ""},
                ]
            }
            self.servicios[idioma] = servicio
        return self.servicios[idioma]

    def test_devuelve_los_generos_en_el_idioma_y_completa_los_vacios(self):
        es = APIClient().get("/api/catalogo/genres/?tipo=tv", HTTP_ACCEPT_LANGUAGE="es")
        self.assertEqual(
            es.json(),
            {
                "genres": [
                    {"id": 16, "name": "Animación"},
                    {"id": 99, "name": "Documentary"},
                ]
            },
        )
        self.servicios["es-MX"].get_genres.assert_called_once_with("tv")
        en = APIClient().get("/api/catalogo/genres/")
        self.assertEqual(en.json()["genres"][0]["name"], "Animation")

    def test_tipo_invalido_usa_el_contrato_de_errores(self):
        respuesta = APIClient().get("/api/catalogo/genres/?tipo=person")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["errors"][0]["code"], "invalid_choice")
