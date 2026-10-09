"""Pruebas HTTP de L-01: contratos y reglas de negocio de listas."""

from importlib import import_module
from unittest.mock import patch

from django.apps import apps
from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.factories import (
    CalificacionFactory,
    ProduccionAudiovisualFactory,
    ResenaFactory,
)
from catalogo.models import Calificacion, Resena, TipoProduccion
from listas.factories import ListaFactory
from listas.models import Lista, Tiene, TipoLista
from usuarios.factories import UsuarioFactory

# El nombre empieza con un dígito: no se puede importar con `import` normal.
_MIGRACION_0004 = import_module("listas.migrations.0004_calificadas_en_vistas")


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
        self.assertIn("tipo", {entry["field"] for entry in respuesta.data["errors"]})

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
        self.assertEqual(respuesta.data["code"], "list_name_duplicated")

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
        self.assertIn("nombre", {entry["field"] for entry in con_guion.data["errors"]})
        self.assertIn(
            "nombre", {entry["field"] for entry in demasiado_largo.data["errors"]}
        )

    def test_predeterminadas_no_se_renombran_ni_eliminan(self):
        """La API sostiene la regla incluso si un cliente evita el menú UI."""
        renombrar = self.cliente.put(
            f"/api/lists/{self.favoritos.pk}/", {"nombre": "Otro"}, format="json"
        )
        eliminar = self.cliente.delete(f"/api/lists/{self.favoritos.pk}/")

        self.assertEqual(renombrar.status_code, 409)
        self.assertEqual(eliminar.status_code, 409)
        self.assertEqual(renombrar.data["code"], "default_list_protected")
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
        self.assertEqual(respuesta.data["code"], "list_item_duplicated")
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
        self.assertEqual(respuesta.data["code"], "rating_blocks_removal_from_watched")
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


class QuitarDeVistasBorrandoCalificacionTests(TestCase):
    """El flag que convierte el 409 de CU-011 en una confirmación (fase 3 de C-08).

    Hasta acá, quitar de «Vistas» algo calificado respondía 409 y mandaba al
    usuario a borrar su calificación en otra pantalla. Con
    `?borrar_calificacion=true` la UI puede preguntar —«Se eliminarán tu
    calificación de 9/10 y tu reseña»— y hacerlo en el momento.

    El 409 sin el flag no cambia: el flag es aditivo, y es el 409 lo que le
    avisa al frontend que tiene que preguntar antes.
    """

    def setUp(self):
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)
        self.vistas = self.usuario.listas.get(nombre="Vistas")
        self.produccion = ProduccionAudiovisualFactory(
            id_tmdb=550, tipo=TipoProduccion.PELICULA
        )
        self.item = Tiene.objects.create(lista=self.vistas, produccion=self.produccion)

    def _calificar(self, *, con_texto=True):
        calificacion = CalificacionFactory(
            usuario=self.usuario, produccion=self.produccion, valor=9
        )
        if con_texto:
            ResenaFactory(calificacion=calificacion, texto="La primera regla...")
        return calificacion

    def _quitar(self, *, flag=None):
        url = f"/api/lists/{self.vistas.pk}/items/{self.item.pk}/"
        if flag is not None:
            url = f"{url}?borrar_calificacion={flag}"
        return self.cliente.delete(url)

    def test_con_el_flag_borra_la_calificacion_y_quita_el_item(self):
        self._calificar()

        respuesta = self._quitar(flag="true")

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Tiene.objects.filter(pk=self.item.pk).exists())
        self.assertFalse(Calificacion.objects.exists())

    def test_el_flag_se_lleva_tambien_la_resena(self):
        # Por CASCADE. Es lo que el modal tiene que advertir: quien escribió 800
        # caracteres los pierde, y enterarse después sería una pérdida por
        # sorpresa.
        self._calificar()

        self._quitar(flag="true")

        self.assertFalse(Resena.objects.exists())

    def test_sin_el_flag_el_409_sigue_igual(self):
        # El cambio es aditivo: el comportamiento por defecto no se toca, y es
        # el 409 el que le dice al frontend que tiene que preguntar.
        self._calificar()

        respuesta = self._quitar()

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data["code"], "rating_blocks_removal_from_watched")
        self.assertTrue(Calificacion.objects.exists())
        self.assertTrue(Tiene.objects.filter(pk=self.item.pk).exists())

    def test_con_el_flag_en_false_tambien_da_409(self):
        # `?borrar_calificacion=false` es una respuesta explícita de "no": tiene
        # que comportarse como no mandar nada, no como mandar "true". Sin este
        # caso, cualquier valor presente activaría el borrado.
        self._calificar()

        respuesta = self._quitar(flag="false")

        self.assertEqual(respuesta.status_code, 409)
        self.assertTrue(Calificacion.objects.exists())

    def test_el_flag_sin_calificacion_es_un_borrado_normal(self):
        # No hay nada que borrar de más: el flag es permiso, no orden.
        respuesta = self._quitar(flag="true")

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Tiene.objects.filter(pk=self.item.pk).exists())

    def test_en_una_lista_que_no_es_vistas_el_flag_no_borra_nada(self):
        # La regla de CU-011 es solo de «Vistas»: quitar de Favoritos algo
        # calificado nunca estuvo bloqueado, así que el flag no tiene por qué
        # destruir una calificación ahí.
        calificacion = self._calificar()
        favoritos = self.usuario.listas.get(nombre="Favoritos")
        item = Tiene.objects.create(lista=favoritos, produccion=self.produccion)

        respuesta = self.cliente.delete(
            f"/api/lists/{favoritos.pk}/items/{item.pk}/?borrar_calificacion=true"
        )

        self.assertEqual(respuesta.status_code, 204)
        self.assertTrue(Calificacion.objects.filter(pk=calificacion.pk).exists())

    def test_la_calificacion_de_otro_usuario_no_se_toca(self):
        # El borrado se acota al dueño de la lista. La calificación de otra
        # persona sobre la misma película no es asunto de este request.
        ajena = CalificacionFactory(
            usuario=UsuarioFactory(), produccion=self.produccion, valor=7
        )
        self._calificar()

        self._quitar(flag="true")

        self.assertTrue(Calificacion.objects.filter(pk=ajena.pk).exists())

    def test_un_valor_invalido_en_el_flag_se_rechaza(self):
        # Ni "true" ni "false": mejor un 400 que adivinar. Si un typo como
        # `borrar_calificacion=tru` se interpretara como false, el usuario
        # confirmaría el borrado y recibiría un 409 sin entender por qué.
        self._calificar()

        respuesta = self._quitar(flag="quizas")

        self.assertEqual(respuesta.status_code, 400)
        self.assertTrue(Calificacion.objects.exists())


