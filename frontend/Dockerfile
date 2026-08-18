# =============================================================================
# FilmAI Frontend — Dockerfile (Next.js 15 + Tailwind + Shadcn)
# =============================================================================
# Estrategia de capas:
#   1. package.json PRIMERO → Docker cachea node_modules si no cambian dependencias
#   2. Copia del código DESPUÉS
#   3. El volumen montado en docker-compose.yml pisa esta copia en desarrollo
# =============================================================================

FROM node:22-alpine

WORKDIR /app

# --- Variables de entorno por defecto ---
ENV NEXT_TELEMETRY_DISABLED=1

# --- Dependencias ---
# Copiamos package.json y package-lock.json PRIMERO para aprovechar la caché
COPY package.json package-lock.json* ./
RUN npm install

# --- Código ---
# En desarrollo, el volumen montado (./frontend:/app) pisa este COPY,
# así que los cambios en el host se reflejan al instante.
COPY . .

# --- Puerto de desarrollo ---
EXPOSE 3000

# --- Comando ---
CMD ["npm", "run", "dev"]
