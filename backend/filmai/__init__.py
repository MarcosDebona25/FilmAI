"""Paquete del proyecto Django.

Importar la app de Celery acá hace que quede disponible apenas Django
arranca, que es lo que permite registrar las tareas declaradas con
`@shared_task` en las apps (ver `filmai/celery.py`).
"""

from filmai.celery import app as celery_app

__all__ = ("celery_app",)
