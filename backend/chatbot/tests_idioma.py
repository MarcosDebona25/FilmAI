"""Tests de `detectar_idioma()`: en qué idioma escribió el usuario su mensaje.

El modelo no lo deduce bien cuando el perfil y el historial están en otro idioma
(verificado contra DeepSeek el 06/11/2026), así que el código lo detecta y el
prompt se lo dice con todas las letras.
"""

from django.test import SimpleTestCase

from chatbot.idioma import detectar_idioma


class DetectarIdiomaTests(SimpleTestCase):
    def test_un_pedido_en_ingles(self):
        self.assertEqual(detectar_idioma("Something like Arrival, but lighter"), "en")

    def test_un_pedido_en_espanol(self):
        texto = "Quiero algo como Interestelar pero más corto"
        self.assertEqual(detectar_idioma(texto), "es")

    def test_los_signos_del_espanol_alcanzan(self):
        # «¿Cuál?» no tiene ninguna palabra de la lista, pero solo puede ser español.
        self.assertEqual(detectar_idioma("¿Cuál?"), "es")

    def test_sin_senal_no_adivina(self):
        # Un título suelto o un «ok» no dicen nada: decide el idioma del turno.
        self.assertIsNone(detectar_idioma("Moon"))
        self.assertIsNone(detectar_idioma("ok"))
        self.assertIsNone(detectar_idioma(""))

    def test_un_titulo_en_ingles_no_cambia_el_idioma_del_pedido(self):
        # Cada palabra cuenta una vez: los dos «the» del título suman como uno.
        texto = "Recomendame algo como The Lord of the Rings"
        self.assertEqual(detectar_idioma(texto), "es")

    def test_una_tilde_de_un_titulo_no_alcanza_contra_el_ingles(self):
        self.assertEqual(detectar_idioma("Something like Amélie"), "en")
