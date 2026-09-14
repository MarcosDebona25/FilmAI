"""App de Celery del proyecto (C-04a).

Celery corre en un proceso aparte del servidor web (servicio `celery-worker`
en `docker-compose.yml`), así que necesita saber por su cuenta dónde está la
configuración de Django: de ahí el `DJANGO_SETTINGS_MODULE` de abajo.

La app se expone en `filmai/__init__.py` para que Django la cargue al
arrancar y las tareas declaradas con `@shared_task` queden registradas.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "filmai.settings")

app = Celery("filmai")

# `namespace="CELERY"` = toma de settings.py solo las variables que empiezan
# con CELERY_ (CELERY_BROKER_URL → broker_url, etc.).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Busca un `tasks.py` en cada app de INSTALLED_APPS y registra lo que
# encuentre (ej. `catalogo/tasks.py`, que llega en la Fase 4 de C-04a).
app.autodiscover_tasks()
