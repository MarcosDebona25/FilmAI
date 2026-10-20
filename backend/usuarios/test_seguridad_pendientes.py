"""F4 de la auditoría: una cuenta pendiente reservaba el correo para siempre.

Quien registraba el correo de otra persona (con una contraseña propia) la dejaba
sin poder registrarse ni recuperar la cuenta, y la pendiente no vencía nunca.
Ahora una pendiente deja de reservar su correo y su usuario cuando pasa el plazo
del enlace de confirmación; dentro del plazo el registro se sigue rechazando
(reemplazarla permitiría quitarle a la víctima un registro legítimo).
"""

from datetime import date, timedelta

from allauth.account.models import EmailAddress
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from filmai import tests_contrato

from .factories import UsuarioFactory
from .models import EstadoCuenta, Usuario
from .pendientes import liberar_pendientes_vencidas
from .tasks import limpiar_pendientes_vencidas

REGISTRO = "/api/auth/registration/"
DISPONIBLE = "/api/auth/username-available/"


def cuerpo(**cambios):
    datos = {
        "correo": "ana@example.com",
        "nombre_usuario": "ana12345",
        "nombre": "Ana",
        "apellido": "Pérez",
        "fecha_nacimiento": "1990-01-01",
        "genero": "no_especifica",
        "pais": "AR",
        "acepta_terminos": True,
        "password1": "NuevaClave456!",
        "password2": "NuevaClave456!",
    }
    return {**datos, **cambios}


def pendiente(dias, **campos):
    """Pendiente registrada hace `dias` días (el campo es auto_now_add)."""
    usuario = UsuarioFactory(estado=EstadoCuenta.PENDIENTE, **campos)
    EmailAddress.objects.create(
        user=usuario, email=usuario.correo, primary=True, verified=False
    )
    Usuario.objects.filter(pk=usuario.pk).update(
        fecha_registro=date.today() - timedelta(days=dias)
    )
    return usuario


class PlazoTests(TestCase):
    """El corte no puede adelantarse al enlace: es de días enteros, por encima."""

    def test_una_pendiente_de_hoy_y_de_ayer_siguen_vigentes(self):
        hoy, ayer = pendiente(0), pendiente(1)
        self.assertEqual(liberar_pendientes_vencidas(), 0)
        self.assertTrue(Usuario.objects.filter(pk__in=[hoy.pk, ayer.pk]).count() == 2)

    def test_una_pendiente_de_hace_dos_dias_vence(self):
        vieja = pendiente(2)
        self.assertEqual(liberar_pendientes_vencidas(), 1)
        self.assertFalse(Usuario.objects.filter(pk=vieja.pk).exists())

    def test_se_borra_tambien_su_direccion_de_allauth(self):
        pendiente(2, correo="vieja@example.com")
        liberar_pendientes_vencidas()
        self.assertFalse(
            EmailAddress.objects.filter(email="vieja@example.com").exists()
        )

    def test_nunca_toca_cuentas_activas_ni_de_baja(self):
        activa = UsuarioFactory()
        baja = UsuarioFactory(estado=EstadoCuenta.BAJA)
        Usuario.objects.filter(pk__in=[activa.pk, baja.pk]).update(
            fecha_registro=date.today() - timedelta(days=400)
        )
        self.assertEqual(liberar_pendientes_vencidas(), 0)
        self.assertEqual(Usuario.objects.filter(pk__in=[activa.pk, baja.pk]).count(), 2)

    @override_settings(ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS=3)
    def test_el_plazo_sigue_al_del_enlace_de_confirmacion(self):
        pendiente(2)
        self.assertEqual(liberar_pendientes_vencidas(), 0)
        vieja = pendiente(4)
        self.assertEqual(liberar_pendientes_vencidas(), 1)
        self.assertFalse(Usuario.objects.filter(pk=vieja.pk).exists())

    def test_el_filtro_solo_libera_la_cuenta_que_ocupa_ese_dato(self):
        a = pendiente(2, correo="a@example.com")
        b = pendiente(2, correo="b@example.com")
        liberar_pendientes_vencidas(correo="A@example.com")
        self.assertFalse(Usuario.objects.filter(pk=a.pk).exists())
        self.assertTrue(Usuario.objects.filter(pk=b.pk).exists())


