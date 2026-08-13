# AGENTS.md — Reglas para agentes que trabajan en FilmIA

Instrucciones obligatorias para cualquier agente (o asistente de IA) que trabaje
en este repositorio.

## 1. Registro de decisiones y cambios

- Todo cambio relevante de diseño, arquitectura o implementación debe quedar
  anotado en **`docs/decisiones.md`** (archivo markdown).
- Formato de cada entrada:
  - **Fecha** (DD/MM/AAAA)
  - **Título** breve
  - **Descripción**: qué se decidió/cambió, por qué, y qué archivos se vieron
    afectados.
- No dar por cerrada una decisión de diseño sin registrarla en ese archivo.

## 2. Consultar la documentación

- Antes de implementar o modificar algo, leer la documentación de dominio en
  `docs/` (archivos 01 a 05) como fuente de verdad.
- El código debe ser consistente con la documentación. Si divergen, actualizar
  la documentación para reflejar el estado real (o acordar el cambio primero).

## 3. Ante ambigüedad, consultar al usuario

- Si algo en la documentación o en los requerimientos es ambiguo, contradictorio
  o poco claro, **NO asumir**: preguntar al usuario a través del chat.
- Nunca tomar decisiones de diseño unilaterales cuando la documentación no es clara.

## Contexto técnico

- **Backend**: Django 5.1 + Django REST Framework, PostgreSQL 16, Redis, Celery
  (todo en Docker, `docker compose`).
- **Frontend**: Next.js + Tailwind + Shadcn.
- **Modelo de usuario**: `usuarios.Usuario` como `AUTH_USER_MODEL`
  (detalles en `docs/decisiones.md`).
