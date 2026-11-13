"""Ninguna caché guarda contenido de TMDB más de 180 días (#180, tarea 2.8).

Los términos de TMDB cuentan todo lo que se guarda, no solo la base: la caché de
Redis, su copia de respaldo y lo que el navegador retiene por `Cache-Control`.
Hoy el tope mayor es de 30 días; este test falla si alguien lo sube por encima
de 180, y dice cuál fue.
"""

from django.test import SimpleTestCase

from catalogo import cache, views

DIAS_LIMITE = 180
LIMITE_EN_SEGUNDOS = DIAS_LIMITE * 24 * 3600


class TopeDeCacheTests(SimpleTestCase):
    def test_ningun_ttl_de_un_endpoint_pasa_de_180_dias(self):
        for endpoint, segundos in cache.ENDPOINT_TTLS.items():
            with self.subTest(endpoint=endpoint):
                self.assertLessEqual(segundos, LIMITE_EN_SEGUNDOS)

    def test_el_respaldo_general_no_pasa_de_180_dias(self):
        self.assertLessEqual(cache.RESPALDO_TTL, LIMITE_EN_SEGUNDOS)

    def test_ningun_respaldo_por_endpoint_pasa_de_180_dias(self):
        for endpoint, segundos in cache.RESPALDO_TTLS.items():
            with self.subTest(endpoint=endpoint):
                self.assertLessEqual(segundos, LIMITE_EN_SEGUNDOS)

    def test_el_max_age_del_catalogo_no_pasa_de_180_dias(self):
        self.assertLessEqual(views.CACHE_NAVEGADOR_SEGUNDOS, LIMITE_EN_SEGUNDOS)

    def test_el_test_si_detecta_un_ttl_de_200_dias(self):
        # Prueba del propio test: con un TTL de 200 días, el chequeo falla.
        excesivo = {**cache.ENDPOINT_TTLS, "movie_detail": 200 * 24 * 3600}

        pasan = all(segundos <= LIMITE_EN_SEGUNDOS for segundos in excesivo.values())

        self.assertFalse(pasan)
