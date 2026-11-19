"""Estado único por título: Watchlist, Watching o Watched (PR 4, 15/11/2026).

Un usuario tiene cada título en una sola de las tres listas de estado
(`pendientes`, `viendo`, `vistas`) o en ninguna. Favoritos y las personalizadas
son independientes. Acá se prueba la regla en sus tres puertas: la función de
`listas/services.py`, el endpoint `PUT /api/lists/status/` y los caminos viejos
(agregar un ítem a una predeterminada, calificar, borrar la nota).
"""

from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from catalogo.exceptions import TMDBNotFound
from catalogo.factories import CalificacionFactory, ProduccionAudiovisualFactory
from catalogo.models import Calificacion, TipoProduccion
from filmai.throttles import EscrituraThrottle
from listas.factories import ListaFactory
from listas.models import ClaveLista, Lista, Tiene
from listas.services import poner_estado
from listas.views import EstadoView
from usuarios.factories import UsuarioFactory

URL = "/api/lists/status/"
ESTADOS = (ClaveLista.PENDIENTES, ClaveLista.VIENDO, ClaveLista.VISTAS)


class _Base(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)
        self.produccion = ProduccionAudiovisualFactory(
            id_tmdb=550, tipo=TipoProduccion.PELICULA
        )

    def lista(self, clave, usuario=None):
        return (usuario or self.usuario).listas.get(clave=clave)

    def estados_de(self, produccion=None, usuario=None):
        """Las claves de estado en las que está el título (debería haber 0 o 1)."""
        return sorted(
            Tiene.objects.filter(
                lista__usuario=usuario or self.usuario,
                lista__clave__in=ESTADOS,
                produccion=produccion or self.produccion,
            ).values_list("lista__clave", flat=True)
        )


