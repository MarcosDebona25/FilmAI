"""Los marcadores `[[n]]`: cómo el modelo elige qué títulos llevan tarjeta.

El modelo escribe `[[3]]` en lugar del título; el filtro lo cambia por
`**Título** (año)` mientras el texto sale por SSE y suma la tarjeta.
"""

import json
from unittest.mock import patch

from asgiref.sync import sync_to_async
from django.test import SimpleTestCase

from chatbot.eventos import Texto
from chatbot.llm import ProveedorFalso
from chatbot.marcadores import FiltroDeMarcadores
from chatbot.models import Mensaje, TipoAutor
from chatbot.orquestador import _LARGO_DE_PREAMBULO, responder
from chatbot.prompts import armar_sistema
from chatbot.tests_orquestador import BaseOrquestador, pelicula_de_mentira, tool
from chatbot.tools import ESQUEMAS, FUNCIONES, ContextoTurno
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

    def test_un_marcador_envuelto_en_negrita_no_duplica_la_negrita(self):
        # El 13/11/2026 el modelo escribió `**[[1]] (1999)**` y salió `****Matrix**`.
        casos = {
            "Acá: **[[1]]** va": "Acá: **Moon** (2009) va",
            "Acá: **[[1]] (2009)** va": "Acá: **Moon** (2009) va",
            "Acá: **[[1]]** (2009) va": "Acá: **Moon** (2009) va",
            "Acá: [[1]] (2009) va": "Acá: **Moon** (2009) va",
            "Acá: [[1]] (1999) va": "Acá: **Moon** (2009) va",
        }
        for texto, esperado in casos.items():
            for corte in range(1, len(texto)):
                with self.subTest(texto=texto, corte=corte):
                    self.setUp()
                    salidas = self.pasar(texto[:corte], texto[corte:])
                    self.assertEqual("".join(salidas), esperado)
                    self.assertEqual(self.ids(), [1])

    def test_las_negritas_y_los_anios_normales_pasan_tal_cual(self):
        texto = "**Para empezar**\n* un item (2009) y 1999)\n- **A** (1990) [ok]"
        for corte in range(1, len(texto)):
            with self.subTest(corte=corte):
                self.setUp()
                self.assertEqual(
                    "".join(self.pasar(texto[:corte], texto[corte:])), texto
                )

    def test_un_marcador_invalido_envuelto_en_negrita_se_elimina_entero(self):
        salidas = self.pasar("Mirá **[[9]]** ya")

        self.assertEqual("".join(salidas), "Mirá ya")

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


class BaseMarcadores(BaseOrquestador):
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


class MarcadoresEnElTurnoTests(BaseMarcadores):
    """El filtro conectado al orquestador: lo que sale por SSE y lo que se guarda."""

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


class SinMostrarTarjetasTests(BaseMarcadores):
    """Los marcadores reemplazan a la tool `mostrar_tarjetas` y a la red de #189."""

    def test_la_tool_mostrar_tarjetas_ya_no_existe(self):
        nombres = [esquema["function"]["name"] for esquema in ESQUEMAS]

        self.assertNotIn("mostrar_tarjetas", nombres)
        self.assertNotIn("mostrar_tarjetas", FUNCIONES)

    async def test_un_titulo_en_negrita_sin_marcador_no_arma_tarjeta(self):
        # La red de #189 adivinaba tarjetas desde el texto. Ahora la única forma de
        # mostrar una es el marcador: el texto que el modelo escribe no decide nada.
        eventos = await self.correr(
            [[tool("descubrir")], ["Te recomiendo **Moon** y **Arrival**."]]
        )

        self.assertEqual(eventos[-1].tarjetas, [])

    async def test_el_log_del_turno_dice_que_las_tarjetas_salieron_de_marcadores(self):
        with self.assertLogs("chatbot.orquestador", level="INFO") as log:
            await self.correr([[tool("descubrir")], ["Mirá [[1]] y [[9]]"]])

        linea = next(m for m in log.output if "Turno:" in m)
        self.assertIn("tarjetas=marcadores", linea)
        self.assertIn("marcadores_validos=1", linea)
        self.assertIn("marcadores_invalidos=1", linea)


