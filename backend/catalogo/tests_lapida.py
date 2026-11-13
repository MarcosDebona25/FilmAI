"""Dónde se ve (y dónde no) una lápida: título que TMDB ya no tiene (#180).

Una lápida es una producción con `disponible_en_tmdb = False`, sin contenido de
TMDB, que alguien calificó o guardó en una lista. Solo se muestra en las listas
y en «Mis reseñas» del propio usuario, como «Title no longer available».
"""

from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from catalogo.factories import (
    CalificacionFactory,
    ProduccionAudiovisualFactory,
    ResenaFactory,
)
from catalogo.models import (
    Calificacion,
    EstadoEmbedding,
    ProduccionAudiovisual,
    ProduccionEmbedding,
    TipoProduccion,
)
from catalogo.services.semantica import buscar_semantico
from catalogo.services.traducciones import pendientes
from catalogo.tests_semantica import vector_a
from listas.factories import ListaFactory
from listas.models import Tiene
from usuarios.factories import UsuarioFactory


def lapida(id_tmdb=900, tipo=TipoProduccion.PELICULA):
    """La fila tal como la deja `vencimiento._convertir_en_lapida`."""
    return ProduccionAudiovisual.objects.create(
        id_tmdb=id_tmdb,
        tipo=tipo,
        titulo="",
        disponible_en_tmdb=False,
        fecha_enriquecimiento=timezone.now(),
    )


class LapidaFueraDeLasBusquedasTests(TestCase):
    def test_la_busqueda_semantica_no_la_devuelve_aunque_conserve_un_vector(self):
        # Pasar a lápida borra el embedding; esto es la segunda barrera, por si
        # un vector llegara a existir (un `generar_embedding` en vuelo).
        normal = ProduccionAudiovisualFactory(
            titulo="Moon", tipo=TipoProduccion.PELICULA
        )
        ProduccionEmbedding.objects.create(
            produccion=normal, vector=vector_a(0.1), estado=EstadoEmbedding.READY
        )
        muerta = lapida()
        ProduccionEmbedding.objects.create(
            produccion=muerta, vector=vector_a(0.0), estado=EstadoEmbedding.READY
        )

        with (
            patch(
                "catalogo.services.semantica.generar_vector",
                return_value=vector_a(0),
            ),
            patch("catalogo.services.semantica.modelo_cargado", return_value=True),
        ):
            titulos = [p.titulo for p in buscar_semantico("algo")]

        self.assertEqual(titulos, ["Moon"])

    def test_el_relleno_de_traducciones_no_la_pide_a_tmdb_cada_noche(self):
        # Sin traducciones y enriquecida, `pendientes()` la elegiría y TMDB
        # respondería 404 todas las noches.
        lapida()

        self.assertFalse(pendientes().exists())


class LapidaEnListasYResenasTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory(idioma="en")
        self.api = APIClient()
        self.api.force_authenticate(self.usuario)

    def test_un_item_de_lista_llega_como_no_disponible_con_su_identidad(self):
        lista = ListaFactory(usuario=self.usuario)
        normal = ProduccionAudiovisualFactory(titulo="Moon")
        Tiene.objects.create(lista=lista, produccion=normal)
        muerta = lapida(id_tmdb=900)
        Tiene.objects.create(lista=lista, produccion=muerta)

        respuesta = self.api.get(f"/api/lists/{lista.pk}/items/")

        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        por_id = {item["id_tmdb"]: item for item in respuesta.data["results"]}
        self.assertTrue(por_id[normal.id_tmdb]["disponible"])
        caida = por_id[900]
        self.assertFalse(caida["disponible"])
        # Sin contenido de TMDB, pero con lo que el usuario necesita para
        # quitarla de la lista.
        self.assertEqual((caida["titulo"], caida["poster"]), ("", ""))
        self.assertIsNone(caida["anio"])
        self.assertIsNone(caida["calificacion_promedio"])
        self.assertIn("item_id", caida)

    def test_se_puede_quitar_de_la_lista_como_cualquier_item(self):
        lista = ListaFactory(usuario=self.usuario)
        item = Tiene.objects.create(lista=lista, produccion=lapida())

        respuesta = self.api.delete(f"/api/lists/{lista.pk}/items/{item.pk}/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Tiene.objects.filter(pk=item.pk).exists())
        # La fila sigue (ya no la usa nadie): la borrará la próxima noche.
        self.assertTrue(ProduccionAudiovisual.objects.filter(id_tmdb=900).exists())

    def test_la_lapida_no_cuenta_como_poster_de_portada_de_la_lista(self):
        lista = ListaFactory(usuario=self.usuario)
        Tiene.objects.create(lista=lista, produccion=lapida())

        respuesta = self.api.get(f"/api/lists/{lista.pk}/")

        self.assertEqual(respuesta.data["preview_posters"], [])

    def test_mis_resenas_la_muestra_no_disponible_con_nota_y_texto(self):
        muerta = lapida()
        calificacion = CalificacionFactory(
            usuario=self.usuario, produccion=muerta, valor=8
        )
        ResenaFactory(calificacion=calificacion, texto="La vi de chico.")
        normal = CalificacionFactory(
            usuario=self.usuario, produccion=ProduccionAudiovisualFactory()
        )

        respuesta = self.api.get("/api/reviews/mias/")

        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        por_id = {item["id"]: item for item in respuesta.data["results"]}
        caida = por_id[calificacion.pk]
        self.assertFalse(caida["disponible"])
        self.assertEqual((caida["valor"], caida["texto"]), (8, "La vi de chico."))
        self.assertEqual((caida["titulo"], caida["poster"]), ("", ""))
        self.assertTrue(por_id[normal.pk]["disponible"])

    def test_se_puede_borrar_la_resena_de_una_lapida(self):
        calificacion = CalificacionFactory(
            usuario=self.usuario, produccion=lapida(), valor=8
        )
        ResenaFactory(calificacion=calificacion, texto="La vi de chico.")

        respuesta = self.api.delete(f"/api/reviews/{calificacion.pk}/texto/")

        self.assertEqual(respuesta.status_code, 204)

    def test_borrar_la_calificacion_de_una_lapida_libera_la_fila_para_la_noche(self):
        # Quitar la última referencia deja la fila sin uso: la tarea la borra.
        calificacion = CalificacionFactory(
            usuario=self.usuario, produccion=lapida(), valor=8
        )

        respuesta = self.api.delete(f"/api/reviews/{calificacion.pk}/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertTrue(
            ProduccionAudiovisual.objects.filter(
                id_tmdb=900, disponible_en_tmdb=False
            ).exists()
        )


class LapidaNoSeAceptaDeNuevoTests(TestCase):
    """Si TMDB ya no tiene el título, nadie puede calificarlo ni guardarlo.

    `materializar()` es la puerta común de calificar y de agregar a una lista:
    una lápida cuenta como enriquecida (su fecha es de hoy), así que sin esta
    regla se devolvería tal cual y el POST escribiría una fila sobre un título
    sin contenido.
    """

    def setUp(self):
        self.usuario = UsuarioFactory(idioma="en")
        self.api = APIClient()
        self.api.force_authenticate(self.usuario)
        self.muerta = lapida(id_tmdb=901)

    def test_calificar_una_lapida_responde_404_y_no_escribe_nada(self):
        respuesta = self.api.post(
            "/api/reviews/",
            {"id_tmdb": 901, "tipo": "movie", "valor": 4},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 404, respuesta.data)
        self.assertFalse(Calificacion.objects.exists())

    def test_agregar_una_lapida_a_una_lista_responde_404_y_no_escribe_nada(self):
        lista = ListaFactory(usuario=self.usuario)

        respuesta = self.api.post(
            f"/api/lists/{lista.pk}/items/",
            {"id_tmdb": 901, "tipo": "movie"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 404, respuesta.data)
        self.assertFalse(Tiene.objects.exists())

    def test_la_lapida_no_se_borra_ni_cambia_al_rechazar_el_pedido(self):
        self.api.post(
            "/api/reviews/",
            {"id_tmdb": 901, "tipo": "movie", "valor": 4},
            format="json",
        )

        self.muerta.refresh_from_db()
        self.assertFalse(self.muerta.disponible_en_tmdb)