class MigracionCalificadasEnVistasTests(TestCase):
    """`listas.0004`: repara las calificaciones anteriores a la regla del 30/09.

    La función se prueba con los modelos actuales (`django.apps.apps`) en vez
    de migrar la base hacia atrás y hacia adelante: es la misma consulta y
    mucho más rápida. Lo que importa es el efecto sobre los datos.
    """

    def setUp(self):
        self.usuario = UsuarioFactory()
        self.vistas = self.usuario.listas.get(nombre="Vistas")

    def _migrar(self):
        _MIGRACION_0004.poner_calificadas_en_vistas(apps, None)

    def test_pone_en_vistas_lo_calificado_y_nada_mas(self):
        calificada, no_calificada = ProduccionAudiovisualFactory.create_batch(2)
        Calificacion.objects.create(
            usuario=self.usuario, produccion=calificada, valor=8
        )

        self._migrar()

        self.assertEqual(list(self.vistas.producciones.all()), [calificada])
        self.assertNotIn(no_calificada, self.vistas.producciones.all())

    def test_lo_que_ya_estaba_en_vistas_no_se_duplica(self):
        # Marcada a mano y calificada: el ítem ya existe y el UNIQUE de
        # `Tiene` haría fallar la migración entera sin `ignore_conflicts`.
        produccion = ProduccionAudiovisualFactory()
        Tiene.objects.create(lista=self.vistas, produccion=produccion)
        Calificacion.objects.create(
            usuario=self.usuario, produccion=produccion, valor=6
        )

        self._migrar()

        self.assertEqual(self.vistas.items.count(), 1)

    def test_cada_calificacion_va_a_las_vistas_de_su_autor(self):
        otro = UsuarioFactory()
        produccion = ProduccionAudiovisualFactory()
        Calificacion.objects.create(usuario=otro, produccion=produccion, valor=9)

        self._migrar()

        self.assertFalse(self.vistas.items.exists())
        self.assertTrue(otro.listas.get(nombre="Vistas").items.exists())

    def test_correrla_dos_veces_da_lo_mismo(self):
        # Idempotente: si alguien la re-aplica a mano, no agrega nada nuevo.
        Calificacion.objects.create(
            usuario=self.usuario, produccion=ProduccionAudiovisualFactory(), valor=7
        )

        self._migrar()
        self._migrar()

        self.assertEqual(self.vistas.items.count(), 1)
