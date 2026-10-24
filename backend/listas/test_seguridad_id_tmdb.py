"""Auditoría F7 en listas: el alta de ítems pasa por el mismo `materializar()`.

La auditoría confirmó la falla en el alta de reseñas, pero agregar a una lista
llama a la misma función con el mismo payload (`id_tmdb` + `tipo`), así que
tenía las mismas dos fallas: fila vacía con un id inexistente y 500 (Internal
Server Error) con uno fuera de rango.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.exceptions import TMDBNotFound
from catalogo.models import ProduccionAudiovisual
from catalogo.tests import _ParchesDeMaterializacion
from listas.factories import ListaFactory
from listas.models import Tiene
from usuarios.factories import UsuarioFactory

MAXIMO_POSTGRES = 2_147_483_647


class AgregarIdInexistenteTests(_ParchesDeMaterializacion, TestCase):
    def setUp(self):
        super().setUp()
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)
        self.lista = ListaFactory(usuario=self.usuario, nombre="Para ver")

    def _agregar(self, id_tmdb):
        return self.cliente.post(
            f"/api/lists/{self.lista.pk}/items/",
            {"id_tmdb": id_tmdb, "tipo": "movie"},
            format="json",
        )

    def test_un_id_que_tmdb_no_conoce_es_404_y_no_deja_filas(self):
        self.servicio.get_movie_detail.side_effect = TMDBNotFound("HTTP 404")

        respuesta = self._agregar(999_999_999)

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.data["code"], "upstream_not_found")
        self.assertFalse(ProduccionAudiovisual.objects.exists())
        self.assertFalse(Tiene.objects.exists())

    def test_un_id_fuera_de_rango_es_400_sin_llamar_a_tmdb(self):
        respuesta = self._agregar(MAXIMO_POSTGRES + 1)

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            {
                "field": "id_tmdb",
                "code": "max_value",
                "params": {"maxValue": MAXIMO_POSTGRES},
            },
            respuesta.data["errors"],
        )
        self.servicio.get_movie_detail.assert_not_called()

    def test_la_pertenencia_valida_el_mismo_rango(self):
        respuesta = self.cliente.get(
            "/api/lists/", {"id_tmdb": MAXIMO_POSTGRES + 1, "tipo": "movie"}
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            ("id_tmdb", "max_value"),
            {(error["field"], error["code"]) for error in respuesta.data["errors"]},
        )