class PromptDeMarcadoresTests(SimpleTestCase):
    def sistema(self):
        return armar_sistema("", [], "es")

    def test_no_menciona_la_tool_que_ya_no_existe(self):
        self.assertNotIn("mostrar_tarjetas", self.sistema())

    def test_explica_como_usar_el_marcador(self):
        sistema = self.sistema()

        self.assertIn("`ref`", sistema)
        self.assertIn("`[[ref]]`", sistema)
        self.assertIn("en el lugar de su nombre", sistema)
        self.assertIn("como mucho 3", sistema)

    def test_una_referencia_va_con_el_nombre_y_sin_marcador(self):
        sistema = self.sistema()

        self.assertIn("«algo como Arrival»", sistema)
        self.assertIn("sin marcador", sistema)

    def test_nunca_escribe_un_titulo_recomendado_sin_marcador(self):
        sistema = self.sistema()

        self.assertIn("Nunca escribas el nombre de un título que recomendás", sistema)

    def test_pedir_algo_como_x_tambien_se_busca_antes(self):
        self.assertIn("«algo como X»", self.sistema())

    def test_las_secciones_siguen_en_el_mismo_orden(self):
        # El 12/11 mover reglas cambió la conducta del modelo: solo se reemplazan en
        # su lugar las que hablaban de `mostrar_tarjetas`.
        sistema = self.sistema()
        orden = [
            sistema.index(titulo)
            for titulo in (
                "Cómo trabajar:",
                "Títulos vistos:",
                "Al recomendar:",
                "Referencias y datos:",
                "Datos no confiables",
            )
        ]

        self.assertEqual(orden, sorted(orden))

    def test_pedir_las_tarjetas_se_resuelve_con_marcadores(self):
        sistema = self.sistema()

        self.assertIn("«¿y las tarjetas?»", sistema)
        self.assertIn("los títulos de tu última respuesta", sistema)
        self.assertIn("Nunca tomes los de «Ya recomendados»", sistema)


def tarjeta_guardada(id_tmdb, nombre, anio=2009, tipo="movie"):
    """Una tarjeta como queda en `Mensaje.tarjetas`."""
    return {
        "id_tmdb": id_tmdb,
        "tipo": tipo,
        "titulo": nombre,
        "poster": f"/{id_tmdb}.jpg",
        "anio": anio,
    }


