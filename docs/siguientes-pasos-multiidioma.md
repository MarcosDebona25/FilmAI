# Plan multiidioma — estado y siguientes pasos

Actualizado el 08/10/2026. Reemplaza a `cierre-parcial-2026-10-08.md` como punto
de entrada para retomar el trabajo. El detalle de cada orden de trabajo (OT)
sigue en `docs/plan-multiidioma.md` (tabla 10.4 y notas 10.5) y las decisiones
en `docs/decisiones.md`.

## 1. Dónde estamos

**El backend del plan está terminado** (fases F2 a F6). Todo vive en la rama
`develop`; `main` no recibió ningún merge.

| Fase | Qué cubre                                            | Estado                        |
| ---- | ---------------------------------------------------- | ----------------------------- |
| F0   | Línea base y red de seguridad                        | Cerrada                       |
| F1   | Contrato, glosario, claves y copia                   | Cerrada                       |
| F2   | `Usuario.idioma`, `idioma_efectivo`, preferencias    | Cerrada                       |
| F3   | Errores con códigos estables (OT-30 a OT-34)         | Cerrada                       |
| F4   | Listas por `clave` y restricciones (OT-40 a OT-42)   | Cerrada                       |
| F5   | Correos localizados (OT-50 a OT-53)                  | Cerrada (falta revisión manual) |
| F6   | TMDB por idioma (OT-60 a OT-63)                      | Cerrada                       |
| F7   | Frontend, infraestructura                            | Solo OT-70 hecha              |
| F8   | Frontend, pruebas y cierre del contrato              | Pendiente                     |
| F9   | Documentación y cierre                               | Pendiente                     |

Qué expone hoy el backend para el frontend:

- **Errores**: sobre `{code, params, errors, debug?}` en todo 4xx/5xx, junto a
  las claves anteriores (`detail`, `codigo`, claves de campo). Contrato en
  `contracts/error-codes.json` y en `contracts/openapi.yaml` (`ErrorEnvelope`).
- **Éxitos con texto**: llevan `code` además de `detail`.
- **Login**: `account_deactivated` / `account_pending_confirmation` solo con
  credenciales correctas; si no, `invalid_credentials`.
- **Listas**: `clave` en la API, nombres reservados en ambos idiomas,
  `contracts/enums.json`.
- **Correos**: los cuatro casos en `en`/`es`, en el idioma del destinatario.
- **Catálogo**: `Accept-Language` decide `en-US`/`es-MX`; fuera del inglés cada
  detalle y cada ítem de listado trae `campos_en_ingles` (lista de campos
  completados con inglés, para marcar `lang="en"`); `GET /api/catalogo/genres/`
  da los géneros por idioma; listas y «mis reseñas» devuelven título y póster
  traducidos.

## 2. Pendientes antes de seguir con el frontend

Son chicos, pero conviene cerrarlos primero:

1. **Publicar `develop` y mirar el CI.** Todo lo de esta etapa se verificó en
   local (suite backend completa, ruff, `makemigrations --check`). El CI
   (ruff + suite + Playwright + `tsc` + `next build`) todavía no corrió sobre
   estos commits.
2. **Correr lo que no se ejecutó en local**: `npx playwright test`,
   `npx tsc --noEmit` y `next build` (el frontend no se tocó, pero el contrato
   de la API cambió por adición).
3. **Revisar los correos en un cliente real** (plan 10.1): con
   `RESEND_TEST_RECIPIENT`, enviar los 4 casos en `en` y `es`.
4. **Rellenar las traducciones de la base de desarrollo**:
   `docker compose exec backend python manage.py rellenar_traducciones`
   (quedaron 88 producciones pendientes; la sincronización nocturna también las
   va completando de a 100).
5. **`admin` no tiene listas predeterminadas** en la base de desarrollo
   (se creó sin la señal): `python manage.py reparar_recursos_usuarios`.
6. Decidir si el docstring de `FronteraErroresMixin`, que hoy aparece como
   `description` de dos esquemas en `openapi.yaml`, se oculta del contrato.

## 3. Siguientes órdenes de trabajo

En este orden (dependencias en la tabla 10.4 del plan):

### F7 — frontend, infraestructura (aquí empieza lo visible)