class PonerEstadoTests(_Base):
    """La función única que pone el estado y saca de las otras dos."""

    def test_sin_estado_previo_lo_pone_y_el_anterior_es_none(self):
        anterior, item = poner_estado(
            self.usuario, self.produccion, ClaveLista.PENDIENTES
        )

        self.assertIsNone(anterior)
        self.assertEqual(item.lista, self.lista(ClaveLista.PENDIENTES))
        self.assertEqual(self.estados_de(), ["pendientes"])

    def test_cambiar_de_estado_mueve_el_titulo_y_devuelve_el_anterior(self):
        poner_estado(self.usuario, self.produccion, ClaveLista.PENDIENTES)

        for nuevo, esperado in (
            (ClaveLista.VIENDO, "pendientes"),
            (ClaveLista.VISTAS, "viendo"),
            (ClaveLista.PENDIENTES, "vistas"),
        ):
            with self.subTest(nuevo=nuevo):
                anterior, _ = poner_estado(self.usuario, self.produccion, nuevo)

                self.assertEqual(anterior, esperado)
                self.assertEqual(self.estados_de(), [nuevo])

    def test_none_saca_el_titulo_del_estado(self):
        poner_estado(self.usuario, self.produccion, ClaveLista.VIENDO)

        anterior, item = poner_estado(self.usuario, self.produccion, None)

        self.assertEqual(anterior, "viendo")
        self.assertIsNone(item)
        self.assertEqual(self.estados_de(), [])

    def test_pedir_el_mismo_estado_no_cambia_nada(self):
        _, original = poner_estado(self.usuario, self.produccion, ClaveLista.VIENDO)

        anterior, item = poner_estado(self.usuario, self.produccion, ClaveLista.VIENDO)

        self.assertEqual(anterior, "viendo")
        # Es el mismo ítem: no se borra y se vuelve a crear (perdería la fecha).
        self.assertEqual(item.pk, original.pk)
        self.assertEqual(item.fecha_agregado, original.fecha_agregado)

    def test_con_fecha_el_item_nuevo_la_conserva(self):
        # El Undo devuelve el título con la fecha que tenía (la «Empezada el»).
        fecha = timezone.now() - timedelta(days=40)

        _, item = poner_estado(
            self.usuario, self.produccion, ClaveLista.VIENDO, fecha_agregado=fecha
        )

        item.refresh_from_db()
        self.assertEqual(item.fecha_agregado, fecha)

    def test_con_fecha_pero_ya_en_ese_estado_no_la_cambia(self):
        _, original = poner_estado(self.usuario, self.produccion, ClaveLista.VIENDO)

        _, item = poner_estado(
            self.usuario,
            self.produccion,
            ClaveLista.VIENDO,
            fecha_agregado=timezone.now() - timedelta(days=40),
        )

        item.refresh_from_db()
        self.assertEqual(item.fecha_agregado, original.fecha_agregado)

    def test_si_hay_dos_estados_por_datos_viejos_los_unifica(self):
        Tiene.objects.create(
            lista=self.lista(ClaveLista.PENDIENTES), produccion=self.produccion
        )
        Tiene.objects.create(
            lista=self.lista(ClaveLista.VISTAS), produccion=self.produccion
        )

        poner_estado(self.usuario, self.produccion, ClaveLista.VIENDO)

        self.assertEqual(self.estados_de(), ["viendo"])

    def test_no_toca_favoritos_ni_las_personalizadas(self):
        favoritos = self.lista(ClaveLista.FAVORITOS)
        propia = ListaFactory(usuario=self.usuario, nombre="Mi colección")
        for lista in (favoritos, propia):
            Tiene.objects.create(lista=lista, produccion=self.produccion)

        poner_estado(self.usuario, self.produccion, ClaveLista.VISTAS)
        poner_estado(self.usuario, self.produccion, None)

        self.assertTrue(favoritos.items.filter(produccion=self.produccion).exists())
        self.assertTrue(propia.items.filter(produccion=self.produccion).exists())

    def test_no_toca_a_otros_usuarios_ni_a_otros_titulos(self):
        otro = UsuarioFactory()
        distinto = ProduccionAudiovisualFactory(id_tmdb=551)
        poner_estado(otro, self.produccion, ClaveLista.VIENDO)
        poner_estado(self.usuario, distinto, ClaveLista.VIENDO)

        poner_estado(self.usuario, self.produccion, ClaveLista.VISTAS)

        self.assertEqual(self.estados_de(usuario=otro), ["viendo"])
        self.assertEqual(self.estados_de(distinto), ["viendo"])

    def test_un_estado_que_no_es_de_estado_se_rechaza(self):
        for clave in (ClaveLista.FAVORITOS, "otra"):
            with self.subTest(clave=clave), self.assertRaises(ValueError):
                poner_estado(self.usuario, self.produccion, clave)

    def test_si_falla_al_crear_el_estado_anterior_se_conserva(self):
        poner_estado(self.usuario, self.produccion, ClaveLista.PENDIENTES)

        with (
            patch("listas.services.Tiene.objects.create", side_effect=RuntimeError),
            self.assertRaises(RuntimeError),
        ):
            poner_estado(self.usuario, self.produccion, ClaveLista.VISTAS)

        self.assertEqual(self.estados_de(), ["pendientes"])


