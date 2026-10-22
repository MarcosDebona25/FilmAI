"""Ejecutor de pruebas que exige el sobre en toda respuesta de error de la API.

Parchea `django.test.Client.request` (la base de `APIClient`) mientras corre la
suite: cada 4xx/5xx JSON bajo `/api/` debe cumplir el contrato o la prueba que lo
provocó falla en el punto exacto.
"""

import json
import unittest

from django.conf import settings
from django.core.cache import cache
from django.test import Client
from django.test.runner import DiscoverRunner

from filmai.errores.sobre import validar_respuesta_error

_original = Client.request


def _validar(self, **request):
    response = _original(self, **request)
    ruta = request.get("PATH_INFO", "")
    es_json = response.get("Content-Type", "").startswith("application/json")
    if response.status_code >= 400 and ruta.startswith("/api/") and es_json:
        try:
            cuerpo = json.loads(response.content)
        except ValueError:
            cuerpo = None
        try:
            validar_respuesta_error(response.status_code, cuerpo, debug=settings.DEBUG)
        except AssertionError as error:
            raise AssertionError(
                f"Sobre inválido en {request.get('REQUEST_METHOD')} {ruta}: {error}"
            ) from error
    return response


class ResultadoConCacheLimpia(unittest.TextTestResult):
    """Vacía la caché antes de cada test.

    Los límites de tasa (login, registro, catálogo) cuentan por IP y, en los
    tests, todos los pedidos vienen de la misma. Sin esto el contador de un test
    se arrastra al siguiente y los tests se rompen según el orden en que corran.
    """

    def startTest(self, test):
        cache.clear()
        super().startTest(test)


class EjecutorConSobre(DiscoverRunner):
    def get_resultclass(self):
        base = super().get_resultclass()
        if base is None:
            return ResultadoConCacheLimpia
        return type("ResultadoConCacheLimpia", (ResultadoConCacheLimpia, base), {})

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.FILMAI_SOBRE_ESTRICTO = True
        Client.request = _validar

    def teardown_test_environment(self, **kwargs):
        Client.request = _original
        del settings.FILMAI_SOBRE_ESTRICTO
        super().teardown_test_environment(**kwargs)