class TarjetasDelUltimoMensajeTests(BaseMarcadores):
    """«¿Y las tarjetas?»: las del último mensaje del asistente son candidatas."""

    def charla(self, *tarjetas_por_respuesta):
        for tarjetas in tarjetas_por_respuesta:
            Mensaje.objects.create(
                chat=self.chat, texto="pregunta", autor=TipoAutor.USUARIO
            )
            Mensaje.objects.create(
                chat=self.chat,
                texto="respuesta",
                autor=TipoAutor.CHATBOT,
                tarjetas=tarjetas,
            )

    def sistema_del_primer_pedido(self):
        return self.proveedor.pedidos[0][0]["content"]

    async def test_se_pueden_marcar_sin_volver_a_buscar(self):
        await sync_to_async(self.charla)(
            [
                tarjeta_guardada(10, "Log Horizon", 2013),
                tarjeta_guardada(11, "Btooom!", 2012),
            ]
        )

        eventos = await self.correr(
            [["Acá van [[1]] y [[2]]."]], texto="¿y las tarjetas?"
        )

        self.assertEqual(
            eventos[-1].texto, "Acá van **Log Horizon** (2013) y **Btooom!** (2012)."
        )
        self.assertEqual([t["id_tmdb"] for t in eventos[-1].tarjetas], [10, 11])
        self.assertEqual(len(self.proveedor.pedidos), 1)

    async def test_el_modelo_las_ve_numeradas_en_el_sistema(self):
        await sync_to_async(self.charla)([tarjeta_guardada(10, "Log Horizon", 2013)])

        await self.correr([["Hola"]])

        self.assertIn(
            "Tarjetas de tu último mensaje: [[1]] Log Horizon (2013)",
            self.sistema_del_primer_pedido(),
        )

    async def test_sin_tarjetas_el_sistema_lo_dice(self):
        await self.correr([["Hola"]])

        self.assertIn(
            "Tarjetas de tu último mensaje: ninguna", self.sistema_del_primer_pedido()
        )

    async def test_solo_cuenta_el_ultimo_mensaje_del_asistente(self):
        await sync_to_async(self.charla)(
            [tarjeta_guardada(10, "Vieja")], [tarjeta_guardada(11, "Nueva")]
        )

        await self.correr([["Hola"]])

        sistema = self.sistema_del_primer_pedido()
        self.assertIn("[[1]] Nueva", sistema)
        self.assertNotIn("Vieja", sistema)

    async def test_los_refs_de_las_busquedas_siguen_despues_de_las_del_mensaje(self):
        await sync_to_async(self.charla)([tarjeta_guardada(10, "Log Horizon")])

        await self.correr([[tool("descubrir")], ["Listo"]])

        resultado = json.loads(self.proveedor.pedidos[1][-1]["content"])
        self.assertEqual([r["ref"] for r in resultado["resultados"]], [2, 3, 4, 5])

    async def test_una_tarjeta_guardada_sin_nota_sale_con_nota_null(self):
        await sync_to_async(self.charla)([tarjeta_guardada(10, "Vieja")])

        eventos = await self.correr([["Va [[1]]"]], texto="¿y las tarjetas?")

        self.assertIsNone(eventos[-1].tarjetas[0]["nota_tmdb"])

    async def test_una_tarjeta_vieja_mal_formada_se_ignora(self):
        await sync_to_async(self.charla)(
            [{"titulo": "Sin id"}, tarjeta_guardada(10, "Bien")]
        )

        await self.correr([["Hola"]])

        self.assertIn("[[1]] Bien", self.sistema_del_primer_pedido())

    async def test_las_tarjetas_recortadas_no_son_candidatas(self):
        # El recorte de #180 deja las tarjetas de más de 180 días como
        # `{id_tmdb, tipo}`: sin título no se pueden nombrar, así que no entran
        # como candidatas y el turno sigue sin romperse.
        await sync_to_async(self.charla)([{"id_tmdb": 10, "tipo": "movie"}])

        await self.correr([["Hola"]])

        self.assertIn(
            "Tarjetas de tu último mensaje: ninguna", self.sistema_del_primer_pedido()
        )

    async def test_el_mismo_titulo_en_una_busqueda_conserva_el_ref_del_mensaje(self):
        await sync_to_async(self.charla)([tarjeta_guardada(1, "Moon", 2009)])

        await self.correr([[tool("descubrir")], ["Listo"]])

        resultado = json.loads(self.proveedor.pedidos[1][-1]["content"])
        self.assertEqual(resultado["resultados"][0]["ref"], 1)

    def test_el_prompt_manda_a_marcar_las_tarjetas_del_ultimo_mensaje(self):
        sistema = armar_sistema("", [], "es")

        self.assertIn("«Tarjetas de tu último mensaje»", sistema)
        self.assertIn("sin buscar de nuevo", sistema)