@patch("listas.views.materializar")
class EndpointEstadoTests(_Base):
    """`PUT /api/lists/status/`: el cambio de estado atómico (y el Undo)."""

    def poner(self, estado, **extra):
        cuerpo = {"id_tmdb": 550, "tipo": "movie", "estado": estado, **extra}
        return self.cliente.put(URL, cuerpo, format="json")

    def resumen(self, respuesta, clave):
        return next(
            lista for lista in respuesta.data["listas"] if lista["clave"] == clave
        )

    def test_requiere_autenticacion(self, materializar):
        respuesta = APIClient().put(
            URL, {"id_tmdb": 550, "tipo": "movie", "estado": "viendo"}, format="json"
        )

        self.assertEqual(respuesta.status_code, 401)

    def test_pone_el_estado_y_responde_como_la_consulta_de_pertenencia(
        self, materializar
    ):
        materializar.return_value = self.produccion

        respuesta = self.poner("viendo")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["estado"], "viendo")
        self.assertIsNone(respuesta.data["estado_anterior"])
        self.assertEqual(self.estados_de(), ["viendo"])
        # Las listas vienen igual que `GET /api/lists/?id_tmdb=550&tipo=movie`.
        esperado = self.cliente.get("/api/lists/", {"id_tmdb": 550, "tipo": "movie"})
        self.assertEqual(respuesta.data["listas"], esperado.data)
        viendo = self.resumen(respuesta, "viendo")
        self.assertTrue(viendo["contiene"])
        self.assertIsNotNone(viendo["item_id"])
        self.assertEqual(viendo["cantidad_items"], 1)
        self.assertFalse(self.resumen(respuesta, "vistas")["contiene"])

    def test_cambiar_de_estado_devuelve_el_anterior_y_mueve_el_titulo(
        self, materializar
    ):
        materializar.return_value = self.produccion
        self.poner("pendientes")

        respuesta = self.poner("vistas")

        self.assertEqual(respuesta.data["estado_anterior"], "pendientes")
        self.assertEqual(self.estados_de(), ["vistas"])
        self.assertFalse(self.resumen(respuesta, "pendientes")["contiene"])
        self.assertTrue(self.resumen(respuesta, "vistas")["contiene"])

    def test_null_saca_el_estado_y_sirve_de_undo(self, materializar):
        materializar.return_value = self.produccion
        self.poner("viendo")

        respuesta = self.poner(None)

        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.data["estado"])
        self.assertEqual(respuesta.data["estado_anterior"], "viendo")
        self.assertEqual(self.estados_de(), [])
        self.assertFalse(any(lista["contiene"] for lista in respuesta.data["listas"]))

    def test_volver_al_estado_anterior_deshace_el_cambio(self, materializar):
        materializar.return_value = self.produccion
        self.poner("pendientes")
        cambio = self.poner("viendo")

        self.poner(cambio.data["estado_anterior"])

        self.assertEqual(self.estados_de(), ["pendientes"])

    def test_el_mismo_estado_es_idempotente(self, materializar):
        materializar.return_value = self.produccion
        primera = self.poner("viendo")

        segunda = self.poner("viendo")

        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(segunda.data["estado_anterior"], "viendo")
        self.assertEqual(
            self.resumen(segunda, "viendo")["item_id"],
            self.resumen(primera, "viendo")["item_id"],
        )

    def test_materializa_el_titulo_si_no_esta_en_el_catalogo(self, materializar):
        materializar.return_value = self.produccion

        self.poner("pendientes")

        materializar.assert_called_once_with(550, "movie")

    def test_sacar_el_estado_no_llama_a_tmdb(self, materializar):
        respuesta = self.poner(None)

        self.assertEqual(respuesta.status_code, 200)
        materializar.assert_not_called()

    def test_un_titulo_que_tmdb_no_tiene_no_deja_nada_escrito(self, materializar):
        materializar.side_effect = TMDBNotFound("no existe")

        respuesta = self.poner("viendo", id_tmdb=999)

        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(Tiene.objects.exists())

    def test_favoritos_y_personalizadas_no_cambian(self, materializar):
        materializar.return_value = self.produccion
        propia = ListaFactory(usuario=self.usuario, nombre="Mi colección")
        for lista in (self.lista(ClaveLista.FAVORITOS), propia):
            Tiene.objects.create(lista=lista, produccion=self.produccion)

        respuesta = self.poner("viendo")

        self.assertTrue(self.resumen(respuesta, "favoritos")["contiene"])
        self.assertTrue(propia.items.exists())

    def test_la_nota_se_conserva_al_cambiar_de_estado(self, materializar):
        materializar.return_value = self.produccion
        CalificacionFactory(usuario=self.usuario, produccion=self.produccion)

        for estado in ("vistas", "viendo", "pendientes", None):
            with self.subTest(estado=estado):
                self.poner(estado)

                self.assertEqual(Calificacion.objects.count(), 1)

    def test_estado_invalido_o_ausente_es_400(self, materializar):
        for estado in ("favoritos", "watching", "", 3):
            with self.subTest(estado=estado):
                self.assertEqual(self.poner(estado).status_code, 400)
        sin_estado = self.cliente.put(
            URL, {"id_tmdb": 550, "tipo": "movie"}, format="json"
        )
        self.assertEqual(sin_estado.status_code, 400)
        self.assertEqual(sin_estado.data["code"], "validation_error")
        materializar.assert_not_called()

    def test_titulo_invalido_es_400(self, materializar):
        for cuerpo in (
            {"id_tmdb": 0, "tipo": "movie"},
            {"id_tmdb": 550, "tipo": "pelicula"},
            {"tipo": "movie"},
        ):
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.cliente.put(
                    URL, {**cuerpo, "estado": "viendo"}, format="json"
                )

                self.assertEqual(respuesta.status_code, 400)

    def test_el_undo_con_fecha_agregado_conserva_la_fecha_original(self, materializar):
        materializar.return_value = self.produccion
        empezada = timezone.now() - timedelta(days=48)
        self.poner("viendo")
        Tiene.objects.update(fecha_agregado=empezada)
        self.poner("vistas")

        respuesta = self.poner("viendo", fecha_agregado=empezada.isoformat())

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.estados_de(), ["viendo"])
        self.assertEqual(Tiene.objects.get().fecha_agregado, empezada)

    def test_sin_fecha_agregado_el_item_nuevo_lleva_la_de_ahora(self, materializar):
        materializar.return_value = self.produccion
        antes = timezone.now()

        self.poner("viendo")

        self.assertGreaterEqual(Tiene.objects.get().fecha_agregado, antes)

    def test_fecha_agregado_nula_se_trata_como_ausente(self, materializar):
        materializar.return_value = self.produccion

        respuesta = self.poner("viendo", fecha_agregado=None)

        self.assertEqual(respuesta.status_code, 200)

    def test_fecha_agregado_en_el_futuro_o_mal_formada_es_400(self, materializar):
        manana = (timezone.now() + timedelta(days=1)).isoformat()
        for fecha in (manana, "ayer", 12, "2026-13-45T00:00:00Z"):
            with self.subTest(fecha=fecha):
                respuesta = self.poner("viendo", fecha_agregado=fecha)

                self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.estados_de(), [])
        materializar.assert_not_called()

    def test_la_pertenencia_trae_la_fecha_del_item_de_cada_lista(self, materializar):
        materializar.return_value = self.produccion
        empezada = timezone.now() - timedelta(days=3)
        self.poner("viendo")
        Tiene.objects.update(fecha_agregado=empezada)

        respuesta = self.poner("viendo")

        viendo = self.resumen(respuesta, "viendo")
        self.assertEqual(parse_datetime(viendo["fecha_agregado"]), empezada)
        self.assertIsNone(self.resumen(respuesta, "vistas")["fecha_agregado"])
        esperado = self.cliente.get("/api/lists/", {"id_tmdb": 550, "tipo": "movie"})
        self.assertEqual(respuesta.data["listas"], esperado.data)

    def test_el_get_no_existe_en_esta_ruta(self, materializar):
        self.assertEqual(self.cliente.get(URL).status_code, 405)

    def test_usa_el_limite_comun_de_escrituras(self, materializar):
        self.assertEqual(EstadoView.throttle_classes, [EscrituraThrottle])

    def test_si_falla_el_alta_el_estado_anterior_queda_intacto(self, materializar):
        materializar.return_value = self.produccion
        self.poner("pendientes")

        with patch("listas.services.Tiene.objects.create", side_effect=RuntimeError):
            # El manejador de errores convierte lo inesperado en 500 (Internal
            # Server Error): la transacción ya se deshizo al salir de la vista.
            respuesta = self.poner("vistas")

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(self.estados_de(), ["pendientes"])


