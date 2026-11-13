"""Los marcadores `[[n]]`: cómo el modelo elige qué títulos llevan tarjeta.

El modelo escribe `[[3]]` en lugar del título; el filtro lo cambia por
`**Título** (año)` mientras el texto sale por SSE y suma la tarjeta.
"""

import json
from unittest.mock import patch

from django.test import SimpleTestCase

from chatbot.eventos import Texto
from chatbot.marcadores import FiltroDeMarcadores
from chatbot.tests_orquestador import BaseOrquestador, pelicula_de_mentira, tool
from chatbot.tools import FUNCIONES, ContextoTurno
from chatbot.tools.turno import publicar


def titulo_de(id_tmdb, nombre, anio=2009, tipo="movie"):
    return {
        "id_tmdb": id_tmdb,
        "tipo": tipo,
        "titulo": nombre,
        "poster": f"/{id_tmdb}.jpg",
        "anio": anio,
        "nota_tmdb": 7.0,
    }


def contexto_con(*titulos):
    ctx = ContextoTurno(usuario=None, idioma="es", vistas=set())
    for titulo in titulos:
        ctx.encontrados[(titulo["id_tmdb"], titulo["tipo"])] = titulo
    return ctx


class FiltroDeMarcadoresTests(SimpleTestCase):
    def setUp(self):
        self.ctx = contexto_con(
            titulo_de(1, "Moon"),
            titulo_de(2, "Arrival", 2016),
            titulo_de(3, "Her", 2013),
            titulo_de(4, "Solaris", 1972),
        )
        self.filtro = FiltroDeMarcadores(self.ctx)

    def pasar(self, *trozos):
        """Alimenta los trozos y devuelve lo que salió tras cada uno, más el cierre."""
        salidas = [self.filtro.alimentar(trozo) for trozo in trozos]
        return [*salidas, self.filtro.cerrar()]

    def ids(self):
        return [t["id_tmdb"] for t in self.ctx.tarjetas]

    def test_un_marcador_se_cambia_por_titulo_en_negrita_y_anio(self):
        salidas = self.pasar("Te recomiendo [[2]] por su guion.")

        self.assertEqual(
            "".join(salidas), "Te recomiendo **Arrival** (2016) por su guion."
        )
        self.assertEqual(self.ids(), [2])
        self.assertEqual(self.filtro.validos, 1)

    def test_la_tarjeta_es_la_que_anoto_la_busqueda(self):
        self.pasar("[[1]]")

        self.assertEqual(self.ctx.tarjetas, [titulo_de(1, "Moon")])

    def test_un_titulo_sin_anio_no_lleva_parentesis(self):
        ctx = contexto_con(titulo_de(1, "Moon", anio=None))

        texto = "".join(self._pasar_en(ctx, "Mirá [[1]]"))

        self.assertEqual(texto, "Mirá **Moon**")

    @staticmethod
    def _pasar_en(ctx, *trozos):
        filtro = FiltroDeMarcadores(ctx)
        return [*(filtro.alimentar(t) for t in trozos), filtro.cerrar()]

    def test_un_marcador_partido_entre_dos_trozos_se_arma_igual(self):
        salidas = self.pasar("Mirá [[", "3]] que es linda")

        self.assertEqual("".join(salidas), "Mirá **Her** (2013) que es linda")
        self.assertEqual(self.ids(), [3])

    def test_nunca_sale_a_medias_un_marcador(self):
        # Parte el texto en cada posición posible: ningún trozo de salida puede
        # llevar un corchete, ni siquiera cuando el marcador queda cortado.
        texto = "Mirá [[3]] y [[1]]."
        for corte in range(1, len(texto)):
            with self.subTest(corte=corte):
                self.setUp()
                salidas = self.pasar(texto[:corte], texto[corte:])
                self.assertEqual(
                    "".join(salidas), "Mirá **Her** (2013) y **Moon** (2009)."
                )
                self.assertFalse(any("[" in s for s in salidas))

    def test_un_marcador_que_no_corresponde_a_nadie_se_elimina_sin_dejar_hueco(self):
        salidas = self.pasar("Mirá [[9]].")

        self.assertEqual("".join(salidas), "Mirá.")
        self.assertEqual(self.ids(), [])
        self.assertEqual(self.filtro.invalidos, 1)

    def test_un_marcador_invalido_se_loguea_sin_el_texto_del_usuario(self):
        with self.assertLogs("chatbot.marcadores", level="WARNING") as log:
            self.pasar("Mirá [[9]]")

        self.assertIn("9", log.output[0])

    def test_un_marcador_repetido_repite_el_titulo_pero_no_la_tarjeta(self):
        salidas = self.pasar("[[1]] es buena. Insisto con [[1]].")

        self.assertEqual(
            "".join(salidas),
            "**Moon** (2009) es buena. Insisto con **Moon** (2009).",
        )
        self.assertEqual(self.ids(), [1])

    def test_las_tarjetas_van_en_orden_de_aparicion(self):
        self.pasar("[[3]], luego [[1]] y [[2]]")

        self.assertEqual(self.ids(), [3, 1, 2])

    def test_por_encima_del_tope_el_titulo_va_en_el_texto_sin_tarjeta(self):
        salidas = self.pasar("[[1]], [[2]], [[3]] y [[4]]")

        self.assertIn("**Solaris** (1972)", "".join(salidas))
        self.assertEqual(self.ids(), [1, 2, 3])

    def test_los_corchetes_normales_no_son_marcadores(self):
        texto = "Ojo [spoiler] y [[nota]] o [1] o [[1 o ]] sueltos."
        salidas = self.pasar(texto[:10], texto[10:])

        self.assertEqual("".join(salidas), texto)
        self.assertEqual(self.ids(), [])

    def test_un_corchete_suelto_al_final_se_entrega_al_cerrar(self):
        salidas = self.pasar("Mirá [")

        self.assertEqual(salidas[0], "Mirá")
        self.assertEqual("".join(salidas), "Mirá [")

    def test_un_marcador_sin_cerrar_al_final_se_descarta(self):
        # El modelo se quedó sin tokens a mitad del marcador.
        salidas = self.pasar("Mirá [[3")

        self.assertEqual("".join(salidas), "Mirá")

    def test_un_numero_enorme_no_es_un_marcador_ni_rompe(self):
        salidas = self.pasar("Mirá [[99999999999999999999]]")

        self.assertEqual("".join(salidas), "Mirá [[99999999999999999999]]")

    def test_cuenta_las_negritas_que_escribio_el_modelo(self):
        self.pasar("Te recomiendo **Moon** y [[2]].")

        self.assertEqual(self.filtro.negritas, 1)

    def test_el_mismo_id_de_pelicula_y_serie_son_dos_marcadores_distintos(self):
        ctx = contexto_con(
            titulo_de(5, "Fargo", 1996, "movie"), titulo_de(5, "Fargo", 2014, "tv")
        )

        texto = "".join(self._pasar_en(ctx, "[[2]] y [[1]]"))

        self.assertEqual(texto, "**Fargo** (2014) y **Fargo** (1996)")
        self.assertEqual([t["tipo"] for t in ctx.tarjetas], ["tv", "movie"])


