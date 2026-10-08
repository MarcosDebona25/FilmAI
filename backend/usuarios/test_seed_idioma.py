"""El seed completo ofrece cuentas conocidas; el modo de reseñas las conserva."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from catalogo.factories import ProduccionAudiovisualFactory

from .factories import UsuarioFactory
from .models import Usuario


class SemillaIdiomaTests(TestCase):
    def test_seed_crea_cuentas_conocidas_en_ambos_idiomas_al_repetir(self):
        """La recreación explícita asigna ES/EN deterministas y conserva el idioma del admin."""
        administrador = UsuarioFactory(is_staff=True, is_superuser=True, idioma=None)
        esperado = {
            "usuario001@filmai.com": "es",
            "usuario002@filmai.com": "en",
            "usuario003@filmai.com": "es",
        }
        for _ in range(2):
            call_command("seed", stdout=StringIO())
            self.assertEqual(
                dict(
                    Usuario.objects.filter(is_staff=False).values_list(
                        "correo", "idioma"
                    )
                ),
                esperado,
            )
            administrador.refresh_from_db()
            self.assertIsNone(administrador.idioma)

    def test_solo_resenas_no_asigna_ni_reemplaza_idiomas(self):
        """Agregar actividad a cuentas previas no elige un idioma por ellas."""
        usuarios = (UsuarioFactory(idioma="es"), UsuarioFactory(idioma=None))
        ProduccionAudiovisualFactory()
        call_command("seed", solo_resenas=True, stdout=StringIO())
        for usuario, esperado in zip(usuarios, ("es", None), strict=True):
            usuario.refresh_from_db()
            self.assertEqual(usuario.idioma, esperado)
