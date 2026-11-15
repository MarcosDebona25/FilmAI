"""Tests de caracterización de `responder()`.

Un test de caracterización no prueba una regla nueva: saca una foto de lo que el
código YA hace, para poder moverlo de lugar sin miedo. Se escribieron antes de
partir `responder` en funciones (15/11/2026) y pasan igual antes y después: si uno
falla, el refactor cambió la conducta.

Los demás tests del orquestador miran sobre todo el texto final. Estos miran lo que
aquellos no fijaban: la secuencia exacta de eventos, en qué momento sale cada uno y
la línea `Turno:` en los caminos menos comunes.
"""

from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.llm import ProveedorFalso
from chatbot.orquestador import _LARGO_DE_PREAMBULO, responder
from chatbot.tests_orquestador import BaseOrquestador, tool

LARGO = "x" * (_LARGO_DE_PREAMBULO + 1)


class SecuenciaDeEventosTests(BaseOrquestador):
    async def test_un_turno_con_preambulo_y_busqueda_entrega_estos_eventos(self):
        eventos = await self.correr(
            [["Busco.", tool("descubrir")], ["Te recomiendo ", "[[1]]."]]
        )

        # El preámbulo no sale; el `Estado` va antes de correr la tool; el marcador
        # sale ya cambiado por el título, y el `Resultado` cierra con la tarjeta.
        self.assertEqual(eventos[0], Estado("searching"))
        self.assertTrue(all(isinstance(e, Texto) for e in eventos[1:-1]))
        texto = "".join(e.delta for e in eventos[1:-1])
        self.assertEqual(texto, "Te recomiendo **Moon** (2009).")
        self.assertEqual(eventos[-1], Resultado(texto, eventos[-1].tarjetas))
        self.assertEqual([t["id_tmdb"] for t in eventos[-1].tarjetas], [1])

    async def test_un_texto_largo_con_busqueda_sale_antes_del_estado(self):
        eventos = await self.correr([[LARGO, tool("descubrir")], ["Listo."]])

        # El «\n\n» que separa las dos vueltas sale partido: el filtro de marcadores
        # retiene el último espacio por si después viene un `[[n]]`.
        self.assertEqual(
            eventos[:-1],
            [Texto(LARGO), Estado("searching"), Texto("\n"), Texto("\nListo.")],
        )

    async def test_despues_de_una_busqueda_el_texto_largo_sale_mientras_llega(self):
        # Ya corrió una tool: la vuelta no se retiene entera. En cuanto el texto pasa
        # el largo de un preámbulo sale al front, sin esperar al último trozo.
        self.proveedor = ProveedorFalso([[tool("descubrir")], [LARGO, "fin"]])
        generador = responder(self.chat, "hola", "es", proveedor=self.proveedor)

        self.assertEqual(await anext(generador), Estado("searching"))
        self.assertEqual(await anext(generador), Texto(LARGO))

        # `entregados` cuenta los trozos que el proveedor ya dio: falta «fin».
        self.assertEqual(self.proveedor.entregados, 1)
        await generador.aclose()

    async def test_dos_busquedas_seguidas_avisan_dos_veces(self):
        eventos = await self.correr(
            [[tool("descubrir")], [tool("descubrir")], ["Listo."]]
        )

        self.assertEqual(
            eventos[:-1],
            [Estado("searching"), Estado("searching"), Texto("Listo.")],
        )


class FallaAMitadDelTurnoTests(BaseOrquestador):
    async def test_si_el_proveedor_falla_tras_buscar_lo_ya_emitido_no_se_pierde(self):
        eventos = []
        self.proveedor = ProveedorFalso(
            [[LARGO, tool("descubrir")], [LARGO, RuntimeError("503")]]
        )

        with self.assertRaises(ErrorDelTurno):
            async for evento in responder(
                self.chat, "hola", "es", proveedor=self.proveedor
            ):
                eventos.append(evento)

        # Lo que salió antes de la falla ya está en el front; no hay `Resultado`.
        self.assertEqual(
            eventos,
            [Texto(LARGO), Estado("searching"), Texto("\n"), Texto("\n" + LARGO)],
        )

    async def test_si_el_proveedor_falla_en_la_primera_vuelta_no_sale_nada(self):
        eventos = []
        self.proveedor = ProveedorFalso([[LARGO, RuntimeError("503")]])

        with self.assertRaises(ErrorDelTurno):
            async for evento in responder(
                self.chat, "hola", "es", proveedor=self.proveedor
            ):
                eventos.append(evento)

        # La primera vuelta se retiene entera: el usuario no llegó a leer nada.
        self.assertEqual(eventos, [])


class LineaDelTurnoTests(BaseOrquestador):
    """La línea `Turno:` del log, en los caminos que los otros tests no fijaban."""

    async def linea(self, guion):
        with self.assertLogs("chatbot.orquestador", level="INFO") as log:
            self.eventos = await self.correr(guion)
        return next(m for m in log.output if "Turno:" in m)

    async def test_un_turno_simple(self):
        linea = await self.linea([["Hola"]])

        self.assertIn("tools=ninguna vueltas=1 ultima_sin_tools=no", linea)
        self.assertIn("tarjetas=ninguna", linea)
        self.assertIn("llamadas=1", linea)

    async def test_una_busqueda_y_la_respuesta(self):
        linea = await self.linea([[tool("descubrir")], ["Mirá [[1]]"]])

        self.assertIn("tools=descubrir(1) vueltas=2 ultima_sin_tools=no", linea)
        self.assertIn("tarjetas=marcadores marcadores_validos=1", linea)

    async def test_la_busqueda_forzada_cuenta_como_una_vuelta_mas(self):
        linea = await self.linea([["Uno [[9]]"], [tool("descubrir")], ["Mirá [[1]]"]])

        self.assertIn("vueltas=3", linea)
        self.assertIn("reintento_forzado=si", linea)
        self.assertIn("llamadas=3", linea)

    async def test_si_la_busqueda_forzada_falla_no_hay_mas_llamadas(self):
        linea = await self.linea([["Primero [[9]] ok"], [RuntimeError("503")]])

        self.assertEqual(self.eventos, [Texto("Primero ok"), Resultado("Primero ok")])
        self.assertEqual(len(self.proveedor.pedidos), 2)
        self.assertIn("vueltas=2", linea)
        self.assertIn("reintento_forzado=si", linea)
        # La llamada que falló no llegó a informar su costo.
        self.assertIn("llamadas=1", linea)

    async def test_el_tope_de_vueltas_queda_anotado(self):
        guion = [[tool("descubrir")] for _ in range(5)] + [["Con lo que hay."]]

        linea = await self.linea(guion)

        self.assertIn("vueltas=5 ultima_sin_tools=si", linea)
        self.assertIn("llamadas=6", linea)

    async def test_un_turno_sin_texto_queda_anotado(self):
        linea = await self.linea([[tool("descubrir")], [], ["Moon."]])

        self.assertIn("vueltas=2 ultima_sin_tools=si", linea)
        self.assertIn("llamadas=3", linea)
