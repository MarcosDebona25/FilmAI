"""El plazo del turno: el orquestador reparte los 25 s y cierra a tiempo (H3).

Ningún test duerme de verdad. El tiempo es simulado con dos piezas:

- `RelojFalso` reemplaza a `orquestador._ahora`: la hora es un número que el test
  mueve. Un paso `reloj.pasan(4)` dentro del guion del proveedor quiere decir «acá
  el modelo tardó 4 segundos».
- `CorteFalso` reemplaza a `plazo.Corte` (el que de verdad usa `asyncio.timeout`):
  anota cuántos segundos le dieron y, si el reloj falso pasa de ese límite, lanza
  `TimeoutError` en ese punto, que es lo que vería el código real.

El `Corte` real se prueba aparte, al final, con un límite de 0 segundos.
"""

import asyncio
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from catalogo import plazo as plazo_de_red
from chatbot import orquestador
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.llm import ProveedorFalso
from chatbot.orquestador import _LARGO_DE_PREAMBULO, responder
from chatbot.plazo import Corte, Plazo, recorrer
from chatbot.tests_orquestador import BaseOrquestador, tool
from chatbot.tools import FUNCIONES
from chatbot.views import tope_de_la_vista

LARGO = "x" * (_LARGO_DE_PREAMBULO + 1)


class RelojFalso:
    """Un reloj que solo avanza cuando el test lo dice."""

    def __init__(self):
        self.ahora = 0.0
        # El corte que está abierto en este momento (ver `CorteFalso`), si hay uno.
        self.corte = None
        # Los segundos que recibió cada corte, en orden: es lo que se «repartió».
        self.cortes = []

    def __call__(self):
        # Así el objeto se puede llamar como una función: `reloj()`.
        return self.ahora

    def avanzar(self, segundos):
        """Hace pasar el tiempo. Si en el camino vence el corte abierto, corta ahí."""
        destino = self.ahora + segundos
        if self.corte is not None and destino >= self.corte.vence:
            self.ahora = self.corte.vence
            self.corte.vencido = True
            raise TimeoutError
        self.ahora = destino

    def pasan(self, segundos):
        """Un paso para el guion de `ProveedorFalso`: el modelo tarda `segundos`."""

        async def paso():
            self.avanzar(segundos)

        return paso


class CorteFalso:
    """Lo mismo que `plazo.Corte`, pero contra el `RelojFalso`."""

    def __init__(self, reloj, segundos):
        self.reloj = reloj
        self.vence = reloj.ahora + segundos
        self.vencido = False
        reloj.cortes.append(segundos)

    async def esperar(self, cosa):
        # Mientras dura la espera, este es el corte que el reloj puede hacer vencer.
        self.reloj.corte = self
        try:
            return await cosa
        finally:
            self.reloj.corte = None

    def correr_hasta(self, segundos):
        self.vence = self.reloj.ahora + segundos

    def vencio(self):
        return self.vencido


@override_settings(LLM_TIMEOUT_SECONDS=25)
class BasePlazo(BaseOrquestador):
    """Con 25 s de plazo: 7,5 s de reserva para cerrar y 10 s para otra vuelta."""

    def setUp(self):
        super().setUp()
        self.reloj = RelojFalso()
        for parche in (
            patch("chatbot.orquestador._ahora", self.reloj),
            patch("chatbot.plazo.Corte", lambda s: CorteFalso(self.reloj, s)),
        ):
            parche.start()
            self.addCleanup(parche.stop)

    async def linea(self, guion):
        with self.assertLogs("chatbot.orquestador", level="INFO") as log:
            self.eventos = await self.correr(guion)
        return next(m for m in log.output if "Turno:" in m)