class ReintentoForzadoTests(BaseMarcadores):
    """Si recomienda sin haber buscado, se repite la llamada obligándolo a buscar."""

    async def test_un_marcador_sin_candidatos_repite_con_tool_choice_required(self):
        eventos = await self.correr(
            [["Intento [[9]]"], [tool("descubrir")], ["Mirá [[2]]"]]
        )

        self.assertEqual(self.proveedor.tool_choices, [None, "required", None])
        self.assertEqual(eventos[-1].texto, "Mirá **Arrival** (2016)")
        self.assertEqual([t["id_tmdb"] for t in eventos[-1].tarjetas], [2])

    async def test_un_titulo_en_negrita_sin_buscar_tambien_repite(self):
        eventos = await self.correr(
            [["Te recomiendo **Moon**."], [tool("descubrir")], ["Mirá [[1]]"]]
        )

        self.assertEqual(self.proveedor.tool_choices, [None, "required", None])
        self.assertEqual(eventos[-1].texto, "Mirá **Moon** (2009)")

    async def test_el_primer_intento_descartado_nunca_llega_al_usuario(self):
        eventos = await self.correr(
            [["Intento [[9]] fallido"], [tool("descubrir")], ["Mirá [[2]]"]]
        )

        self.assertEqual("".join(self.deltas(eventos)), "Mirá **Arrival** (2016)")

    async def test_el_primer_intento_no_queda_en_lo_que_ve_el_modelo(self):
        await self.correr([["Intento [[9]]"], [tool("descubrir")], ["Mirá [[2]]"]])

        contenidos = [m.get("content") for m in self.proveedor.pedidos[1]]
        self.assertNotIn("Intento [[9]]", contenidos)

    async def test_una_respuesta_que_no_recomienda_no_reintenta(self):
        eventos = await self.correr([["Hola, ¿en qué te ayudo?"]])

        self.assertEqual(self.proveedor.tool_choices, [None])
        self.assertEqual(eventos[-1].texto, "Hola, ¿en qué te ayudo?")

    async def test_si_busco_primero_no_hay_reintento(self):
        await self.correr([[tool("descubrir")], ["Mirá [[2]]"]])

        self.assertEqual(self.proveedor.tool_choices, [None, None])

    async def test_los_marcadores_de_las_tarjetas_previas_no_cuentan_como_recomendar_sin_buscar(
        self,
    ):
        await sync_to_async(Mensaje.objects.create)(
            chat=self.chat,
            texto="x",
            autor=TipoAutor.CHATBOT,
            tarjetas=[tarjeta_guardada(10, "Log Horizon")],
        )

        await self.correr([["Acá va [[1]]"]])

        self.assertEqual(self.proveedor.tool_choices, [None])

    async def test_es_un_solo_reintento(self):
        # Si el segundo intento tampoco busca, se muestra lo que escribió, limpio.
        eventos = await self.correr([["Uno [[9]]"], ["Dos [[8]]"]])

        self.assertEqual(self.proveedor.tool_choices, [None, "required"])
        self.assertEqual(eventos[-1].texto, "Dos")

    async def test_si_el_reintento_falla_se_muestra_el_primer_intento(self):
        eventos = await self.correr([["Primero [[9]] ok"], [RuntimeError("503")]])

        self.assertEqual(eventos[-1].texto, "Primero ok")

    async def test_sin_tiempo_no_reintenta(self):
        # Ya pasó la mitad del presupuesto del turno: otra llamada no entraría.
        with patch("chatbot.orquestador._ahora", side_effect=[0, 100, 100, 100]):
            eventos = await self.correr([["Uno [[9]]"]])

        self.assertEqual(self.proveedor.tool_choices, [None])
        self.assertEqual(eventos[-1].texto, "Uno")

    async def test_la_primera_vuelta_sin_tools_sale_recien_al_terminar(self):
        # Se retiene entera para poder descartarla: el texto sale después del último
        # trozo del modelo, no mientras llega.
        # El primer trozo ya pasa el umbral del preámbulo: sin retención saldría solo.
        largo = "x" * (_LARGO_DE_PREAMBULO + 1)
        self.proveedor = ProveedorFalso([[largo, "y"]])
        generador = responder(self.chat, "hola", "es", proveedor=self.proveedor)

        primero = await anext(generador)

        self.assertEqual(self.proveedor.entregados, 2)
        self.assertEqual(primero, Texto(largo))
        await generador.aclose()

    async def test_el_log_cuenta_el_reintento(self):
        with self.assertLogs("chatbot.orquestador", level="INFO") as log:
            await self.correr([["Uno [[9]]"], [tool("descubrir")], ["Mirá [[2]]"]])

        linea = next(m for m in log.output if "Turno:" in m)
        self.assertIn("reintento_forzado=si", linea)

    async def test_el_log_sin_reintento(self):
        with self.assertLogs("chatbot.orquestador", level="INFO") as log:
            await self.correr([["Hola"]])

        self.assertIn(
            "reintento_forzado=no", next(m for m in log.output if "Turno:" in m)
        )
