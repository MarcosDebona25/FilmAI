"""S3 de la auditoría: Postgres publicado en todas las interfaces.

Es una prueba de configuración: lee el compose real (montado como
`BASE_DIR.parent`, igual que `test_seguridad_redis.py`) y no levanta ningún
contenedor.
"""

from django.conf import settings
from django.test import SimpleTestCase


class ComposePostgresTests(SimpleTestCase):
    def setUp(self):
        import yaml

        ruta = settings.BASE_DIR.parent / "docker-compose.yml"
        if not ruta.exists():
            self.skipTest("docker-compose.yml no está montado en este entorno")
        self.db = yaml.safe_load(ruta.read_text())["services"]["db"]

    def test_el_puerto_solo_se_publica_en_loopback(self):
        self.assertTrue(self.db["ports"])
        for puerto in self.db["ports"]:
            self.assertTrue(str(puerto).startswith("127.0.0.1:"), puerto)

    def test_el_puerto_sigue_publicado_para_el_host(self):
        """DBeaver desde el host necesita el 5432 de Postgres en loopback."""
        self.assertIn("127.0.0.1:5432:5432", self.db["ports"])

