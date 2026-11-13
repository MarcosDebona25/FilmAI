"""Tareas de Celery del chatbot (#180, PR 3)."""

from celery import shared_task

from chatbot.recorte import recortar


@shared_task(name="chatbot.recortar_tarjetas")
def recortar_tarjetas():
    """Recorta lo que TMDB no deja guardar más de 180 días.

    Corre a las 04:30, después del refresco del catálogo (03:30): para cuando
    rehidrata el historial, las filas que lo alimentan ya están al día. Es
    idempotente: una segunda corrida no encuentra nada que recortar.
    """
    return recortar()
