"""Vencimiento de las cuentas pendientes de confirmación (F4 de la auditoría).

Una cuenta `PENDIENTE` reserva su correo y su nombre de usuario. Sin
vencimiento, quien registre el correo de otra persona lo bloquea para siempre.
Por eso una pendiente deja de reservar cuando pasó el plazo del enlace de
confirmación (`ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS`).

`Usuario` solo guarda el día de registro (`fecha_registro`, sin hora), así que
el corte es por días enteros: se libera la cuenta registrada antes de
`hoy - plazo`. Una cuenta registrada a las 23:59 vive hasta pasadas 24 horas,
nunca menos que el primer enlace; en el peor caso reserva casi 48 horas.

El plazo cuenta desde el registro y no se renueva al reenviar el enlace: si se
renovara, quien registra un correo ajeno podría reservarlo para siempre pidiendo
reenvíos. Un enlace reenviado cerca del corte puede, por eso, vencer antes que
su plazo propio (la cuenta ya no existe y la persona debe registrarse de nuevo).
"""

import logging
from datetime import date, timedelta

from allauth.account import app_settings as allauth_account_settings

from .models import EstadoCuenta, Usuario

logger = logging.getLogger(__name__)


def pendientes_vencidas():
    """Cuentas pendientes cuyo plazo de confirmación ya pasó."""
    # `auto_now_add` de un DateField escribe `date.today()` (reloj del proceso, no
    # `timezone.localdate()`): se compara contra la misma fuente para no
    # desfasar el corte si el reloj del contenedor y TIME_ZONE difieren.
    plazo = timedelta(days=allauth_account_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS)
    return Usuario.objects.filter(
        estado=EstadoCuenta.PENDIENTE,
        fecha_registro__lt=date.today() - plazo,
    )


def liberar_pendientes_vencidas(*, correo=None, nombre_usuario=None):
    """Borra las pendientes vencidas; con filtros, solo las que ocupan ese dato.

    Se llama antes de comprobar si un correo o un nombre de usuario están
    tomados, para que una pendiente vencida no los siga reservando aunque la
    limpieza diaria todavía no haya corrido. Devuelve cuántas borró.
    """
    cuentas = pendientes_vencidas()
    if correo is not None or nombre_usuario is not None:
        coincide = Usuario.objects.none()
        if correo is not None:
            coincide = coincide | cuentas.filter(correo__iexact=correo)
        if nombre_usuario is not None:
            coincide = coincide | cuentas.filter(nombre_usuario__iexact=nombre_usuario)
        cuentas = coincide
    # `delete()` arrastra el `EmailAddress` de allauth (cascada).
    _, detalle = cuentas.delete()
    borradas = detalle.get(Usuario._meta.label, 0)
    if borradas:
        logger.info("Cuentas pendientes vencidas liberadas: %d", borradas)
    return borradas
