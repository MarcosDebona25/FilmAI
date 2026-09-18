# AGENTS.md — Reglas para agentes que trabajan en FilmAI

Instrucciones obligatorias para cualquier agente (o asistente de IA) que trabaje en este repositorio.

## 1. Registro de decisiones y cambios

- Todo cambio relevante de diseño, arquitectura o implementación debe quedar anotado en **`docs/decisiones.md`** (archivo markdown).
- Formato de cada entrada:
  - **Fecha** (DD/MM/AAAA)
  - **Título** breve
  - **Descripción**: qué se decidió/cambió, por qué, y qué archivos se vieron afectados.
- No dar por cerrada una decisión de diseño sin registrarla en ese archivo.

## 2. Consultar la documentación

- Antes de implementar o modificar algo, leer la documentación de dominio en `docs/` (archivos 01 a 06) como fuente de verdad.
- El código debe ser consistente con la documentación. Si divergen, actualizar la documentación para reflejar el estado real (o acordar el cambio primero).

## 3. Ante ambigüedad, consultar al usuario

- Si algo en la documentación o en los requerimientos es ambiguo, contradictorio o poco claro, **NO asumir**: preguntar al usuario a través del chat.
- Nunca tomar decisiones de diseño unilaterales cuando la documentación no es clara.

## 4. Antes de dar el OK al usuario

- Correr el formateo/lint en ambos proyectos y asegurar que pasa limpio antes de declarar terminada una consulta/tarea:
  - Backend: `ruff format . && ruff check .`
  - Frontend: `npx prettier --check .` (o `npm run format:check`)
- No declarar "listo" si hay archivos sin formatear.

## 5. Tests unitarios

- Al implementar nueva funcionalidad o corregir bugs, crear o actualizar los tests unitarios correspondientes.
- Ejecutar los tests (`python manage.py test` en el backend) antes de declarar terminada una tarea para asegurar que no se rompen tests existentes (regresión).

## 6. Consultar skills disponibles

- La única fuente de skills del proyecto es `.agents/skills/`. Antes de iniciar
  una implementación, Codex, OpenCode y Antigravity CLI deben revisar la skill
  aplicable allí. No crear ni copiar skills en directorios específicos de un
  harness, como `.opencode/skills/`.
 - Skills disponibles:
   - **conventional-commits**: redactar mensajes de commit convencionales.
   - **explicar-al-implementar**: explicar conceptos, arquitectura y tests mientras se construye (siempre activa; el equipo está aprendiendo los frameworks del stack).
   - **humanizer**: eliminar señales de escritura generada por IA en textos.
   - **impeccable**: diseño, rediseño y auditoría de interfaces frontend.
   - **vercel-quality**: checklist de calidad post-implementación para frontend.
 - Usar la skill correspondiente cuando la tarea lo requiera.

## 7. Uso y mantenimiento del grafo de conocimiento (graphify)

- **Consulta previa obligatoria**: antes de realizar búsquedas abiertas o exploraciones amplias de archivos (`grep`, `find`, lecturas masivas) para entender arquitectura, relaciones entre módulos o flujo de llamadas, el agente DEBE consultar `graphify-out/GRAPH_REPORT.md` (o `graphify-out/graph.json`) para orientar la búsqueda y ahorrar tokens identificando directamente los hubs y dependencias relevantes.
- **Actualización periódica**: ejecutar `graphify update .` al finalizar una tarea que haya creado o modificado archivos relevantes (código, docs, specs, config), ANTES de dar el OK al usuario o de crear el commit, de modo que el grafo actualizado quede versionado en el mismo commit.
- `graphify update .` es incremental: solo re-extrae los archivos nuevos/modificados y no requiere LLM cuando los cambios son solo de código.
- `graphify-out/` se versiona en git (salvo `cache/`, `.graphify_python`, `.graphify_root` y los backups automáticos, que están en `.gitignore`).

## 8. AI Review desactivado

- **No se usa AI Review en los pull requests**. El workflow de AI Review fue desactivado el 18/09/2026 debido a que generaba un 93% de falsos positivos (comentarios que no detectaban bugs reales ni sugerían mejoras válidas).
- **Motivo**: Los comentarios de AI Review no tenían contexto del proyecto (convenciones de idioma, valores de configuración, arquitectura), lo que resultaba en sugerencias genéricas e incorrectas para el caso específico de FilmAI.
- **Alternativa**: La revisión de código se hace manualmente por los maintainers del proyecto, con apoyo de los skills disponibles (ver sección 6) y la documentación de dominio en `docs/`.

## 9. Estructura de documentación

- **`docs/`**: Documentación de dominio (requerimientos, modelos de datos, UI, decisiones de diseño, plan de desarrollo). Es la fuente de verdad del proyecto.
- **`openspec/specs/`**: Especificaciones canónicas de cada módulo (qué hace, requisitos, escenarios). Son útiles como referencia rápida.
- **`openspec/changes/`**: Solo contiene cambios activos en progreso. Los cambios completados se archivan (se eliminan) porque la información de decisiones ya está registrada en `docs/decisiones.md`.
- **`graphify-out/`**: Grafo de conocimiento del código (ver sección 7).

## Contexto técnico

- **Backend**: Django 5.1 + Django REST Framework, PostgreSQL 16, Redis, Celery (todo en Docker, `docker compose`).
- **Frontend**: Next.js + Tailwind + Shadcn.
- **Modelo de usuario**: `usuarios.Usuario` como `AUTH_USER_MODEL` (detalles en `docs/decisiones.md`).