class RepartoDelTiempoTests(BasePlazo):
    async def test_cada_llamada_y_cada_busqueda_recibe_lo_que_queda(self):
        pasan = self.reloj.pasan
        await self.correr([[pasan(4), tool("descubrir")], [pasan(3), "Mirá [[1]]"]])

        # 1.ª llamada: 25 - 7,5 de reserva. Tools y 2.ª llamada: ya pasaron 4 s.
        self.assertEqual(self.reloj.cortes, [17.5, 13.5, 13.5])

    async def test_las_tools_saben_cuanto_tiempo_tienen_y_usan_el_tmdb_corto(self):
        visto = {}

        def espiar(ctx, **argumentos):
            # Corre en el hilo de las tools: ahí tiene que verse el plazo de red.
            visto["queda"] = plazo_de_red.que_queda()
            visto["tmdb"] = plazo_de_red.para_tmdb()
            return {"resultados": []}

        with (
            patch.dict(FUNCIONES, {"descubrir": espiar}),
            override_settings(CHAT_TMDB_TIMEOUT=3, CHAT_TMDB_REINTENTOS=1),
        ):
            await self.correr(
                [[self.reloj.pasan(4), tool("descubrir")], ["No encontré nada."]]
            )

        # Este reloj es el de verdad (`time.monotonic`): de 13,5 s pasó un instante.
        self.assertAlmostEqual(visto["queda"], 13.5, delta=1)
        self.assertEqual(visto["tmdb"].timeout, 3)
        self.assertEqual(visto["tmdb"].reintentos, 1)

    async def test_fuera_de_las_tools_no_hay_plazo_de_red(self):
        await self.correr([[tool("descubrir")], ["Listo."]])

        self.assertIsNone(plazo_de_red.que_queda())

    async def test_las_sagas_no_esperan_mas_de_lo_que_queda(self):
        def dos_titulos(ctx, **argumentos):
            for id_tmdb, nombre in ((1, "Moon"), (2, "Solaris")):
                ctx.encontrados[(id_tmdb, "movie")] = {
                    "id_tmdb": id_tmdb,
                    "tipo": "movie",
                    "titulo": nombre,
                    "poster": None,
                    "anio": 2009,
                }
            return {"resultados": [{"id_tmdb": 1}, {"id_tmdb": 2}]}

        with (
            patch.dict(FUNCIONES, {"descubrir": dos_titulos}),
            patch(
                "chatbot.orquestador.una_parte_por_saga",
                wraps=orquestador.una_parte_por_saga,
            ) as sagas,
        ):
            await self.correr(
                [
                    [self.reloj.pasan(9), tool("descubrir")],
                    ["Mirá ", self.reloj.pasan(15), "[[1]] y [[2]]"],
                ]
            )

        # Pasaron 24 s: queda 1 s, menos que los 2 s que las sagas esperan siempre.
        self.assertEqual(sagas.call_args.kwargs["presupuesto"], 1.0)


