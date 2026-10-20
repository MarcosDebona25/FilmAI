"""F3 de la auditoría: `NUM_PROXIES` obligatorio en producción.

Con un proxy delante y `NUM_PROXIES=0`, todos los usuarios compartirían la IP del
proxy y los límites por IP bloquearían a todos juntos. Por eso, con DEBUG=False,
no hay valor por defecto: el arranque falla si falta.
"""

import json

from django.test import SimpleTestCase

from .test_seguridad_redis import importar_settings


class NumProxiesTests(SimpleTestCase):
    def test_produccion_sin_num_proxies_no_arranca(self):
        codigo, _, stderr = importar_settings(NUM_PROXIES="")
        self.assertNotEqual(codigo, 0)
        self.assertIn("NUM_PROXIES", stderr)

    def test_produccion_con_num_proxies_vacio_con_espacios_tampoco_arranca(self):
        codigo, _, stderr = importar_settings(NUM_PROXIES="  ")
        self.assertNotEqual(codigo, 0)
        self.assertIn("NUM_PROXIES", stderr)

    def test_produccion_con_valor_no_numerico_no_arranca(self):
        codigo, _, _ = importar_settings(NUM_PROXIES="uno")
        self.assertNotEqual(codigo, 0)

    def test_produccion_acepta_cero_y_lo_pasa_a_drf(self):
        codigo, stdout, stderr = importar_settings(NUM_PROXIES="0")
        self.assertEqual(codigo, 0, stderr)
        self.assertEqual(json.loads(stdout)["num_proxies"], 0)

    def test_produccion_acepta_un_proxy(self):
        codigo, stdout, stderr = importar_settings(NUM_PROXIES="1")
        self.assertEqual(codigo, 0, stderr)
        self.assertEqual(json.loads(stdout)["num_proxies"], 1)

    def test_desarrollo_no_lo_exige_y_usa_cero(self):
        codigo, stdout, stderr = importar_settings(DEBUG="True", NUM_PROXIES="")
        self.assertEqual(codigo, 0, stderr)
        self.assertEqual(json.loads(stdout)["num_proxies"], 0)
