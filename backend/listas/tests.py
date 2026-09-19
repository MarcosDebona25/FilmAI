"""Pruebas HTTP de L-01: contratos y reglas de negocio de listas."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.factories import CalificacionFactory, ProduccionAudiovisualFactory
from catalogo.models import TipoProduccion
from listas.factories import ListaFactory
from listas.models import Lista, Tiene, TipoLista
from usuarios.factories import UsuarioFactory


class ListasEndpointsTests(TestCase):
    """Cada prueba describe un caso observable por el frontend."""

    def setUp(self):
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)
        self.favoritos = self.usuario.listas.get(nombre="Favoritos")
        self.pendientes = self.usuario.listas.get(nombre="Pendientes")
        self.vistas = self.usuario.listas.get(nombre="Vistas")

    def _lista_personalizada(self, nombre="Para ver"):
        return ListaFactory(usuario=self.usuario, nombre=nombre)

    def _produccion(self, *, id_tmdb=550, tipo=TipoProduccion.PELICULA, **extra):
        return ProduccionAudiovisualFactory(id_tmdb=id_tmdb, tipo=tipo, **extra)

    def test_requiere_autenticacion(self):
        """Las listas son datos personales y no se exponen a anónimos."""
        respuesta = APIClient().get("/api/lists/")

        self.assertEqual(respuesta.status_code, 401)

    def test_lista_resumen_trae_orden_contadores_y_preview(self):
        """La ListCard recibe total, desglose y hasta cinco pósters recientes."""
        personalizada = self._lista_personalizada("Ciencia ficción")
        peliculas = [
            self._produccion(id_tmdb=100 + indice, poster=f"/{indice}.jpg")
            for indice in range(5)
        ]
        serie = self._produccion(
            id_tmdb=200,
            tipo=TipoProduccion.SERIE,
            poster="/serie.jpg",
        )
        for produccion in [*peliculas, serie]:
            Tiene.objects.create(lista=personalizada, produccion=produccion)

        respuesta = self.cliente.get("/api/lists/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            [lista["nombre"] for lista in respuesta.data[:3]],
            ["Favoritos", "Pendientes", "Vistas"],
        )
        resumen = next(
            lista for lista in respuesta.data if lista["id"] == personalizada.pk
        )
        self.assertEqual(resumen["cantidad_items"], 6)
        self.assertEqual(resumen["cantidad_peliculas"], 5)
        self.assertEqual(resumen["cantidad_series"], 1)
        self.assertEqual(len(resumen["preview_posters"]), 5)
        self.assertNotIn("contiene", resumen)

    def test_consulta_de_pertenencia_entrega_item_id(self):
        """El checklist futuro sabe qué desmarcar sin recorrer páginas."""
        produccion = self._produccion()
        item = Tiene.objects.create(lista=self.favoritos, produccion=produccion)

        respuesta = self.cliente.get(
            f"/api/lists/?id_tmdb={produccion.id_tmdb}&tipo=movie"
        )

        self.assertEqual(respuesta.status_code, 200)
        favorito = next(
            lista for lista in respuesta.data if lista["id"] == self.favoritos.pk
        )
        pendiente = next(
            lista for lista in respuesta.data if lista["id"] == self.pendientes.pk
        )
        self.assertTrue(favorito["contiene"])
        self.assertEqual(favorito["item_id"], item.pk)
        self.assertFalse(pendiente["contiene"])
        self.assertIsNone(pendiente["item_id"])

    def test_consulta_de_pertenencia_exige_los_dos_parametros(self):
        """Evita respuestas ambiguas cuando falta el tipo TMDB."""
        respuesta = self.cliente.get("/api/lists/?id_tmdb=550")

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("tipo", respuesta.data)

    def test_crea_lista_con_nombre_normalizado_y_caracteres_permitidos(self):
        """Los nombres naturales se guardan consistentes para la unicidad."""
        respuesta = self.cliente.post(
            "/api/lists/", {"nombre": "  Ciencia   Ficcion 2026  "}, format="json"
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data["nombre"], "Ciencia Ficcion 2026")
        self.assertEqual(respuesta.data["tipo"], TipoLista.PERSONALIZADA)
        self.assertEqual(respuesta.data["cantidad_items"], 0)
        self.assertEqual(respuesta.data["cantidad_peliculas"], 0)
        self.assertEqual(respuesta.data["cantidad_series"], 0)

    def test_rechaza_nombre_duplicado_sin_distinguir_mayusculas(self):
        """Evita dos cards que para el usuario representan la misma lista."""
        self._lista_personalizada("Ciencia Ficcion")

        respuesta = self.cliente.post(
            "/api/lists/", {"nombre": "ciencia ficcion"}, format="json"
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data["codigo"], "nombre_lista_duplicado")

    def test_rechaza_nombre_invalido_o_mas_largo_de_ochenta_caracteres(self):
        """El límite se aplica tras normalizar y tampoco se admiten guiones."""
        con_guion = self.cliente.post(
            "/api/lists/", {"nombre": "Sci-Fi"}, format="json"
        )
        demasiado_largo = self.cliente.post(
            "/api/lists/", {"nombre": "a" * 81}, format="json"
        )

        self.assertEqual(con_guion.status_code, 400)
        self.assertEqual(demasiado_largo.status_code, 400)
        self.assertIn("nombre", con_guion.data)
        self.assertIn("nombre", demasiado_largo.data)

    def test_predeterminadas_no_se_renombran_ni_eliminan(self):
        """La API sostiene la regla incluso si un cliente evita el menú UI."""
        renombrar = self.cliente.put(
            f"/api/lists/{self.favoritos.pk}/", {"nombre": "Otro"}, format="json"
        )
        eliminar = self.cliente.delete(f"/api/lists/{self.favoritos.pk}/")

        self.assertEqual(renombrar.status_code, 409)
        self.assertEqual(eliminar.status_code, 409)
        self.assertEqual(renombrar.data["codigo"], "lista_predeterminada_protegida")
        self.assertTrue(Lista.objects.filter(pk=self.favoritos.pk).exists())

    def test_renombrar_preserva_el_resumen_de_la_lista(self):
        """Renombrar no altera los ítems ni entrega contadores engañosos."""
        lista = self._lista_personalizada()
        produccion = self._produccion()
        Tiene.objects.create(lista=lista, produccion=produccion)

        respuesta = self.cliente.put(
            f"/api/lists/{lista.pk}/", {"nombre": "Renombrada"}, format="json"
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["nombre"], "Renombrada")
        self.assertEqual(respuesta.data["cantidad_items"], 1)
        self.assertEqual(respuesta.data["cantidad_peliculas"], 1)
        self.assertEqual(respuesta.data["cantidad_series"], 0)

    def test_eliminar_personalizada_borra_sus_items(self):
        """CU-012 exige borrar permanentemente la lista y sus relaciones."""
        lista = self._lista_personalizada()
        item = Tiene.objects.create(lista=lista, produccion=self._produccion())

        respuesta = self.cliente.delete(f"/api/lists/{lista.pk}/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Lista.objects.filter(pk=lista.pk).exists())
        self.assertFalse(Tiene.objects.filter(pk=item.pk).exists())

    @patch("listas.views.materializar")
    def test_agregar_item_materializa_y_registra_fecha(self, materializar_mock):
        """Toda relación apunta a una producción local materializada primero."""
        lista = self._lista_personalizada()
        produccion = self._produccion()
        materializar_mock.return_value = produccion

        respuesta = self.cliente.post(
            f"/api/lists/{lista.pk}/items/",
            {"id_tmdb": 550, "tipo": "movie"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 201)
        materializar_mock.assert_called_once_with(550, "movie")
        item = Tiene.objects.get(lista=lista, produccion=produccion)
        self.assertIsNotNone(item.fecha_agregado)
        self.assertEqual(respuesta.data["item_id"], item.pk)

    @patch("listas.views.materializar")
    def test_agregar_item_duplicado_devuelve_conflicto(self, materializar_mock):
        """La restricción N:N se comunica al frontend con un código estable."""
        lista = self._lista_personalizada()
        produccion = self._produccion()
        Tiene.objects.create(lista=lista, produccion=produccion)
        materializar_mock.return_value = produccion

        respuesta = self.cliente.post(
            f"/api/lists/{lista.pk}/items/",
            {"id_tmdb": 550, "tipo": "movie"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data["codigo"], "item_duplicado")
        self.assertEqual(Tiene.objects.filter(lista=lista).count(), 1)

    def test_items_usa_cursor_de_veinte_resultados(self):
        """El scroll recibe un lote acotado y una URL para continuar."""
        lista = self._lista_personalizada()
        for indice in range(21):
            Tiene.objects.create(
                lista=lista,
                produccion=self._produccion(id_tmdb=1000 + indice),
            )

        respuesta = self.cliente.get(f"/api/lists/{lista.pk}/items/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data["results"]), 20)
        self.assertIsNotNone(respuesta.data["next"])
        self.assertIsNone(respuesta.data["previous"])

    def test_quitar_de_vistas_con_calificacion_activa_es_conflicto(self):
        """CU-011 impide romper el historial que respalda una calificación."""
        produccion = self._produccion()
        item = Tiene.objects.create(lista=self.vistas, produccion=produccion)
        CalificacionFactory(usuario=self.usuario, produccion=produccion, activa=True)

        respuesta = self.cliente.delete(f"/api/lists/{self.vistas.pk}/items/{item.pk}/")

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(
            respuesta.data["codigo"], "calificacion_impide_quitar_de_vistas"
        )
        self.assertTrue(Tiene.objects.filter(pk=item.pk).exists())

    def test_quitar_item_de_lista_propietaria(self):
        """Los ítems de cualquier lista, incluso predeterminada, se pueden quitar."""
        produccion = self._produccion()
        item = Tiene.objects.create(lista=self.pendientes, produccion=produccion)

        respuesta = self.cliente.delete(
            f"/api/lists/{self.pendientes.pk}/items/{item.pk}/"
        )

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Tiene.objects.filter(pk=item.pk).exists())

    def test_no_expone_listas_ni_items_de_otro_usuario(self):
        """Un ID ajeno recibe 404 y no revela datos de otra cuenta."""
        ajeno = UsuarioFactory()
        lista_ajena = ListaFactory(usuario=ajeno)
        item_ajeno = Tiene.objects.create(
            lista=lista_ajena,
            produccion=self._produccion(),
        )

        detalle = self.cliente.delete(f"/api/lists/{lista_ajena.pk}/")
        item = self.cliente.delete(
            f"/api/lists/{lista_ajena.pk}/items/{item_ajeno.pk}/"
        )

        self.assertEqual(detalle.status_code, 404)
        self.assertEqual(item.status_code, 404)