@patch("catalogo.reviews.materializar")
class CaminosViejosTests(_Base):
    """Agregar un ítem, calificar y quitar usan la misma regla de exclusividad."""

    def setUp(self):
        super().setUp()
        self.vistas = self.lista(ClaveLista.VISTAS)

    def agregar(self, clave):
        lista = self.lista(clave)
        with patch("listas.views.materializar", return_value=self.produccion):
            return self.cliente.post(
                f"/api/lists/{lista.pk}/items/",
                {"id_tmdb": 550, "tipo": "movie"},
                format="json",
            )

    def calificar(self, materializar):
        materializar.return_value = self.produccion
        respuesta = self.cliente.post(
            "/api/reviews/",
            {"id_tmdb": 550, "tipo": "movie", "valor": 8},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        return respuesta.data["id"]

    def test_agregar_a_una_lista_de_estado_saca_de_las_otras_dos(self, materializar):
        for destino, origen in (
            (ClaveLista.VIENDO, ClaveLista.PENDIENTES),
            (ClaveLista.VISTAS, ClaveLista.VIENDO),
            (ClaveLista.PENDIENTES, ClaveLista.VISTAS),
        ):
            with self.subTest(destino=destino):
                poner_estado(self.usuario, self.produccion, origen)

                respuesta = self.agregar(destino)

                self.assertEqual(respuesta.status_code, 201)
                self.assertEqual(self.estados_de(), [destino])

    def test_agregar_a_la_lista_donde_ya_esta_sigue_siendo_409(self, materializar):
        self.agregar(ClaveLista.VIENDO)

        respuesta = self.agregar(ClaveLista.VIENDO)

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data["code"], "list_item_duplicated")

    def test_agregar_a_favoritos_no_cambia_el_estado(self, materializar):
        poner_estado(self.usuario, self.produccion, ClaveLista.VIENDO)

        self.assertEqual(self.agregar(ClaveLista.FAVORITOS).status_code, 201)

        self.assertEqual(self.estados_de(), ["viendo"])

    def test_calificar_mueve_a_vistas_desde_cualquier_estado(self, materializar):
        for origen in (None, ClaveLista.PENDIENTES, ClaveLista.VIENDO):
            with self.subTest(origen=origen):
                Calificacion.objects.all().delete()
                poner_estado(self.usuario, self.produccion, origen)

                self.calificar(materializar)

                self.assertEqual(self.estados_de(), ["vistas"])

    def test_tras_calificar_el_estado_cambia_libremente_y_la_nota_queda(
        self, materializar
    ):
        self.calificar(materializar)

        poner_estado(self.usuario, self.produccion, ClaveLista.PENDIENTES)

        self.assertEqual(self.estados_de(), ["pendientes"])
        self.assertEqual(Calificacion.objects.count(), 1)

    def test_borrar_la_nota_saca_de_vistas(self, materializar):
        calificacion_id = self.calificar(materializar)

        respuesta = self.cliente.delete(f"/api/reviews/{calificacion_id}/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(self.estados_de(), [])

    def test_borrar_la_nota_no_toca_a_quien_cambio_a_viendo(self, materializar):
        calificacion_id = self.calificar(materializar)
        poner_estado(self.usuario, self.produccion, ClaveLista.VIENDO)

        self.cliente.delete(f"/api/reviews/{calificacion_id}/")

        self.assertEqual(self.estados_de(), ["viendo"])

    def test_quitar_de_vistas_algo_calificado_ya_no_es_409_y_conserva_la_nota(
        self, materializar
    ):
        self.calificar(materializar)
        item = self.vistas.items.get()

        respuesta = self.cliente.delete(f"/api/lists/{self.vistas.pk}/items/{item.pk}/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(Calificacion.objects.count(), 1)
        self.assertEqual(self.estados_de(), [])

    def test_el_flag_borrar_calificacion_ya_no_existe(self, materializar):
        self.calificar(materializar)
        item = self.vistas.items.get()

        respuesta = self.cliente.delete(
            f"/api/lists/{self.vistas.pk}/items/{item.pk}/?borrar_calificacion=true"
        )

        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(Calificacion.objects.count(), 1)


class ListasPredeterminadasTests(_Base):
    def test_son_cuatro_en_el_orden_favoritos_pendientes_viendo_vistas(self):
        respuesta = self.cliente.get("/api/lists/")

        self.assertEqual(
            [lista["clave"] for lista in respuesta.data[:4]],
            ["favoritos", "pendientes", "viendo", "vistas"],
        )
        self.assertEqual(
            [lista["nombre"] for lista in respuesta.data[:4]],
            ["Favoritos", "Pendientes", "Viendo", "Vistas"],
        )

    def test_el_alta_de_usuario_crea_las_cuatro(self):
        self.assertEqual(
            set(self.usuario.listas.values_list("clave", flat=True)),
            {"favoritos", "pendientes", "viendo", "vistas"},
        )

    def test_watching_y_viendo_son_nombres_reservados(self):
        for nombre in ("Watching", "viendo", "VIENDO"):
            with self.subTest(nombre=nombre):
                respuesta = self.cliente.post(
                    "/api/lists/", {"nombre": nombre}, format="json"
                )

                self.assertEqual(respuesta.status_code, 409)
                self.assertEqual(respuesta.data["code"], "list_name_reserved")

    def test_la_reparacion_crea_la_lista_viendo_que_falta(self):
        Lista.objects.filter(usuario=self.usuario, clave="viendo").delete()

        call_command("reparar_recursos_usuarios", verbosity=0)

        self.assertEqual(self.usuario.listas.get(clave="viendo").nombre, "Viendo")