| OT    | Qué hay que hacer                                                                 | Depende de          |
| ----- | --------------------------------------------------------------------------------- | ------------------- |
| OT-71 | `lib/format.ts` y reemplazo de los usos de `es-AR`                                | OT-70               |
| OT-72 | `Accept-Language` en cada request, `ApiError` con códigos, `lib/errors.ts`, API simulada de e2e | OT-70, OT-34 (lista) |
| OT-73 | Validaciones por código y etiquetas desde `contracts/enums.json`                  | OT-72               |
| OT-74 | Selector de idioma (ubicaciones: ver `docs/04`, 4.1), sincronización cookie ↔ cuenta, locale del botón de Google | OT-70, OT-20        |
| OT-75 | Rutas en inglés en frontend, backend y tests, **en un solo PR**                   | OT-70               |
| OT-76 | Tres pantallas piloto migradas                                                    | OT-73, OT-74, OT-75 |
| OT-77 | Catálogos completos sembrados desde `docs/i18n/claves.csv`                        | OT-70               |

Notas para F7:

- OT-72 debe leer `code`/`errors` y **nunca** `debug`; el mapeo
  `retry_after_seconds` → `retryAfterSeconds` va centralizado.
- OT-75 toca también el backend: los enlaces de los correos usan hoy
  `/confirmar-correo/` y `/restablecer-contrasena/`
  (`usuarios/adapter.py`, `usuarios/serializers.py`) y la notificación de
  contraseña enlaza a `/login/`. Las referencias de correo se regeneran ahí.
- El frontend debe marcar `lang="en"` en los campos listados en
  `campos_en_ingles` y usar `GET /api/catalogo/genres/` para las etiquetas.

### F8 — pruebas y cierre del contrato

| OT    | Qué hay que hacer                                                             |
| ----- | ----------------------------------------------------------------------------- |
| OT-80 | Paridad de catálogos `en`/`es`, reglas de lint, script de residuos de español |
| OT-81 | Selectores independientes del idioma y recorrido e2e en ambos idiomas         |
| OT-82 | Tests del backend afirmando por código (hoy muchos afirman por texto)         |
| OT-83 | **Eliminar el formato anterior de errores** (`detail`, `codigo`, claves de campo) y el `detail` de los éxitos |

OT-83 solo puede hacerse cuando el frontend ya no lea las claves anteriores.

### F9 — documentación y cierre

- OT-90: alinear `docs/02`, `docs/03` (falta documentar `ProduccionTraduccion`,
  `generos_ids`, `Lista.clave` y `Usuario.idioma` en el modelo de datos),
  `docs/04` y `docs/06`; guía de uso; lista de la sección 8 del plan completa;
  segunda revisión manual de correos.

## 4. Cómo trabajar (recordatorio)

- Rama: `develop`. Sin merges a `main` hasta decidirlo explícitamente.
- Una OT por sesión, con tests, entrada en `docs/decisiones.md`, spec de
  `openspec/specs/` actualizada, fila de la tabla 10.4 y `graphify update .`.
- Levantar el entorno: `docker compose up -d --build --force-recreate`
  (el `node_modules` del frontend vive en un volumen anónimo).
- **El entrypoint del backend ejecuta `migrate` en cada arranque**, también
  con `docker compose run`: cualquier migración nueva se aplica sola a la base
  de desarrollo.
- Suite backend (necesita ver `contracts/` y `docs/`):

  ```bash
  docker compose run --rm --no-deps \
    -v "$PWD/contracts:/contracts:ro" -v "$PWD/docs:/docs:ro" \
    backend python manage.py test --noinput
  ```

- Regenerar referencias cuando un cambio es deliberado (revisar el diff):

  ```bash
  # OpenAPI y referencias de correo
  docker compose run --rm --no-deps -v "$PWD/contracts:/contracts" \
    -v "$PWD/docs:/docs:ro" -e FILMAI_ACTUALIZAR_REFERENCIAS=1 \
    backend python manage.py test filmai.tests_esquema filmai.tests_correos_contrato --noinput
  # Contrato de códigos de error
  docker compose run --rm --no-deps -v "$PWD/contracts:/contracts" \
    backend python manage.py exportar_contrato
  ```

- La suite valida el sobre de errores en toda respuesta 4xx/5xx de `/api/` y
  falla ante un código no registrado (`filmai/pruebas.py`). Un código nuevo se
  agrega primero a `filmai/errores/catalogo.py` y luego se exporta.
- Unitarios del frontend: correrlos en el host (`cd frontend && npx vitest run`,
  Node 22 de `~/.nvm`). Dentro del contenedor falla 1 de 73 porque `docs/` no
  está montado y el test lee `docs/i18n/ot70-catalogo-transitorio.csv`.
- Hay un test intermitente conocido (`401 != 200` en
  `usuarios.test_cuenta.PreferenciasTests`); si aparece, repetir la corrida.
- Los SHAs de las ramas borradas en el cierre del 08/10/2026 quedaron en el
  historial de git: `git show 05a53a2:docs/cierre-parcial-2026-10-08.md`.