class CerrarConLoQueHayTests(BasePlazo):
    async def test_sin_tiempo_para_otra_vuelta_responde_con_lo_que_encontro(self):
        pasan = self.reloj.pasan
        linea = await self.linea(
            [
                [pasan(8), tool("descubrir")],
                [pasan(8), tool("descubrir")],
                ["Con lo que hay: [[1]]"],
            ]
        )

        # Pasaron 16 s y quedan 9: no alcanza para otra vuelta con tools (10 s).
        # La tercera llamada va sin tools y con el aviso de que ya no puede buscar.
        self.assertTrue(all(self.proveedor.esquemas[:2]))
        self.assertFalse(self.proveedor.esquemas[2])
        self.assertIn("Ya no podés buscar", self.proveedor.pedidos[2][-1]["content"])
        self.assertEqual(self.eventos[-1].texto, "Con lo que hay: **Moon** (2009)")
        self.assertEqual([t["id_tmdb"] for t in self.eventos[-1].tarjetas], [1])
        self.assertIn("ultima_sin_tools=si", linea)
        self.assertIn("sin_tiempo=busqueda", linea)

    async def test_con_tiempo_sigue_buscando(self):
        pasan = self.reloj.pasan
        linea = await self.linea(
            [
                [pasan(2), tool("descubrir")],
                [pasan(2), tool("descubrir")],
                ["Mirá [[1]]"],
            ]
        )

        self.assertTrue(all(self.proveedor.esquemas))
        self.assertIn("ultima_sin_tools=no", linea)
        self.assertIn("sin_tiempo=no", linea)

    async def test_un_modelo_que_no_contesta_se_corta_y_se_le_pide_cerrar(self):
        linea = await self.linea([[self.reloj.pasan(30)], ["Respuesta corta."]])

        # La primera llamada se cortó a los 17,5 s; la de cierre tuvo los 7,5 restantes.
        self.assertEqual(self.reloj.cortes, [17.5, 7.5])
        self.assertFalse(self.proveedor.esquemas[1])
        self.assertEqual(self.eventos[-1], Resultado("Respuesta corta."))
        self.assertIn("sin_tiempo=busqueda", linea)

    async def test_unas_tools_que_no_terminan_se_cortan_y_se_responde_igual(self):
        en_hilo = orquestador.en_hilo

        async def en_hilo_lento(funcion, *args, **kwargs):
            # Las tools «tardan» 30 s; el resto de las idas al hilo, lo normal.
            if funcion is orquestador._correr_tools:
                self.reloj.avanzar(30)
            return await en_hilo(funcion, *args, **kwargs)

        with patch("chatbot.orquestador.en_hilo", en_hilo_lento):
            linea = await self.linea(
                [[self.reloj.pasan(2), tool("descubrir")], ["No pude buscar."]]
            )

        self.assertEqual(self.eventos[-1].texto, "No pude buscar.")
        # El modelo recibe la búsqueda como fallida: la charla que ve tiene que cerrar
        # (un pedido de tool sin su resultado es un error para el proveedor).
        asistente, resultado, aviso = self.proveedor.pedidos[1][-3:]
        self.assertEqual(asistente["tool_calls"][0]["function"]["name"], "descubrir")
        self.assertEqual(resultado["role"], "tool")
        self.assertIn("tool_failed", resultado["content"])
        self.assertEqual(aviso["role"], "system")
        self.assertIn("tools=descubrir(sin_tiempo)", linea)
        self.assertIn("sin_tiempo=busqueda", linea)

    async def test_si_no_queda_tiempo_para_buscar_las_tools_no_corren(self):
        corridas = []

        def contar(ctx, **argumentos):
            corridas.append(1)
            return {"resultados": []}

        pasan = self.reloj.pasan
        with patch.dict(FUNCIONES, {"descubrir": contar}):
            eventos = await self.correr(
                [
                    [pasan(5), tool("descubrir")],
                    # Un texto largo que ya está saliendo puede usar hasta el final
                    # del plazo; al terminar (19 s) quedan 6 s: menos que la reserva.
                    [LARGO, pasan(14), tool("descubrir")],
                    ["Final."],
                ]
            )

        self.assertEqual(len(corridas), 1)
        self.assertEqual(eventos[-1].texto, f"{LARGO}\n\nFinal.")


class RespuestaCortadaTests(BasePlazo):
    async def test_una_respuesta_que_ya_sale_no_se_corta_en_la_reserva(self):
        pasan = self.reloj.pasan
        eventos = await self.correr(
            [[pasan(5), tool("descubrir")], [LARGO, pasan(15), " Fin."]]
        )

        # A los 20 s seguía escribiendo: pasó los 17,5 porque ya había texto.
        self.assertEqual(eventos[-1].texto, f"{LARGO} Fin.")

    async def test_una_respuesta_cortada_a_la_mitad_termina_en_puntos_suspensivos(self):
        pasan = self.reloj.pasan
        linea = await self.linea(
            [[pasan(5), tool("descubrir")], [LARGO, " y", pasan(30), " nunca"]]
        )

        # El turno cierra bien (hay `Resultado`: se guarda), con lo que llegó a salir.
        self.assertEqual(self.eventos[-1], Resultado(f"{LARGO} y…"))
        self.assertEqual(self.eventos[-2], Texto("…"))
        self.assertEqual(len(self.proveedor.pedidos), 2)
        self.assertIn("sin_tiempo=respuesta", linea)

    async def test_la_primera_respuesta_retenida_y_cortada_tambien_se_muestra(self):
        # Sin tools la primera vuelta se retiene entera: si se corta, sale lo juntado.
        linea = await self.linea([["Hola, te cuento ", self.reloj.pasan(30)]])

        self.assertEqual(self.eventos[-1], Resultado("Hola, te cuento…"))
        self.assertEqual(len(self.proveedor.pedidos), 1)
        self.assertIn("sin_tiempo=respuesta", linea)

    async def test_si_se_acaba_el_tiempo_sin_una_palabra_es_un_error(self):
        pasan = self.reloj.pasan
        eventos = []
        self.proveedor = ProveedorFalso([[pasan(30)], [pasan(30)]])

        with self.assertRaises(ErrorDelTurno):
            async for evento in responder(
                self.chat, "hola", "es", proveedor=self.proveedor
            ):
                eventos.append(evento)

        self.assertEqual(eventos, [])
        self.assertEqual(self.reloj.ahora, 25)

    async def test_la_ultima_llamada_cortada_conserva_lo_que_escribio(self):
        pasan = self.reloj.pasan
        eventos = await self.correr(
            [[pasan(30)], ["Te recomiendo", pasan(30), " nada"]]
        )

        self.assertEqual(eventos[-1], Resultado("Te recomiendo…"))

    async def test_un_timeout_del_proveedor_no_es_el_plazo(self):
        # Un `TimeoutError` que no viene de nuestro corte (un socket, el SDK) sigue
        # siendo una falla del proveedor, como antes.
        with self.assertRaises(ErrorDelTurno):
            await self.correr([["Hola", TimeoutError("socket")]])

    async def test_los_eventos_de_un_turno_normal_no_cambian(self):
        eventos = await self.correr([[tool("descubrir")], ["Mirá [[1]]"]])

        self.assertEqual(eventos[0], Estado("searching"))
        self.assertEqual(eventos[-1].texto, "Mirá **Moon** (2009)")


