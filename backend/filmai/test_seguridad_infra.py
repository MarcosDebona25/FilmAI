"""S3 y S4 de la auditoría: Postgres en todas las interfaces y `entrypoint.sh`.

Son pruebas de configuración: leen los archivos reales (el compose montado como
`BASE_DIR.parent`, igual que `test_seguridad_redis.py`, y el entrypoint dentro
de `backend/`) y no levantan ningún contenedor.
"""

import re

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


class EntrypointSuperusuarioTests(SimpleTestCase):
    def setUp(self):
        ruta = settings.BASE_DIR / "entrypoint.sh"
        if not ruta.exists():
            self.skipTest("entrypoint.sh no está montado en este entorno")
        self.texto = ruta.read_text()

    def test_el_shell_no_interpola_los_datos_del_superusuario_en_el_python(self):
        """Una comilla en la contraseña rompería el script o inyectaría código."""
        self.assertNotRegex(self.texto, r"\$\{?DJANGO_SUPERUSER_")

    def test_python_lee_los_datos_del_entorno(self):
        for variable in ("USERNAME", "EMAIL", "PASSWORD"):
            with self.subTest(variable=variable):
                self.assertIn(f'os.environ["DJANGO_SUPERUSER_{variable}"]', self.texto)

    def test_el_python_va_en_un_heredoc_entrecomillado(self):
        """Con `<<'PY'` el shell no expande nada; sin comillas sí lo haría."""
        self.assertRegex(self.texto, r"manage\.py shell <<'PY'\n")
        self.assertNotRegex(self.texto, r"<<\s*PY\b")

    def test_la_contrasena_no_viaja_en_la_linea_de_comandos(self):
        """`shell -c "..."` deja el texto en `ps`; el heredoc entra por stdin."""
        self.assertIsNone(re.search(r"manage\.py shell\s+-c", self.texto))
