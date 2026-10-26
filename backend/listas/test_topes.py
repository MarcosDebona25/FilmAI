"""Topes de escritura (decisión del 26/10/2026, revisión de seguridad del 24/10).

Tres cosas: el límite común de escrituras por usuario (60 por minuto, compartido
por reseñas, listas y perfil), el techo de listas personalizadas y el de ítems
por lista personalizada. «Vistas» no tiene techo: crece sola al calificar.
"""

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.factories import ProduccionAudiovisualFactory
from filmai.throttles import EscrituraThrottle
from listas.factories import ListaFactory
from listas.models import Tiene
from usuarios.factories import UsuarioFactory


class _ConUsuario(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)


class TechoDeListasTests(_ConUsuario):
    @patch("listas.views.MAX_LISTAS_PERSONALIZADAS", 3)
    def test_pasado_el_techo_crear_otra_es_409_con_el_maximo(self):
        for numero in range(3):
            ListaFactory(usuario=self.usuario, nombre=f"Lista {numero}")

        respuesta = self.cliente.post(
            "/api/lists/", {"nombre": "Una más"}, format="json"
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data["code"], "list_limit_reached")
        self.assertEqual(respuesta.data["params"], {"maxLists": 3})

    @patch("listas.views.MAX_LISTAS_PERSONALIZADAS", 3)
    def test_las_predeterminadas_no_cuentan(self):
        # Favoritos, Pendientes y Vistas las crea la señal de alta del usuario.
        for numero in range(2):
            ListaFactory(usuario=self.usuario, nombre=f"Lista {numero}")

        respuesta = self.cliente.post(
            "/api/lists/", {"nombre": "Tercera"}, format="json"
        )

        self.assertEqual(respuesta.status_code, 201)


@patch("listas.views.MAX_ITEMS_POR_LISTA", 2)
@patch("listas.views.materializar")
class TechoDeItemsTests(_ConUsuario):
    def _producciones(self, cantidad):
        return [ProduccionAudiovisualFactory(id_tmdb=900 + i) for i in range(cantidad)]

    def test_una_lista_personalizada_llena_rechaza_otro_titulo(self, materializar):
        lista = ListaFactory(usuario=self.usuario, nombre="Para ver")
        a, b, c = self._producciones(3)
        Tiene.objects.create(lista=lista, produccion=a)
        Tiene.objects.create(lista=lista, produccion=b)
        materializar.return_value = c

        respuesta = self.cliente.post(
            f"/api/lists/{lista.pk}/items/",
            {"id_tmdb": c.id_tmdb, "tipo": "movie"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data["code"], "list_items_limit_reached")
        self.assertEqual(respuesta.data["params"], {"maxItems": 2})
        materializar.assert_not_called()

    def test_vistas_no_tiene_techo(self, materializar):
        vistas = self.usuario.listas.get(nombre="Vistas")
        a, b, c = self._producciones(3)
        Tiene.objects.create(lista=vistas, produccion=a)
        Tiene.objects.create(lista=vistas, produccion=b)
        materializar.return_value = c

        respuesta = self.cliente.post(
            f"/api/lists/{vistas.pk}/items/",
            {"id_tmdb": c.id_tmdb, "tipo": "movie"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 201)


class ReordenarTests(_ConUsuario):
    def test_mas_ids_que_listas_posibles_es_400(self):
        respuesta = self.cliente.put(
            "/api/lists/order/", {"ids": list(range(1, 102))}, format="json"
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            ("ids", "max_length"),
            {(error["field"], error["code"]) for error in respuesta.data["errors"]},
        )


@patch.dict(EscrituraThrottle.THROTTLE_RATES, {"escritura": "3/min"})
class LimiteDeEscriturasTests(_ConUsuario):
    def test_pasado_el_limite_las_escrituras_dan_429(self):
        estados = [
            self.cliente.post(
                "/api/lists/", {"nombre": f"Lista {numero}"}, format="json"
            ).status_code
            for numero in range(4)
        ]

        self.assertEqual(estados, [201, 201, 201, 429])

    def test_el_limite_es_comun_a_listas_y_resenas(self):
        for numero in range(3):
            self.cliente.post(
                "/api/lists/", {"nombre": f"Lista {numero}"}, format="json"
            )

        respuesta = self.cliente.post(
            "/api/reviews/",
            {"id_tmdb": 550, "tipo": "movie", "valor": 8},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(respuesta.data["code"], "throttled")

    def test_las_lecturas_no_cuentan(self):
        for _ in range(10):
            self.cliente.get("/api/lists/")

        respuesta = self.cliente.post("/api/lists/", {"nombre": "Nueva"}, format="json")

        self.assertEqual(respuesta.status_code, 201)

    def test_cada_usuario_tiene_su_contador(self):
        for numero in range(3):
            self.cliente.post(
                "/api/lists/", {"nombre": f"Lista {numero}"}, format="json"
            )
        otro = APIClient()
        otro.force_authenticate(UsuarioFactory())

        respuesta = otro.post("/api/lists/", {"nombre": "Mía"}, format="json")

        self.assertEqual(respuesta.status_code, 201)
