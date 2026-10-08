"""Persistencia de contraseñas y notificación posterior al commit."""

import logging

from django.db import transaction

from filmai.correos.servicio import enviar_correo
from filmai.idioma import idioma_efectivo

logger = logging.getLogger(__name__)


def notificar_cambio_contrasena(usuario, idioma):
    try:
        enviar_correo(
            "contrasena_actualizada", usuario.correo, {"user": usuario}, idioma
        )
    except Exception:
        # La contraseña ya está confirmada: un fallo de correo no revierte el cambio.
        logger.exception("No se pudo enviar la notificación de cambio de contraseña")


def guardar_contrasena(usuario, password, request=None):
    """El hash nuevo invalida los access y refresh emitidos con el anterior."""
    # Se resuelve ahora: al confirmar la transacción el request ya no importa.
    idioma = idioma_efectivo(request, usuario)
    usuario.set_password(password)
    usuario.save(update_fields=["password"])
    transaction.on_commit(lambda: notificar_cambio_contrasena(usuario, idioma))
