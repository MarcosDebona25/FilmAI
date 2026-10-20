"""F1 de la auditoría: Redis sin contraseña y caché que deserializa pickle.

`settings.py` decide la caché y las URLs de Celery al importarse, así que cada
caso importa el módulo en un proceso aparte con las variables de entorno que
quiere probar. Así se prueba el archivo real, no una copia de su lógica.
"""

import json
import os
import subprocess
import sys
from typing import ClassVar

from django.core.cache.backends.redis import RedisCache
from django.test import SimpleTestCase

SCRIPT = """
import json
from filmai import settings as s
print(json.dumps({
    "redis_url": s.REDIS_URL,
    "broker": s.CELERY_BROKER_URL,
    "result": s.CELERY_RESULT_BACKEND,
    "caches": s.CACHES,
}))
"""

CON_CLAVE = "redis://:clave-de-prueba@redis:6379/{db}"
SIN_CLAVE = "redis://redis:6379/{db}"


def importar_settings(**entorno):
    """Importa `filmai.settings` en un proceso nuevo y devuelve (código, salida)."""
    env = {
        **os.environ,
        "DEBUG": "False",
        "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        "REDIS_URL": CON_CLAVE.format(db=0),
        "CELERY_BROKER_URL": CON_CLAVE.format(db=1),
        "CELERY_RESULT_BACKEND": CON_CLAVE.format(db=2),
        **entorno,
    }
    proceso = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return proceso.returncode, proceso.stdout, proceso.stderr


class RedisConContrasenaTests(SimpleTestCase):
    def test_produccion_rechaza_redis_de_cache_sin_contrasena(self):
        codigo, _, stderr = importar_settings(REDIS_URL=SIN_CLAVE.format(db=0))
        self.assertNotEqual(codigo, 0)
        self.assertIn("REDIS_URL", stderr)

    def test_produccion_rechaza_broker_de_celery_sin_contrasena(self):
        codigo, _, stderr = importar_settings(CELERY_BROKER_URL=SIN_CLAVE.format(db=1))
        self.assertNotEqual(codigo, 0)
        self.assertIn("CELERY_BROKER_URL", stderr)

    def test_produccion_rechaza_resultados_de_celery_sin_contrasena(self):
        codigo, _, stderr = importar_settings(
            CELERY_RESULT_BACKEND=SIN_CLAVE.format(db=2)
        )
        self.assertNotEqual(codigo, 0)
        self.assertIn("CELERY_RESULT_BACKEND", stderr)

    def test_produccion_acepta_las_tres_urls_con_contrasena(self):
        codigo, stdout, stderr = importar_settings()
        self.assertEqual(codigo, 0, stderr)
        datos = json.loads(stdout)
        self.assertIn("clave-de-prueba", datos["caches"]["default"]["LOCATION"])

    def test_desarrollo_no_exige_contrasena(self):
        """Con DEBUG la caché es local; no hay nada que proteger en Redis."""
        codigo, _, stderr = importar_settings(
            DEBUG="True", REDIS_URL=SIN_CLAVE.format(db=0)
        )
        self.assertEqual(codigo, 0, stderr)


class CacheSinPickleTests(SimpleTestCase):
    def test_la_cache_de_produccion_no_usa_el_serializador_pickle_por_defecto(self):
        codigo, stdout, stderr = importar_settings()
        self.assertEqual(codigo, 0, stderr)
        opciones = json.loads(stdout)["caches"]["default"].get("OPTIONS", {})
        self.assertEqual(opciones.get("serializer"), "filmai.cache.JSONRedisSerializer")


class JSONRedisSerializerTests(SimpleTestCase):
    def setUp(self):
        from filmai.cache import JSONRedisSerializer

        self.serializador = JSONRedisSerializer()

    def test_ida_y_vuelta_de_los_valores_que_guarda_la_app(self):
        for valor in ([1.5, 2.5], {"a": [1, 2], "b": "x"}, "texto", None, True):
            with self.subTest(valor=valor):
                datos = self.serializador.dumps(valor)
                self.assertEqual(self.serializador.loads(datos), valor)

    def test_los_enteros_se_guardan_crudos_para_que_incr_funcione(self):
        self.assertEqual(self.serializador.dumps(7), 7)
        self.assertEqual(self.serializador.loads(b"7"), 7)

    def test_un_valor_pickle_no_se_deserializa_ni_ejecuta_codigo(self):
        import pickle

        ejecutado = []

        class Ajeno:
            def __reduce__(self):
                return (ejecutado.append, ("ejecutado",))

        with self.assertLogs("filmai.cache", level="WARNING"):
            resultado = self.serializador.loads(pickle.dumps(Ajeno()))
        self.assertIsNone(resultado)
        self.assertEqual(ejecutado, [])


