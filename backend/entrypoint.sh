#!/bin/bash
# =============================================================================
# FilmAI Backend — Entrypoint
# =============================================================================
# Se ejecuta cada vez que el contenedor arranca, ANTES del comando del
# servicio (el `command:` del docker-compose, o el CMD del Dockerfile):
#   1. Espera a que PostgreSQL esté listo            (todos los servicios)
#   2. Corre migraciones + crea superuser            (solo si RUN_MIGRATIONS)
#   3. Ejecuta el comando recibido                   (`exec "$@"`)
#
# RUN_MIGRATIONS existe porque este mismo entrypoint lo usan varios servicios
# (backend, celery-worker): si todos migraran, varios contenedores tocarían la
# misma base a la vez. Migra únicamente el backend.
# =============================================================================
set -e

echo "⏳ Esperando a PostgreSQL en db:5432..."
until PGPASSWORD="${POSTGRES_PASSWORD}" pg_isready \
    -h db -p 5432 \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}"; do
  sleep 1
done
echo "✅ PostgreSQL está listo."

if [ "${RUN_MIGRATIONS:-true}" != "true" ]; then
  echo "⏭️  RUN_MIGRATIONS=${RUN_MIGRATIONS}: se omiten migraciones y superuser."
  echo "🚀 Ejecutando: $*"
  exec "$@"
fi

echo "⏳ Aplicando migraciones..."
python manage.py migrate --noinput

echo "⏳ Creando superuser si no existe..."
# El Python va en un heredoc entrecomillado (<<'PY'): el shell no interpola
# nada dentro. Los datos del superusuario los lee Python de `os.environ`; así
# una comilla en la contraseña no rompe el script ni se ejecuta como código, y
# la contraseña no aparece en la lista de procesos (`ps`).
python manage.py shell <<'PY'
import os

from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
email = os.environ["DJANGO_SUPERUSER_EMAIL"]
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
if not User.objects.filter(correo=email).exists():
    User.objects.create_superuser(
        correo=email,
        nombre_usuario=username,
        nombre='Admin',
        apellido='FilmAI',
        fecha_nacimiento='2000-01-01',
        genero='no_especifica',
        password=password,
    )
    print(f'Superuser {email} creado.')
else:
    print(f'Superuser {email} ya existe.')
PY

# `exec "$@"` ejecuta el comando del servicio (CMD del Dockerfile para el
# backend: runserver; `command:` del compose para el celery-worker).
echo "🚀 Ejecutando: $*"
exec "$@"