class MarcadoresEnElTurnoTests(BaseOrquestador):
    """El filtro conectado al orquestador: lo que sale por SSE y lo que se guarda."""

    def setUp(self):
        super().setUp()
        self.peliculas = [
            pelicula_de_mentira(1, "Moon"),
            pelicula_de_mentira(2, "Arrival", 2016),
            pelicula_de_mentira(3, "Her", 2013),
            pelicula_de_mentira(4, "Solaris", 1972),
        ]
        parche = patch.dict(
            FUNCIONES,
            {
                "descubrir": lambda ctx, **_: {
                    "resultados": publicar(ctx, self.peliculas)
                }
            },
        )
        parche.start()
        self.addCleanup(parche.stop)

    @staticmethod
    def deltas(eventos):
        return [e.delta for e in eventos if isinstance(e, Texto)]

    async def test_el_marcador_sale_como_titulo_y_suma_la_tarjeta(self):
        eventos = await self.correr(
            [[tool("descubrir")], ["Te recomiendo [[2]] y [[1]]."]]
        )

        esperado = "Te recomiendo **Arrival** (2016) y **Moon** (2009)."
        self.assertEqual("".join(self.deltas(eventos)), esperado)
        self.assertEqual(eventos[-1].texto, esperado)
        self.assertEqual([t["id_tmdb"] for t in eventos[-1].tarjetas], [2, 1])

    async def test_el_modelo_ve_el_ref_de_cada_titulo(self):
        await self.correr([[tool("descubrir")], ["Listo"]])

        resultado = json.loads(self.proveedor.pedidos[1][-1]["content"])
        self.assertEqual(
            [(r["ref"], r["titulo"]) for r in resultado["resultados"]],
            [(1, "Moon"), (2, "Arrival"), (3, "Her"), (4, "Solaris")],
        )

    async def test_un_marcador_partido_entre_dos_chunks_nunca_se_ve_a_medias(self):
        eventos = await self.correr([[tool("descubrir")], ["Mirá [[", "3]] ya"]])

        self.assertEqual(eventos[-1].texto, "Mirá **Her** (2013) ya")
        self.assertFalse(any("[" in d for d in self.deltas(eventos)))
        self.assertEqual([t["id_tmdb"] for t in eventos[-1].tarjetas], [3])

    async def test_un_marcador_invalido_se_elimina_y_se_loguea(self):
        with self.assertLogs("chatbot.marcadores", level="WARNING"):
            eventos = await self.correr([[tool("descubrir")], ["Mirá [[9]]."]])

        self.assertEqual(eventos[-1].texto, "Mirá.")
        self.assertEqual(eventos[-1].tarjetas, [])

    async def test_un_marcador_repetido_no_duplica_la_tarjeta(self):
        eventos = await self.correr([[tool("descubrir")], ["[[1]] y de nuevo [[1]]"]])

        self.assertEqual(len(eventos[-1].tarjetas), 1)

    async def test_los_corchetes_normales_pasan_tal_cual(self):
        eventos = await self.correr(
            [[tool("descubrir")], ["Ojo [spoiler] y [[nota]] al final ["]]
        )

        self.assertEqual(eventos[-1].texto, "Ojo [spoiler] y [[nota]] al final [")

    async def test_el_modelo_ve_su_propio_texto_con_el_marcador(self):
        # Lo que se le devuelve al modelo es lo que él escribió, no lo reemplazado.
        await self.correr(
            [[tool("descubrir")], ["Mirá [[1]]", tool("descubrir", "2")], ["Listo"]]
        )

        self.assertEqual(self.proveedor.pedidos[2][-2]["content"], "Mirá [[1]]")

    async def test_en_la_ultima_llamada_sin_tools_tambien_se_reemplazan(self):
        pedidos = [[tool("descubrir", str(i))] for i in range(5)]
        eventos = await self.correr([*pedidos, ["Te dejo [[1]]"]])

        self.assertEqual(eventos[-1].texto, "Te dejo **Moon** (2009)")
        self.assertEqual(len(eventos[-1].tarjetas), 1)
