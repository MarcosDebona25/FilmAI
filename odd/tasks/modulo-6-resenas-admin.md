# Módulo 6 — Reseñas de prueba para el Django Admin

## Objetivo

Cerrar los detalles operativos del Módulo 6 (AD-01', gestión de reseñas en el Django Admin): que la base de desarrollo tenga calificaciones y reseñas **sin destruir el catálogo protegido** (195 producciones pobladas por `seed_catalogo`), que el `seed` sea replicable por el otro desarrollador y que los datos sembrados cumplan las relaciones y restricciones de negocio.

## Problema

- El `ResenaAdmin` y `UsuarioAdmin` están implementados y con 10 tests (`catalogo/test_admin.py`), pero la BD de desarrollo tiene **0 calificaciones y 0 reseñas**.
- `python manage.py seed` crea reseñas, pero **se niega** a correr cuando el catálogo supera las 100 producciones (guard de C-04c), y forzarlo con `--borrar-catalogo` destruye horas de llamadas a TMDB y las cuentas no-staff.
- Además `seed` hoy borraría el superusuario (`_limpiar()` hace `Usuario.objects.all().delete()`), contradiciendo el README.

## Alcance autorizado

- Backend: `backend/usuarios/management/commands/seed.py` y `backend/usuarios/tests.py`.
- Documentación: README, `docs/decisiones.md`, `docs/05_Plan_de_Desarrollo.md` (fila AD-01'), `docs/reportes_dev/explicacion-modulo-6-admin.md`.
- Ejecutar el nuevo modo en la BD de desarrollo local y verificar.
- **No tocar** `frontend/app/perfil/page.tsx` (cambio ajeno en el working tree).

## Decisiones (acordadas con el usuario)

1. **`seed --solo-resenas`** (modo no destructivo dentro del propio `seed`, elegido por el usuario): crea calificaciones y reseñas sobre el catálogo y los usuarios de desarrollo existentes, sin resetear nada. Pertenece al seed para que Gonza lo replique con el mismo comando.
2. Los usuarios objetivo son las cuentas de desarrollo del seed: `estado=ACTIVA`, `is_staff=False`, correo `@filmai.com`.
3. Idempotente: saltea pares `(usuario, produccion)` ya calificados (respeta `uq_calificacion_usuario_produccion`).
4. **1 de cada 7 reseñas nace `activa=False`** (moderada): da ejemplos reales al Admin para filtrar/desactivar/reactivar (CU-017).
5. `seed` completo conserva las cuentas `is_staff` (superusuario del entrypoint) y sus `EmailAddress`, como promete el README.

## Tareas

- [x] T1: implementar `--solo-resenas` en `seed.py` (rama en `handle`, `_solo_resenas()`, errores con `CommandError`)
- [x] T2: idempotencia + regla 1/7 inactivas en `_crear_calificaciones_y_resenas`
- [x] T3: `_limpiar()` conserva staff
- [x] T4: tests (modo solo, idempotencia, inactivas, abortos, superusuario preservado, restricciones del seed completo)
- [x] T5: verificación — suite completa (388 OK) + ruff limpio
- [x] T6: docs (README, decisiones, plan AD-01', reporte módulo 6)
- [x] T7: ejecutar `seed --solo-resenas` en la BD dev + chequeo E2E (SQL de restricciones + API comunidad/mías + Admin) — 34 calificaciones, 20 reseñas, 2 inactivas, todo OK
- [ ] T8: `graphify update .`

## Criterios de aceptación

- `seed --solo-resenas` crea calificaciones 1–10 y reseñas ≤1000 caracteres sobre el catálogo existente sin tocarlo, y se puede correr N veces sin duplicar pares.
- Alguna reseña queda `activa=False` para demostrar la moderación; el Admin las lista todas (filtro activa/No).
- `seed --borrar-catalogo` NO elimina el superusuario.
- Suite de tests completa en verde, ruff limpio, docs actualizadas.

## Nota de espejo

Engram pendiente: `mem_save` rechazó por ambigüedad de sesión activa (30/09). Resincronizar con topic_key `odd/modulo-6-resenas-admin/tasks` cuando haya una sesión única.

## Verificación

| Comando | Resultado |
| --- | --- |
| `docker compose exec backend python manage.py test --noinput` | 388 tests, OK |
| `ruff format backend && ruff check backend` | limpio |
| `seed --solo-resenas` en BD dev + script de chequeo SQL/API | 34 calificaciones, 20 reseñas, 2 inactivas; E2E OK |
