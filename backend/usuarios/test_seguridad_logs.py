"""F8 de la auditoría: la clave de confirmación de correo quedaba en el log.

La clave del enlace es un secreto de un solo uso: quien la lea en un log puede
confirmar la cuenta (y fijar su estado) durante el día que dura. Los logs suelen
viajar a herramientas de terceros, así que no deben contenerla.
"""

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.test import TestCase
from rest_framework.test import APIClient

from .factories import UsuarioFactory
from .models import EstadoCuenta

VERIFICAR = "/api/auth/registration/verify-email/"


class ClaveDeConfirmacionEnLogsTests(TestCase):
    def setUp(self):
        usuario = UsuarioFactory(estado=EstadoCuenta.PENDIENTE)
        direccion = EmailAddress.objects.create(
            user=usuario, email=usuario.correo, primary=True, verified=False
        )
        self.clave = EmailConfirmationHMAC(direccion).key

    def mensajes(self, clave):
        with self.assertLogs("usuarios", level="DEBUG") as capturado:
            APIClient().post(VERIFICAR, {"key": clave}, format="json")
        return [registro.getMessage() for registro in capturado.records]

    def assertSinClave(self, mensajes, clave):
        self.assertTrue(mensajes, "el test no capturó ningún mensaje")
        for mensaje in mensajes:
            self.assertNotIn(clave, mensaje)
            # Tampoco fragmentos: el timestamp o la firma por separado.
            for trozo in clave.split(":"):
                if len(trozo) >= 6:
                    self.assertNotIn(trozo, mensaje)

    def test_una_clave_valida_no_aparece_en_el_log(self):
        self.assertSinClave(self.mensajes(self.clave), self.clave)

    def test_una_clave_con_firma_invalida_no_aparece_en_el_log(self):
        adulterada = self.clave[:-4] + "AAAA"
        self.assertSinClave(self.mensajes(adulterada), adulterada)

    def test_una_clave_mal_formada_no_aparece_en_el_log(self):
        basura = "secreto-que-no-debe-salir-en-el-log"
        self.assertSinClave(self.mensajes(basura), basura)

    def test_el_log_conserva_lo_util_para_depurar(self):
        """Se puede seguir diagnosticando sin el valor: largo y motivo."""
        mensajes = self.mensajes(self.clave)
        self.assertTrue(any(f"len={len(self.clave)}" in m for m in mensajes), mensajes)