class RedisFalso:
    """Cliente mínimo en memoria con la interfaz de `redis.Redis` que usa Django."""

    almacen: ClassVar[dict] = {}

    def __init__(self, connection_pool=None):
        pass

    def set(self, clave, valor, ex=None):
        self.almacen[clave] = valor if isinstance(valor, int) else bytes(valor)
        return True

    def get(self, clave):
        valor = self.almacen.get(clave)
        return str(valor).encode() if isinstance(valor, int) else valor

    def exists(self, clave):
        return int(clave in self.almacen)

    def incr(self, clave, delta=1):
        self.almacen[clave] = int(self.almacen.get(clave, 0)) + delta
        return self.almacen[clave]


class RedisCacheConSerializadorTests(SimpleTestCase):
    """Prueba el contrato real: `RedisCache` + el serializador de `settings`."""

    def setUp(self):
        from django.conf import settings

        RedisFalso.almacen = {}
        self.cache = RedisCache(
            "redis://:clave-de-prueba@redis:6379/0",
            {"OPTIONS": {"serializer": "filmai.cache.JSONRedisSerializer"}},
        )
        self.cache._cache._client = RedisFalso
        self.settings_serializer = settings.CACHES["default"].get("OPTIONS", {})

    def test_el_backend_carga_el_serializador_json(self):
        from filmai.cache import JSONRedisSerializer

        self.assertIsInstance(self.cache._cache._serializer, JSONRedisSerializer)

    def test_ida_y_vuelta_por_el_backend(self):
        self.cache.set("tmdb:x", {"titulo": "Heat", "ids": [1, 2]})
        self.assertEqual(self.cache.get("tmdb:x"), {"titulo": "Heat", "ids": [1, 2]})

    def test_los_contadores_de_throttle_siguen_funcionando(self):
        self.cache.set("throttle:x", 1)
        self.assertEqual(self.cache.incr("throttle:x"), 2)

    def test_un_pickle_ajeno_en_redis_se_lee_como_ausente(self):
        import pickle

        RedisFalso.almacen[self.cache.make_key("tmdb:malo")] = pickle.dumps({"a": 1})
        with self.assertLogs("filmai.cache", level="WARNING"):
            self.assertIsNone(self.cache.get("tmdb:malo"))


class ComposeRedisTests(SimpleTestCase):
    """Lee el compose real (montado como BASE_DIR.parent, igual que `contracts`)."""

    def setUp(self):
        import yaml
        from django.conf import settings

        ruta = settings.BASE_DIR.parent / "docker-compose.yml"
        if not ruta.exists():
            self.skipTest("docker-compose.yml no está montado en este entorno")
        self.redis = yaml.safe_load(ruta.read_text())["services"]["redis"]

    def test_el_puerto_solo_se_publica_en_loopback(self):
        for puerto in self.redis["ports"]:
            self.assertTrue(puerto.startswith("127.0.0.1:"), puerto)

    def test_redis_arranca_con_requirepass(self):
        self.assertIn("--requirepass", " ".join(self.redis["command"]))

    def test_redis_conserva_la_baja_de_privilegios_de_la_imagen(self):
        """Sin pasar por el entrypoint, `redis-server` correría como root."""
        self.assertIn(
            "docker-entrypoint.sh redis-server", " ".join(self.redis["command"])
        )

    def test_la_contrasena_es_obligatoria_y_no_va_en_la_linea_de_comandos(self):
        self.assertIn(":?", self.redis["environment"]["REDIS_PASSWORD"])
        self.assertNotIn("${REDIS_PASSWORD", " ".join(self.redis["command"]))
