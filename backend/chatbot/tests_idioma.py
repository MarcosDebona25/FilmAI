"""Tests de `detectar_idioma()`: en qué idioma escribió el usuario su mensaje.

El modelo no lo deduce bien cuando el perfil y el historial están en otro idioma
(verificado contra DeepSeek el 06/11/2026), así que el código lo detecta y el
prompt se lo dice con todas las letras. Desde el 22/11/2026 lo detecta fastText
(`fast-langdetect`, modelo `lite`) y solo reconoce español e inglés: el resto es
`None` y el chatbot usa el idioma de la cuenta.

Estos tests usan el modelo real (carga ~0,18 s la primera vez, solo en memoria):
lo que se prueba es justamente cómo clasifica, así que un mock no serviría. Los
mensajes salen del benchmark que justificó la elección (`docs/decisiones.md`).
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from chatbot.idioma import detectar_idioma


class DetectarIdiomaTests(SimpleTestCase):
    def test_un_pedido_en_ingles(self):
        self.assertEqual(detectar_idioma("Something like Arrival, but lighter"), "en")

    def test_un_pedido_en_espanol(self):
        texto = "Quiero algo como Interestelar pero más corto"
        self.assertEqual(detectar_idioma(texto), "es")

    def test_los_signos_del_espanol_alcanzan(self):
        self.assertEqual(detectar_idioma("¿Cuál?"), "es")

    def test_sin_senal_no_adivina(self):
        # Un título suelto no dice nada: decide el idioma del turno.
        self.assertIsNone(detectar_idioma("Moon"))
        self.assertIsNone(detectar_idioma("Interstellar"))

    def test_ok_se_toma_como_ingles(self):
        # Error leve aceptado en el benchmark: el modelo da «en» con 0,63 de
        # confianza, por encima del umbral. Es una sola palabra y no cambia el
        # idioma de nadie en la práctica; subir el umbral costaría más aciertos.
        self.assertEqual(detectar_idioma("ok"), "en")

    def test_un_titulo_en_ingles_no_cambia_el_idioma_del_pedido(self):
        texto = "Recomendame algo como The Lord of the Rings"
        self.assertEqual(detectar_idioma(texto), "es")

    def test_una_tilde_de_un_titulo_no_alcanza_contra_el_ingles(self):
        self.assertEqual(detectar_idioma("Something like Amélie"), "en")


class OtrosIdiomasNoSeAdivinanTests(SimpleTestCase):
    """Lo que no es español ni inglés da `None`, no el idioma más parecido."""

    def comprobar(self, casos, esperado=None):
        for texto in casos:
            with self.subTest(texto=texto):
                self.assertEqual(detectar_idioma(texto), esperado)

    def test_portugues(self):
        # El primero es el bug real: la heurística vieja lo tomaba por español.
        self.comprobar(
            [
                "Na verdade, eu só gostei da aparência dos dragões. "
                "Então, me dê uma série nova com muitos dragões.",
                "Tem que ser realista.",
                "Eu quero ver um filme de terror para hoje",
                "Você pode me recomendar um filme de suspense?",
                "Algum filme estrelado por Tom Hardy?",
            ]
        )

    def test_italiano_frances_y_aleman(self):
        self.comprobar(
            [
                "Vorrei vedere un film come Interstellar",
                "Un film d'azione per stasera",
                "Je voudrais un film comme Amélie",
                "recommande-moi une série policière",
                "Ich möchte einen Film wie Interstellar sehen",
            ]
        )

    def test_otros_alfabetos(self):
        self.comprobar(["Посоветуй фильм ужасов", "おすすめの映画を教えて"])


class CasosDelBenchmarkTests(SimpleTestCase):
    def comprobar(self, casos):
        for texto, esperado in casos:
            with self.subTest(texto=texto):
                self.assertEqual(detectar_idioma(texto), esperado)

    def test_mezclas_con_titulos_en_otro_idioma(self):
        self.comprobar(
            [
                ("algo como The Dark Knight", "es"),
                ("something like La casa de papel", "en"),
                ("I want something like El laberinto del fauno", "en"),
            ]
        )

    def test_texto_en_mayusculas(self):
        # La librería pasa a minúsculas el texto mayormente en mayúsculas; sin
        # eso el modelo, entrenado con texto corriente, flaquea.
        self.comprobar(
            [
                ("QUIERO UNA PELI DE TERROR", "es"),
                ("SOMETHING LIKE ALIEN PLEASE", "en"),
                ("EU QUERO UM FILME DE AÇÃO", None),
            ]
        )

    def test_mensajes_de_mas_de_80_caracteres(self):
        # La librería recorta a 80 caracteres salvo que se le pase `None`.
        largo_es = (
            "Hace poco vi Interestelar y me voló la cabeza, quiero algo que tenga "
            "esa mezcla de ciencia y emoción familiar, pero que no dure tres horas"
        )
        largo_en = (
            "I just finished Breaking Bad and I need another crime drama with a "
            "slow burn and great acting, ideally something that is already finished"
        )
        self.assertGreater(len(largo_es), 80)
        self.assertGreater(len(largo_en), 80)
        self.comprobar([(largo_es, "es"), (largo_en, "en")])

    def test_el_recorte_de_la_libreria_esta_apagado(self):
        # Un mensaje que empieza en español y sigue en inglés: con el recorte de
        # 80 caracteres la librería solo vería el comienzo.
        texto = (
            "hola " * 20 + "I would like to watch something similar to this one " * 3
        )
        self.assertEqual(detectar_idioma(texto), "en")


class SinTextoYConFallasTests(SimpleTestCase):
    def test_vacio_o_solo_espacios_es_none_sin_llamar_a_la_libreria(self):
        with patch("chatbot.idioma._detector") as detector:
            for texto in ("", "   ", "\n\t "):
                with self.subTest(texto=texto):
                    self.assertIsNone(detectar_idioma(texto))
        detector.assert_not_called()

    def test_una_excepcion_de_la_libreria_da_none_y_se_loguea_sin_el_texto(self):
        # La detección nunca puede romper un turno. El texto del usuario no
        # puede aparecer en el log, ni siquiera dentro del mensaje de la excepción.
        detector = MagicMock()
        detector.detect.side_effect = RuntimeError("fallo con el texto secreto")
        with (
            patch("chatbot.idioma._detector", return_value=detector),
            self.assertLogs("chatbot.idioma", level="WARNING") as registro,
        ):
            self.assertIsNone(detectar_idioma("texto secreto"))
        self.assertIn("RuntimeError", registro.output[0])
        self.assertNotIn("secreto", registro.output[0])

    def test_el_idioma_debajo_del_umbral_es_none(self):
        detector = MagicMock()
        detector.detect.return_value = [{"lang": "es", "score": 0.49}]
        with patch("chatbot.idioma._detector", return_value=detector):
            self.assertIsNone(detectar_idioma("algo"))
        detector.detect.return_value = [{"lang": "en", "score": 0.5}]
        with patch("chatbot.idioma._detector", return_value=detector):
            self.assertEqual(detectar_idioma("algo"), "en")

    def test_siempre_pide_el_modelo_lite_y_un_solo_resultado(self):
        # `model="auto"` (el valor por defecto) descargaría el modelo de 126 MB.
        detector = MagicMock()
        detector.detect.return_value = [{"lang": "es", "score": 0.9}]
        with patch("chatbot.idioma._detector", return_value=detector):
            detectar_idioma("algo")
        detector.detect.assert_called_once_with("algo", model="lite", k=1)
