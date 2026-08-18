#!/bin/bash
# =============================================================================
# FilmAI Backend — Entrypoint
# =============================================================================
# Se ejecuta cada vez que el contenedor arranca:
#   1. Espera a que PostgreSQL esté listo
#   2. Corre las migraciones pendientes
#   3. Crea el superuser de Django si no existe
#   4. Arranca el servidor de desarrollo
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

echo "⏳ Aplicando migraciones..."
python manage.py migrate --noinput

echo "⏳ Creando superuser si no existe..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
username = '${DJANGO_SUPERUSER_USERNAME}'
email = '${DJANGO_SUPERUSER_EMAIL}'
password = '${DJANGO_SUPERUSER_PASSWORD}'
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
"

echo "🚀 Servidor Django escuchando en 0.0.0.0:8000 (accedé en http://localhost:8000)"
exec python manage.py runserver 0.0.0.0:8000
