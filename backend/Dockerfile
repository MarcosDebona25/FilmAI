# =============================================================================
# FilmAI Backend — Dockerfile
# =============================================================================
# Etapas:
#   1. Imagen base (Python 3.12)
#   2. Variables de entorno Python
#   3. Instalación de dependencias del sistema
#   4. Copia e instalación de dependencias Python
#   5. Copia del código
#   6. Configuración del entrypoint
# =============================================================================

FROM python:3.12-slim

# --- Variables de entorno de Python ---
# PYTHONDONTWRITEBYTECODE: no genera archivos .pyc (evita basura en el volumen montado)
# PYTHONUNBUFFERED: stdout/stderr no se buferizan (logs en tiempo real)
# PYTHONPATH: agrega /app al path para que los imports funcionen
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# --- Dependencias del sistema ---
# postgresql-client: necesario para que psycopg2 se comunique con PostgreSQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# --- Dependencias Python ---
# Copiamos requirements.txt PRIMERO (sin el código) para que Docker cachee
# esta capa: mientras requirements.txt no cambie, no reinstala dependencias.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Código de la aplicación ---
# Se copia al final porque cambia frecuentemente. En desarrollo usamos un
# volumen montado que pisa esta copia, así que esto es más para producción.
COPY . .

# --- Entrypoint ---
# El entrypoint se ejecuta SIEMPRE antes del comando principal.
# Espera a que la DB esté lista, corre migraciones, crea superuser.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
