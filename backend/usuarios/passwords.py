"""Persistencia de contraseñas y notificación posterior al commit."""

import logging

from django.db import transaction

from filmai.correos.servicio import enviar_correo

logger = logging.getLogger(__name__)


def notificar_cambio_contrasena(usuario):
    try:
        enviar_correo("contrasena_actualizada", usuario.correo, {"user": usuario}, "es")
    except Exception:
        # La contraseña ya está confirmada: un fallo de correo no revierte el cambio.
        logger.exception("No se pudo enviar la notificación de cambio de contraseña")


def guardar_contrasena(usuario, password):
    """El hash nuevo invalida los access y refresh emitidos con el anterior."""
    usuario.set_password(password)
    usuario.save(update_fields=["password"])
    transaction.on_commit(lambda: notificar_cambio_contrasena(usuario))
