"""Tarea de Celery que envía los correos de cuenta (Q-08, issue #181).

`enviar_correo()` (`filmai/correos/servicio.py`) renderiza el correo dentro del
pedido HTTP y encola esta tarea; el worker la toma y habla con el proveedor.
Así el visitante no espera a Resend ni a Brevo, y un proveedor caído se reintenta
en segundo plano en vez de dejar al usuario sin correo.

La tarea recibe solo texto (caso, asunto, cuerpo, HTML, destinatario) y no lee la
base de datos: por eso puede encolarse dentro de la transacción del registro sin
carrera con el commit (el worker no necesita ver la cuenta).

Privacidad: los logs de la tarea llevan el caso y el id de la tarea, nunca el
destinatario ni los enlaces. El resultado no se guarda (`ignore_result`) y el
`argsrepr` con que se encola está redactado.
"""

import logging

from celery import Task, shared_task
from django.conf import settings
from django.core.mail import send_mail

from filmai.email_backends import EnvioFallido

logger = logging.getLogger(__name__)

# Reintentos con espera exponencial: 1, 2, 4, 8, 16 y 30 minutos (tope), y otra
# vez 30 minutos hasta el reintento 8. Con `retry_jitter` cada espera es un valor
# al azar entre 0 y ese tope, así que el promedio total ronda 1 hora y el peor
# caso 2 horas: muy por debajo de las 24 horas de vigencia del enlace de
# confirmación. El jitter evita que, al volver Resend, todos los correos
# acumulados salgan en el mismo segundo.
REINTENTO_BASE_SEGUNDOS = 60
REINTENTO_TOPE_SEGUNDOS = 1800
MAX_REINTENTOS = 8


class _TareaDeCorreo(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Se agotaron los reintentos o el error no era reintentable."""
        caso = args[0] if args else "desconocido"
        # `exc` es un EnvioFallido o ErrorDeProveedor: su texto lleva solo el
        # proveedor y el estado HTTP, nunca el destinatario.
        logger.error(
            "Correo de cuenta NO enviado (caso=%s tarea=%s): %s", caso, task_id, exc
        )


@shared_task(
    bind=True,
    base=_TareaDeCorreo,
    name="filmai.enviar_correo",
    # Solo `EnvioFallido` (todos los proveedores con fallo transitorio) se
    # reintenta. Un `ErrorDeProveedor` (400 o 422: datos inválidos) falla igual
    # la próxima vez y se corta en el acto.
    autoretry_for=(EnvioFallido,),
    retry_backoff=REINTENTO_BASE_SEGUNDOS,
    retry_backoff_max=REINTENTO_TOPE_SEGUNDOS,
    retry_jitter=True,
    max_retries=MAX_REINTENTOS,
    # El resultado no sirve para nada y llevaría datos al backend de resultados.
    ignore_result=True,
    # Se confirma el mensaje al terminar, no al recibirlo: si el worker muere a
    # mitad de camino el correo se reentrega (un duplicado es inofensivo; un
    # correo perdido deja la cuenta sin confirmar).
    acks_late=True,
    reject_on_worker_lost=True,
)
def enviar_correo_tarea(self, caso, asunto, texto, html, destinatario):
    """Envía un correo ya renderizado con el `EMAIL_BACKEND` configurado."""
    enviados = send_mail(
        asunto, texto, settings.DEFAULT_FROM_EMAIL, [destinatario], html_message=html
    )
    if not enviados:
        # El backend ya logueó el motivo (p. ej. sin clave de ningún proveedor).
        logger.error(
            "Correo de cuenta NO enviado (caso=%s tarea=%s)", caso, self.request.id
        )
        return
    logger.info("Correo de cuenta enviado (caso=%s tarea=%s)", caso, self.request.id)
