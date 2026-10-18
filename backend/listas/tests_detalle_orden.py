"""Detalle de lista, filtros de sus ítems y orden de las listas (L-02/L-03, 15/10/2026).

El contrato sale del canvas «Lists» y «List detail»: `GET /api/lists/{id}/`,
la nota de TMDB en cada ítem, búsqueda, tipo, tramo de nota y orden en
`GET /api/lists/{id}/items/`, y `PUT /api/lists/order/` para reordenar.
"""

from datetime import UTC, datetime, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.factories import ProduccionAudiovisualFactory
from catalogo.models import ProduccionTraduccion, TipoProduccion
from listas.factories import ListaFactory
from listas.models import Lista, Tiene, TipoLista
from usuarios.factories import UsuarioFactory

_BASE = datetime(2026, 10, 1, tzinfo=UTC)


class _ConUsuario(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory(idioma="en")
        self.api = APIClient()
        self.api.force_authenticate(self.usuario)


class DetalleDeListaTests(_ConUsuario):
    def test_devuelve_el_resumen_de_una_lista_propia(self):
        lista = ListaFactory(usuario=self.usuario, nombre="Sci Fi")
        Tiene.objects.create(
            lista=lista,
            produccion=ProduccionAudiovisualFactory(
                tipo=TipoProduccion.SERIE, poster="/a.jpg"
            ),
        )

        respuesta = self.api.get(f"/api/lists/{lista.pk}/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["nombre"], "Sci Fi")
        self.assertEqual(respuesta.data["tipo"], TipoLista.PERSONALIZADA)
        self.assertEqual(
            (respuesta.data["cantidad_items"], respuesta.data["cantidad_series"]),
            (1, 1),
        )
        self.assertEqual(respuesta.data["preview_posters"], ["/a.jpg"])

    def test_tambien_sirve_las_predeterminadas(self):
        # La miga «Lists > Favorites» de la ficha lo pide para cualquier lista.
        favoritos = self.usuario.listas.get(clave="favoritos")

        respuesta = self.api.get(f"/api/lists/{favoritos.pk}/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["clave"], "favoritos")

    def test_la_lista_de_otra_persona_es_404(self):
        ajena = ListaFactory()

        respuesta = self.api.get(f"/api/lists/{ajena.pk}/")

        self.assertEqual(respuesta.status_code, 404)

    def test_requiere_sesion(self):
        lista = ListaFactory(usuario=self.usuario)

        self.assertEqual(APIClient().get(f"/api/lists/{lista.pk}/").status_code, 401)


class ItemsDeListaTests(_ConUsuario):
    def setUp(self):
        super().setUp()
        self.lista = ListaFactory(usuario=self.usuario, nombre="Mezcla")
        self.dia = 0

        def agregar(titulo, tipo, nota):
            produccion = ProduccionAudiovisualFactory(
                titulo=titulo, tipo=tipo, calificacion_promedio=nota
            )
            item = Tiene.objects.create(lista=self.lista, produccion=produccion)
            # `fecha_agregado` es `auto_now_add`: se fija después con un update.
            self.dia += 1
            Tiene.objects.filter(pk=item.pk).update(
                fecha_agregado=_BASE + timedelta(days=self.dia)
            )
            return produccion

        self.amelie = agregar("Amélie", TipoProduccion.PELICULA, 7.9)
        agregar("Interstellar", TipoProduccion.PELICULA, 8.456)
        agregar("Dark", TipoProduccion.SERIE, 8.4)
        agregar("Bad Movie", TipoProduccion.PELICULA, 3.2)
        agregar("Brand New", TipoProduccion.PELICULA, 0)
        agregar("No Data", TipoProduccion.SERIE, None)
        # En otra lista: nunca aparece.
        Tiene.objects.create(
            lista=ListaFactory(usuario=self.usuario),
            produccion=ProduccionAudiovisualFactory(titulo="Amélie 2"),
        )

    def pedir(self, **params):
        respuesta = self.api.get(f"/api/lists/{self.lista.pk}/items/", params)
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        return respuesta.data

    def titulos(self, datos):
        return [item["titulo"] for item in datos["results"]]

    def test_sin_filtros_trae_lo_mas_reciente_primero_con_el_total(self):
        datos = self.pedir()

        self.assertEqual(
            self.titulos(datos),
            ["No Data", "Brand New", "Bad Movie", "Dark", "Interstellar", "Amélie"],
        )
        self.assertEqual(datos["total"], 6)

    def test_cada_item_trae_la_nota_de_tmdb_y_null_si_no_tiene(self):
        notas = {
            item["titulo"]: item["calificacion_promedio"]
            for item in self.pedir()["results"]
        }

        self.assertEqual(notas["Interstellar"], 8.456)
        # TMDB manda 0 cuando no hay votos: para la UI es «Unrated».
        self.assertIsNone(notas["Brand New"])
        self.assertIsNone(notas["No Data"])

    def test_cada_item_trae_la_fecha_en_que_se_agrego_a_la_lista(self):
        fechas = {
            item["titulo"]: item["fecha_agregado"] for item in self.pedir()["results"]
        }

        # CU-009: la UI la muestra discreta en cada tarjeta del detalle.
        self.assertEqual(
            datetime.fromisoformat(fechas["Amélie"]), _BASE + timedelta(days=1)
        )
        self.assertEqual(len(set(fechas.values())), 6)

    def test_la_busqueda_ignora_mayusculas_y_acentos_y_mira_traducciones(self):
        self.assertEqual(self.titulos(self.pedir(q="  AMELIE ")), ["Amélie"])
        ProduccionTraduccion.objects.create(
            produccion=self.amelie, idioma="es", titulo="El fabuloso destino"
        )
        self.assertEqual(self.titulos(self.pedir(q="fabuloso")), ["Amélie"])

    def test_el_total_cuenta_lo_filtrado(self):
        self.assertEqual(self.pedir(clase="tv")["total"], 2)

    def test_por_tipo(self):
        self.assertEqual(self.titulos(self.pedir(clase="tv")), ["No Data", "Dark"])

    def test_por_tramo_de_nota_sin_contar_los_titulos_sin_nota(self):
        self.assertEqual(self.titulos(self.pedir(nota="8+")), ["Dark", "Interstellar"])
        # «Below 5» no incluye lo que TMDB todavía no calificó (15/10/2026).
        self.assertEqual(self.titulos(self.pedir(nota="m5")), ["Bad Movie"])

    def test_los_filtros_se_combinan(self):
        self.assertEqual(
            self.titulos(self.pedir(clase="movie", nota="7+", q="a")),
            ["Interstellar", "Amélie"],
        )

    def test_primero_lo_agregado_antes(self):
        self.assertEqual(self.titulos(self.pedir(orden="agregado-asc"))[0], "Amélie")

    def test_por_nota_los_sin_nota_quedan_al_final_en_los_dos_sentidos(self):
        mejores = self.titulos(self.pedir(orden="nota-desc"))
        peores = self.titulos(self.pedir(orden="nota-asc"))

        # Interstellar (8.456) va antes que Dark (8.4): cuentan los decimales.
        self.assertEqual(mejores[:4], ["Interstellar", "Dark", "Amélie", "Bad Movie"])
        self.assertEqual(peores[:4], ["Bad Movie", "Amélie", "Dark", "Interstellar"])
        self.assertEqual(set(mejores[4:]), {"Brand New", "No Data"})
        self.assertEqual(set(peores[4:]), {"Brand New", "No Data"})

    def test_por_titulo_sin_acentos_ni_mayusculas(self):
        self.assertEqual(
            self.titulos(self.pedir(orden="titulo-asc")),
            ["Amélie", "Bad Movie", "Brand New", "Dark", "Interstellar", "No Data"],
        )

    def test_por_titulo_usa_el_titulo_que_se_ve_en_el_idioma(self):
        self.usuario.idioma = "es"
        self.usuario.save(update_fields=["idioma"])
        ProduccionTraduccion.objects.create(
            produccion=self.amelie, idioma="es", titulo="Zelig"
        )

        titulos = self.titulos(self.pedir(orden="titulo-asc"))

        self.assertEqual(titulos[-1], "Zelig")

    def test_el_cursor_no_repite_ni_saltea_con_empates(self):
        # 25 títulos con la misma nota y el mismo nombre: con páginas de 20, la
        # segunda depende de desempatar por el id del ítem.
        for _ in range(25):
            Tiene.objects.create(
                lista=self.lista,
                produccion=ProduccionAudiovisualFactory(
                    titulo="Empate", calificacion_promedio=6.5
                ),
            )
        for orden in ("nota-desc", "nota-asc", "titulo-asc"):
            with self.subTest(orden=orden):
                vistos = []
                datos = self.pedir(orden=orden)
                vistos += [item["item_id"] for item in datos["results"]]
                while datos["next"]:
                    datos = self.api.get(datos["next"]).data
                    vistos += [item["item_id"] for item in datos["results"]]

                self.assertEqual(len(vistos), 31)
                self.assertEqual(len(set(vistos)), 31)

    def test_valores_invalidos_responden_400_con_el_campo(self):
        for params, campo in (
            ({"clase": "person"}, "clase"),
            ({"nota": "10+"}, "nota"),
            ({"orden": "azar"}, "orden"),
            ({"q": "x" * 101}, "q"),
        ):
            with self.subTest(params):
                respuesta = self.api.get(f"/api/lists/{self.lista.pk}/items/", params)
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(respuesta.data["errors"][0]["field"], campo)


class OrdenDeListasTests(_ConUsuario):
    URL = "/api/lists/order/"

    def crear(self, nombre):
        respuesta = self.api.post("/api/lists/", {"nombre": nombre}, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        return respuesta.data["id"]

    def nombres(self):
        return [lista["nombre"] for lista in self.api.get("/api/lists/").data]

    def test_las_nuevas_van_al_final(self):
        self.crear("Uno")
        self.crear("Dos")

        self.assertEqual(self.nombres()[3:], ["Uno", "Dos"])

    def test_reordena_las_personalizadas_y_las_predeterminadas_quedan_adelante(self):
        uno, dos, tres = self.crear("Uno"), self.crear("Dos"), self.crear("Tres")

        respuesta = self.api.put(self.URL, {"ids": [tres, uno, dos]}, format="json")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            [lista["nombre"] for lista in respuesta.data][3:], ["Tres", "Uno", "Dos"]
        )
        self.assertEqual(
            [lista["clave"] for lista in respuesta.data][:3],
            ["favoritos", "pendientes", "vistas"],
        )
        self.assertEqual(self.nombres()[3:], ["Tres", "Uno", "Dos"])
        # Una lista creada después sigue entrando al final.
        self.crear("Cuatro")
        self.assertEqual(self.nombres()[-1], "Cuatro")

    def test_las_que_faltan_quedan_al_final_y_los_ids_ajenos_se_ignoran(self):
        # Otra pestaña pudo crear o borrar listas mientras tanto.
        self.crear("Uno")
        self.crear("Dos")
        tres = self.crear("Tres")
        ajena = ListaFactory()
        predeterminada = self.usuario.listas.get(clave="favoritos")

        respuesta = self.api.put(
            self.URL,
            {"ids": [ajena.pk, tres, 999_999, predeterminada.pk]},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.nombres()[3:], ["Tres", "Uno", "Dos"])
        self.assertEqual(Lista.objects.get(pk=ajena.pk).orden, ajena.orden)

    def test_ids_repetidos_o_invalidos_son_400(self):
        uno = self.crear("Uno")
        for cuerpo in ({"ids": [uno, uno]}, {"ids": ["x"]}, {"ids": [0]}, {}):
            with self.subTest(cuerpo=cuerpo):
                respuesta = self.api.put(self.URL, cuerpo, format="json")
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(respuesta.data["errors"][0]["field"], "ids")

    def test_requiere_sesion(self):
        respuesta = APIClient().put(self.URL, {"ids": []}, format="json")

        self.assertEqual(respuesta.status_code, 401)