class PlazoTests(SimpleTestCase):
    def test_queda_baja_con_el_reloj_y_no_pasa_de_cero(self):
        reloj = RelojFalso()
        plazo = Plazo(25, reloj)

        reloj.ahora = 10
        self.assertEqual(plazo.queda(), 15)
        self.assertEqual(plazo.transcurrido(), 10)
        reloj.ahora = 40
        self.assertEqual(plazo.queda(), 0)

    def test_la_reserva_y_el_minimo_para_otra_vuelta_son_parte_del_total(self):
        plazo = Plazo(20, RelojFalso())

        self.assertEqual(plazo.total, 20)
        self.assertEqual(plazo.queda(reserva=6), 14)

    async def test_el_corte_de_verdad_cancela_lo_que_esta_esperando(self):
        # `Event().wait()` espera para siempre: nadie hace `set()`. Con 0 segundos el
        # corte llega en la primera vuelta del event loop, sin dormir.
        corte = Corte(0)
        with self.assertRaises(TimeoutError):
            await corte.esperar(asyncio.Event().wait())

        self.assertTrue(corte.vencio())

    async def test_el_corte_de_verdad_se_puede_correr(self):
        corte = Corte(0)
        corte.correr_hasta(60)

        # `sleep(0)` cede el control una vez: con el límite corrido, no corta.
        await corte.esperar(asyncio.sleep(0))

        self.assertFalse(corte.vencio())

    async def test_un_timeout_ajeno_no_cuenta_como_vencido(self):
        async def falla():
            raise TimeoutError("de otro lado")

        corte = Corte(60)
        with self.assertRaises(TimeoutError):
            await corte.esperar(falla())

        self.assertFalse(corte.vencio())

    async def test_recorrer_entrega_todo_y_cierra_el_flujo(self):
        cerrado = []

        async def flujo():
            try:
                yield "a"
                yield "b"
            finally:
                cerrado.append(True)

        items = [item async for item in recorrer(flujo(), Corte(60))]

        self.assertEqual(items, ["a", "b"])
        self.assertEqual(cerrado, [True])

    async def test_recorrer_cierra_el_flujo_cuando_el_corte_vence(self):
        cerrado = []

        async def flujo():
            try:
                yield "a"
                await asyncio.Event().wait()
            finally:
                # Acá el proveedor real cierra su conexión con el modelo.
                cerrado.append(True)

        items = []
        with self.assertRaises(TimeoutError):
            async for item in recorrer(flujo(), Corte(0)):
                items.append(item)

        self.assertEqual(items, ["a"])
        self.assertEqual(cerrado, [True])


class TopeDeLaVistaTests(SimpleTestCase):
    @override_settings(LLM_TIMEOUT_SECONDS=25)
    def test_la_red_de_la_vista_es_un_poco_mayor_que_el_plazo(self):
        self.assertEqual(tope_de_la_vista(), 30)
