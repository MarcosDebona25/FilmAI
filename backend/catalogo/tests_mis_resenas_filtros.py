"""Filtros de «Mis reseñas»: `GET /api/reviews/mias/` (perfil según el canvas, 15/10/2026).

El diseño está en `openspec/changes/perfil-canvas/design.md` §2. Los datos son
de la base de pruebas (factories); no hay TMDB de por medio.
"""

from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.factories import (
    CalificacionFactory,
    ProduccionAudiovisualFactory,
    ResenaFactory,
)
from catalogo.models import Calificacion, ProduccionTraduccion, TipoProduccion
from usuarios.factories import UsuarioFactory


class MisResenasFiltrosTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory()
        self.api = APIClient()
        self.api.force_authenticate(self.usuario)

        def calificar(titulo, tipo, valor, dia, texto=None, id_tmdb=None):
            produccion = ProduccionAudiovisualFactory(
                titulo=titulo, tipo=tipo, **({"id_tmdb": id_tmdb} if id_tmdb else {})
            )
            calificacion = CalificacionFactory(
                usuario=self.usuario, produccion=produccion, valor=valor
            )
            # `fecha` es `auto_now_add`: se fija después con un update.
            Calificacion.objects.filter(pk=calificacion.pk).update(fecha=dia)
            if texto:
                ResenaFactory(calificacion=calificacion, texto=texto)
            return produccion

        self.amelie = calificar(
            "Amélie", TipoProduccion.PELICULA, 9, date(2026, 10, 3), "Encantadora."
        )
        calificar("Aliens", TipoProduccion.PELICULA, 9, date(2026, 10, 2), "Tensa.")
        calificar("American Dad!", TipoProduccion.SERIE, 7, date(2026, 9, 28))
        calificar("Alpha", TipoProduccion.PELICULA, 4, date(2026, 9, 20), "Floja.")
        # De otra persona: nunca aparece.
        CalificacionFactory(valor=10)

    def pedir(self, **params):
        respuesta = self.api.get("/api/reviews/mias/", params)
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        return respuesta.data

    def titulos(self, datos):
        return [item["titulo"] for item in datos["results"]]

    def test_sin_filtros_trae_todas_las_propias_con_los_dos_totales(self):
        datos = self.pedir()

        self.assertEqual(
            self.titulos(datos), ["Amélie", "Aliens", "American Dad!", "Alpha"]
        )
        self.assertEqual((datos["total"], datos["total_propias"]), (4, 4))

    def test_la_busqueda_ignora_mayusculas_y_acentos(self):
        datos = self.pedir(q="  AMELIE ")

        self.assertEqual(self.titulos(datos), ["Amélie"])
        self.assertEqual((datos["total"], datos["total_propias"]), (1, 4))

    def test_la_busqueda_encuentra_el_titulo_traducido(self):
        ProduccionTraduccion.objects.create(
            produccion=self.amelie, idioma="es", titulo="El fabuloso destino de Amélie"
        )

        datos = self.pedir(q="fabuloso")

        self.assertEqual(datos["total"], 1)

    def test_con_y_sin_resena(self):
        self.assertEqual(self.pedir(texto="sin")["total"], 1)
        self.assertEqual(self.pedir(texto="con")["total"], 3)

    def test_por_clase(self):
        # `clase` y no `tipo`: con `id_tmdb` + `tipo` la ruta devuelve una sola.
        self.assertEqual(self.titulos(self.pedir(clase="tv")), ["American Dad!"])
        self.assertEqual(self.pedir(clase="movie")["total"], 3)

    def test_por_nota(self):
        self.assertEqual(self.pedir(nota_min=9)["total"], 2)
        self.assertEqual(self.titulos(self.pedir(nota_max=4)), ["Alpha"])

    def test_orden_por_nota_y_por_fecha(self):
        self.assertEqual(
            self.titulos(self.pedir(orden="nota-asc")),
            # Amélie y Aliens empatan en 9: desempata el id (Amélie se creó antes).
            ["Alpha", "American Dad!", "Amélie", "Aliens"],
        )
        self.assertEqual(self.titulos(self.pedir(orden="fecha-asc"))[0], "Alpha")

    def test_el_cursor_sigue_estable_ordenando_por_nota(self):
        # 25 calificaciones con la misma nota: el desempate por id evita que la
        # segunda página repita o saltee.
        for i in range(25):
            produccion = ProduccionAudiovisualFactory(titulo=f"Empate {i}")
            CalificacionFactory(usuario=self.usuario, produccion=produccion, valor=6)

        primera = self.pedir(orden="nota-desc", nota_min=6, nota_max=6)
        segunda = self.api.get(primera["next"]).data

        ids = [item["id"] for item in primera["results"] + segunda["results"]]
        self.assertEqual(len(ids), 25)
        self.assertEqual(len(set(ids)), 25)

    def test_los_filtros_se_combinan(self):
        datos = self.pedir(q="al", clase="movie", texto="con", nota_min=5)

        self.assertEqual(self.titulos(datos), ["Aliens"])

    def test_valores_invalidos_responden_400_con_el_campo(self):
        for params, campo in (
            ({"texto": "quizas"}, "texto"),
            ({"clase": "person"}, "clase"),
            ({"nota_min": 0}, "nota_min"),
            ({"orden": "azar"}, "orden"),
            ({"q": "x" * 101}, "q"),
        ):
            with self.subTest(params):
                respuesta = self.api.get("/api/reviews/mias/", params)
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(respuesta.data["errors"][0]["field"], campo)

    def test_orden_invalido_informa_los_valores_permitidos(self):
        # Igual que la comunidad (C-07): el frontend arma el mensaje con
        # `allowedValues`, no con el texto en inglés.
        respuesta = self.api.get("/api/reviews/mias/", {"orden": "azar"})

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data["errors"][0]["params"],
            {"allowedValues": ["fecha-desc", "fecha-asc", "nota-desc", "nota-asc"]},
        )

    def test_tipo_solo_sigue_siendo_400(self):
        # Medio filtro de ficha es un error a propósito (C-08): un frontend que
        # olvide `id_tmdb` no puede recibir la lista entera.
        respuesta = self.api.get("/api/reviews/mias/", {"tipo": "movie"})

        self.assertEqual(respuesta.status_code, 400)
