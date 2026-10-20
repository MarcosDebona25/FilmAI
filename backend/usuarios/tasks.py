"""Tareas de Celery de las cuentas (F4 de la auditoría)."""

from celery import shared_task

from .pendientes import liberar_pendientes_vencidas


@shared_task(name="usuarios.limpiar_pendientes_vencidas")
def limpiar_pendientes_vencidas():
    """Borra las cuentas que nunca confirmaron su correo.

    Además de liberar el correo, evita guardar datos personales de quien nunca
    completó el registro. Es idempotente: correrla dos veces no rompe nada.
    """
    return liberar_pendientes_vencidas()