class TareaDeLimpiezaTests(TestCase):
    def test_borra_las_vencidas_y_conserva_las_vigentes(self):
        vieja, vigente = pendiente(3), pendiente(0)
        self.assertEqual(limpiar_pendientes_vencidas(), 1)
        self.assertFalse(Usuario.objects.filter(pk=vieja.pk).exists())
        self.assertTrue(Usuario.objects.filter(pk=vigente.pk).exists())

    def test_es_idempotente(self):
        pendiente(3)
        limpiar_pendientes_vencidas()
        self.assertEqual(limpiar_pendientes_vencidas(), 0)

    def test_esta_programada_a_diario_en_celery_beat(self):
        from django.conf import settings

        entrada = settings.CELERY_BEAT_SCHEDULE["limpiar-pendientes-vencidas"]
        self.assertEqual(entrada["task"], "usuarios.limpiar_pendientes_vencidas")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegistroSobrePendienteTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()

    def registrar(self, **cambios):
        return self.client.post(REGISTRO, cuerpo(**cambios), format="json")

    def test_dentro_del_plazo_el_registro_sobre_una_pendiente_se_rechaza(self):
        pendiente(1, correo="ana@example.com", nombre_usuario="otro12345")
        respuesta = self.registrar()
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["errors"][0]["code"], "email_already_used")

    def test_rechazar_no_cambia_la_contrasena_de_la_pendiente(self):
        vigente = pendiente(0, correo="ana@example.com", nombre_usuario="otro12345")
        antes = vigente.password
        self.registrar()
        vigente.refresh_from_db()
        self.assertEqual(vigente.password, antes)

    def test_vencida_el_correo_se_puede_registrar_y_la_clave_vieja_ya_no_sirve(self):
        vieja = pendiente(2, correo="ana@example.com", nombre_usuario="otro12345")
        respuesta = self.registrar()
        self.assertEqual(respuesta.status_code, 201)
        self.assertFalse(Usuario.objects.filter(pk=vieja.pk).exists())
        nueva = Usuario.objects.get(correo="ana@example.com")
        self.assertTrue(nueva.check_password("NuevaClave456!"))
        self.assertFalse(nueva.check_password("Password123!"))
        self.assertEqual(nueva.estado, EstadoCuenta.PENDIENTE)
        self.assertEqual(len(mail.outbox), 1)

    def test_vencida_tambien_se_libera_el_nombre_de_usuario(self):
        pendiente(2, correo="otra@example.com", nombre_usuario="ana12345")
        self.assertEqual(self.registrar().status_code, 201)
        self.assertEqual(Usuario.objects.filter(nombre_usuario="ana12345").count(), 1)

    def test_una_cuenta_activa_sigue_reservando_el_correo_aunque_sea_vieja(self):
        activa = UsuarioFactory(correo="ana@example.com", nombre_usuario="activa123")
        Usuario.objects.filter(pk=activa.pk).update(
            fecha_registro=date.today() - timedelta(days=400)
        )
        respuesta = self.registrar()
        self.assertEqual(respuesta.status_code, 400)
        self.assertTrue(Usuario.objects.filter(pk=activa.pk).exists())


class UsernameDisponibleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def disponible(self, nombre):
        return APIClient().get(DISPONIBLE, {"username": nombre}).json()["disponible"]

    def test_una_pendiente_vigente_ocupa_el_nombre(self):
        pendiente(1, nombre_usuario="reservado1")
        self.assertFalse(self.disponible("reservado1"))

    def test_una_pendiente_vencida_ya_no_lo_ocupa_y_el_chequeo_no_borra(self):
        vieja = pendiente(2, nombre_usuario="reservado1")
        self.assertTrue(self.disponible("reservado1"))
        self.assertTrue(Usuario.objects.filter(pk=vieja.pk).exists())


class AltaConGoogleSobrePendienteTests(TestCase):
    """El alta con Google comprueba el correo igual que el registro."""

    google = tests_contrato.ContratoErroresAPITests.google

    serializar = tests_contrato.ContratoErroresAPITests.serializar

    def serializar_tolerante(self, serializer):
        """Valida y devuelve el sobre de error si lo hay, o `None` si pasó."""
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            return tests_contrato.filmai_exception_handler(exc, {})
        return None

    def test_sobre_una_pendiente_vigente_se_rechaza_sin_tocarla(self):
        self.usuario = pendiente(1, correo="ana@example.com")
        antes = self.usuario.password
        respuesta = self.google("correo")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["errors"][0]["code"], "email_already_used")
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.password, antes)

    def test_sobre_una_pendiente_vencida_la_libera_y_no_rechaza_por_el_correo(self):
        self.usuario = pendiente(2, correo="ana@example.com")
        self.serializar = self.serializar_tolerante
        resultado = self.google("correo")
        self.assertFalse(Usuario.objects.filter(pk=self.usuario.pk).exists())
        codigos = [e["code"] for e in getattr(resultado, "data", {}).get("errors", [])]
        self.assertNotIn("email_already_used", codigos)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ReenvioNoRenuevaElPlazoTests(TestCase):
    """Reenviar el enlace no alarga la vida de la cuenta (si no, F4 no cerraría)."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def reenviar(self, correo):
        return APIClient().post(
            "/api/auth/registration/resend-email/", {"email": correo}, format="json"
        )

    def test_reenviar_a_una_pendiente_vigente_manda_el_correo_pero_no_cambia_la_fecha(
        self,
    ):
        vigente = pendiente(1, correo="ana@example.com")
        self.assertEqual(self.reenviar("ana@example.com").status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        vigente.refresh_from_db()
        self.assertEqual(vigente.fecha_registro, date.today() - timedelta(days=1))

    def test_pasado_el_corte_la_cuenta_se_borra_aunque_se_haya_reenviado_antes(self):
        vigente = pendiente(1, correo="ana@example.com")
        self.reenviar("ana@example.com")
        Usuario.objects.filter(pk=vigente.pk).update(
            fecha_registro=date.today() - timedelta(days=2)
        )
        self.assertEqual(liberar_pendientes_vencidas(), 1)
        mail.outbox.clear()
        cache.clear()  # el enfriamiento de 1 minuto entre reenvíos no es lo que se prueba
        self.assertEqual(self.reenviar("ana@example.com").status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
