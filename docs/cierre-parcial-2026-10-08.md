# Cierre parcial — 08/10/2026: entorno, integración en `develop` y punto de continuación

Este documento deja el contexto necesario para retomar el desarrollo después del
cierre parcial. Cubre tres cosas: el estado del **entorno local**, el estado del
**código (una sola rama)** y **qué sigue**.

---

## 1. Entorno local (verificado hoy, funciona)

### Cómo levantarlo

```bash
docker compose up -d --build --force-recreate
```

El `--build --force-recreate` **no es opcional** tras este cierre:

- `--build`: la imagen del frontend se reconstruye para instalar la dependencia
  nueva `next-intl@4.14.9` (declarada en `frontend/package.json`).
- `--force-recreate`: el `node_modules` del frontend vive en un **volumen anónimo**
  (`/app/node_modules`) que se siembra desde la imagen solo al crear el contenedor.
  Sin recrearlo, el contenedor arrancaba con el `node_modules` viejo (sin
  `next-intl`) y `next dev` entraba en bucle de reinicios.

### Estado comprobado hoy

| Chequeo                               | Resultado                                                                                                                                                               |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 6 contenedores arriba                 | `db`, `redis`, `backend`, `celery-worker`, `celery-beat`, `frontend` (Up, healthy)                                                                                      |
| `next-intl` en el contenedor          | presente (`/app/node_modules/next-intl`)                                                                                                                                |
| Frontend                              | `next dev` compila sin reinicios: `✓ Ready` / `GET / 200`                                                                                                               |
| Migraciones de la BD de desarrollo    | `usuarios.0007_usuario_idioma` y `listas.0005_lista_clave` **aplicadas** `[X]`                                                                                          |
| Columnas nuevas                       | `Usuario.idioma` y `Lista.clave` existen y son utilizables                                                                                                              |
| **Login real en la BD de desarrollo** | `POST /api/auth/login/` → **200** con cookies `access`, `refresh`, `sessionid`; `GET /api/auth/user/` → 200; password inválida → 400 con el contrato de errores vigente |

Ese login era la duda que quedó abierta: las suites corrían sobre bases de
prueba actualizadas, pero la base de desarrollo no se había tocado. Ya está
migrada y el login completo (serializer + JWT + cookie) responde bien.

### Comandos útiles

```bash
docker compose exec backend python manage.py migrate        # migrar
docker compose exec frontend npm run test:unit              # unitarios frontend (73)
cd frontend && npx vitest run                               # igual, pero en el host
```

**La suite backend necesita ver `contracts/` y `docs/`** (resuelve
`settings.BASE_DIR.parent / "contracts"`, que dentro del contenedor es `/`, y
ahí no hay nada montado). Correrla así:

```bash
docker compose run --rm --no-deps \
  -v "$PWD/contracts:/contracts:ro" -v "$PWD/docs:/docs:ro" \
  backend python manage.py test --noinput
```

Con `docker compose exec backend python manage.py test` fallan 4 tests por
ruta (el de esquema OpenAPI y los de `listas/test_reservados.py`), no por
código. El CI no tiene ese problema: corre sobre un checkout completo.

Si hay que regenerar el contrato OpenAPI (`contracts/openapi.yaml`) —por
ejemplo cuando cambia la API—, se hace con el mecanismo del propio test:

```bash
docker compose run --rm --no-deps -v "$PWD/contracts:/contracts" \
  -v "$PWD/docs:/docs:ro" -e FILMAI_ACTUALIZAR_REFERENCIAS=1 \
  backend python manage.py test filmai.tests_esquema.EsquemaContratoTests --noinput
```

> **Ojo con `test_filmai_dev`**: si una corrida de tests se interrumpe (por un
> `restart` del contenedor, por ejemplo), queda la base de datos de prueba creada
> y la siguiente corrida se queja con `database "test_filmai_dev" already exists`.
> Se resuelve con `test --noinput` (la borra y recrea) o borrándola a mano.

---

## 2. Estado del código: una sola rama

### Ramas que quedan

| Rama      | Contenido                                                                                               |
| --------- | ------------------------------------------------------------------------------------------------------- |
| `develop` | **Toda** la línea de trabajo multiidioma + todo lo integrado en este cierre. Es la rama para continuar. |
| `main`    | Intacta en `7985200` (línea histórica previa, igual que `origin/main`).                                 |

**Se eliminaron todas las demás ramas** (locales y remotas): las ~50 `backup/*`,
`docs/*`, `chore/*` y `feat/*` del trabajo OT-00…OT-70, y sus réplicas en
`origin`. Motivo: o estaban integradas (eran ancestroras de `develop`), o eran
respaldos/borradores supersuperados. Ver §5 para recuperar cualquier SHa.

Limpieza ya ejecutada en este cierre:

- **Ramas locales**: de 49 a **2** (`develop` y `main`).
- **Ramas remotas**: de 36 a **2** (`develop` y `main`), con
  `git push origin --delete` una por una y `git fetch --prune` después.
- **Stash**: descartado (contenido verificado en `develop`).
- **Worktrees de `/tmp`**: los 16 eliminados (`git worktree remove`).
- **PRs abiertos**: se cerraron los 4 que quedaban (#42, #43, #66, #67) con un
  comentario que explica la consolidación en `develop` — sus ramas se
  eliminaban igual, y GitHub los habría cerrado en silencio.

### Qué integra `develop` (además de lo que ya traía)

Hoy se integraron las tres entregas que estaban **fuera** de la línea principal:

| Entrega | Rama integrada                                              | Qué aporta                                                                                                                       |
| ------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| OT-31   | `feat/i18n-ot31-frontera` (5 commits)                       | Frontera compartida de errores de serializers y códigos propios en `usuarios`/`filmai`                                           |
| OT-50   | `feat/i18n-ot50-layout-recuperacion` (4 commits)            | Servicio único de correos (`filmai.correos.servicio`) y layout compartido, sin cambiar copia                                     |
| OT-41A  | `feat/i18n-ot41-identidades` (1 commit)                     | Identidad de listas: consumidores y API por `clave`                                                                              |
| OT-41B  | **estaba sin commitear** en `/tmp/filmai-i18n-ot41b-retoma` | Nombres reservados ES/EN (`list_name_reserved`), `contracts/enums.json` + comando `exportar_enums`, tests y registro de decisión |

> **ATENCIÓN — OT-41B era trabajo sin commitear** en un worktree de `/tmp`. Se
> rescató y quedó commiteado en `develop` como
> `feat(listas): reserva nombres bilingües y exporta enums (OT-41B)`. Si algún día
> se necesita, ese trabajo ya **no** depende de ningún worktree.

Los únicos conflictos fueron de documentación (`docs/decisiones.md`,
`docs/plan-multiidioma.md`) y de `graphify-out/` (regenerable). El código se
mezcló limpio salvo un choque de imports en `backend/usuarios/serializers.py`
(OT-31 vs OT-50), resuelto conservando ambos lados.

### Orden de los merges (referencia)

```text
7995f39 feat(catalogo): resuelve el idioma en las vistas públicas   ← HEAD anterior
ec509d2 merge(i18n): integra OT-31
b14785c merge(i18n): integra OT-50
ed85794 merge(i18n): integra OT-41A
7eb7584 feat(listas): reserva nombres bilingües y exporta enums (OT-41B)
```

---

## 3. Verificación de este cierre

| Verificación                                         | Resultado                                                |
| ---------------------------------------------------- | -------------------------------------------------------- |
| Suite backend completa (`manage.py test`)            | **598 tests en verde** (186,5 s; ver §1 para los mounts) |
| Unitarios frontend (Vitest)                          | **73/73 en verde**                                       |
| `makemigrations --check` (sin migraciones sin crear) | **OK**                                                   |
| `ruff format . && ruff check .`                      | **OK** (además corre en el pre-commit)                   |
| `npx prettier --check .`                             | **OK** (además corre en el pre-commit)                   |
| Login real en BD de desarrollo                       | **OK** (ver §1)                                          |
| Frontend `GET /`                                     | **200**                                                  |

Dos apuntes de honestidad sobre la verificación:

- La corrida anterior a la final tuvo un `401 != 200` **intermitente** en una
  regresión vieja; es la misma incidencia ya documentada dos veces en
  `docs/decisiones.md` (OT-41A/OT-41B). La repetición salió en verde **sin
  tocar ningún test**.
- `contracts/openapi.yaml` se regeneró (4 líneas): el docstring de
  `FronteraErroresMixin` (OT-31) aporta una `description` a los esquemas
  `CambiarContrasena` y `Preferencias`. Queda anotado para OT-34/OT-72 decidir
  si conviene ocultarlo del contrato público.

Pendiente de correr acá (lo hace el CI en cada PR): Playwright e2e, `npx tsc
--noEmit` y `next build`.

---

## 4. Qué sigue (para retomar el desarrollo)

Prioridad del usuario, sin cambios: **terminar el backend (errores, listas,
correos y TMDB) antes de implementar las interfaces nuevas.** OT-70 dejó la
infraestructura de traducción del frontend lista pero **no** introdujo el
rediseño.

Según `docs/plan-multiidioma.md` (tabla de órdenes de trabajo), el siguiente
trabajo en orden es:

1. **OT-32** — códigos en `listas` y `catalogo`, casos irregulares normalizados
   (depende de OT-30 + el primer bloque de OT-31, ya integrados).
2. **OT-33** — espera en el 429, códigos en respuestas exitosas, estados de
   cuenta en login (completa las respuestas directas que faltan en OT-31).
3. **OT-34** — contrato exportado, sobre en OpenAPI y rechazo de códigos no
   registrados (cierra F3).
4. **OT-42** — restricciones y prueba sobre volcado de desarrollo (cierra F4
   después de OT-41).
5. **OT-51 → OT-53** — vigencias por contexto, HTML de "contraseña actualizada",
   plantillas en inglés y copia final (cierra F5 después de OT-50).
6. **OT-60 (fin) → OT-63** — publicación de la entrega de TMDB y fallback/
   materialización por idioma (F6).
7. **OT-71 → OT-77** — resto de infraestructura de frontend (formato, `ApiError`,
   selector de idioma, rutas en inglés, catálogos). **Aquí empieza lo visible.**
8. **OT-80 → OT-90** — paridad, lint de residuos, docs finales.

Recordatorios de estado:

- **OT-31 queda "Parcial"**: el alcance de F3 paso 2 entró y está verificado,
  pero las respuestas directas viven en OT-33.
- **OT-41 y OT-50 quedan "En validación"**: integradas y verificadas en local;
  falta publicar (CI de cabeza exacta) — no se abrieron PRs en este cierre.
- **OT-60 "En curso"**: cliente, caché, vistas y evidencia real verificados;
  publicación y suites finales pendientes.
- **OT-70 "Completada"**: es lo que habilita `next-intl`; todavía no cambió
  ninguna pantalla visible.

La convención del repo (sección 8 de `AGENTS.md`) sigue vigente: no hay review
humana ni bots; **el CI es la única puerta**, así que antes de mergeear hay que
correr suites, lint, registrar la decisión en `docs/decisiones.md` y actualizar
la spec/plan.

---

## 5. Recuperación: si falta alguna rama borrada

Las ramas se borraron, pero los commits siguen accesibles por SHa durante la
retención del reflog (≈90 días) y en `origin` hasta el GC. Alias usados hoy:

| Rama eliminada                       | Último SHa | Qué era                                                   |
| ------------------------------------ | ---------- | --------------------------------------------------------- |
| `feat/i18n-ot31-frontera`            | `a12bc52`  | **integrada** en `develop` (ec509d2)                      |
| `feat/i18n-ot50-layout-recuperacion` | `4a40b22`  | **integrada** en `develop` (b14785c)                      |
| `feat/i18n-ot41-identidades`         | `79f052c`  | **integrada** en `develop` (ed85794)                      |
| `feat/i18n-ot41-reservados`          | `79f052c`  | mismo commit que la anterior                              |
| `feat/i18n-cierre-entorno-contexto`  | `7995f39`  | **base** de `develop` (es su ancestro)                    |
| `origin/feat/i18n-multiidioma`       | `600aaee`  | merges #62–#65, todo ya en `develop`                      |
| `docs/i18n-ot13-copia-specs`         | `1562333`  | borrador de OT-13, supersuperado por la copia aprobada    |
| `origin/feat/c-04b-fase3-backfill`   | `5363284`  | refactor `ya_existentes`, ya aplicado en `main`/`develop` |
| `backup/*` (9 ramas)                 | varios     | respaldos pre-rebase, sin contenido único                 |
| stash `respaldo ot13 aprobado`       | —          | estado intermedio; todo su contenido está en `develop`    |

Para recuperar cualquiera:

```bash
git switch -c recuperar-<nombre> <sha>
```

Listado completo de las 47 ramas locales eliminadas (`nombre sha`), tomado justo
antes del borrado. Las 36 que no están marcadas eran **ancestroras de
`develop`** (todo su contenido ya está integrado); las 11 restantes son los
respaldos y borradores supersuperados:

```text
backup/i18n-ot30-antes-base-final-ot20 730d706
backup/i18n-ot30-antes-base-ot20a e979e77
backup/i18n-ot60-antes-base-ot70 a72a5d0
backup/i18n-ot70-a-pre-rebase 2ce3173
backup/i18n-ot70-b-pre-rebase 85b7c3e
backup/i18n-ot70-c-pre-rebase 28b7862
backup/ot40-526fe6d-pre-ot20a 526fe6d
backup/ot40-b904577-pre-ot30 b904577
backup/ot50-layout-confirmacion-411 90edcf7
chore/i18n-ot03-build-locale e09b516
docs/i18n-ot00-linea-base 9f6547d
docs/i18n-ot10-decisiones-glosario 9bd1dbd
docs/i18n-ot11-contrato-errores 54218c4
docs/i18n-ot12-claves-cuenta-listas baa60d0
docs/i18n-ot12-claves-descubrimiento f76dc3b
docs/i18n-ot12-claves-legal-correos 354cb43
docs/i18n-ot12-curaduria-claves 9bd1dbd
docs/i18n-ot13-copia-specs 1562333        (borrador, supersuperado)
docs/i18n-ot13-specs-aprobadas 1562333    (borrador, supersuperado)
feat/i18n-cierre-entorno-contexto 7995f39  (es el padre de develop)
feat/i18n-multiidioma 96fbcbc
feat/i18n-ot01-caracterizacion-api 94461ab
feat/i18n-ot02-correos-openapi d8e3c9f
feat/i18n-ot13-copia-aprobada 7c34285
feat/i18n-ot13-specs-aprobadas ff66b30
feat/i18n-ot20-nucleo 0c126cf
feat/i18n-ot20-preferencias-registro 93dce7c
feat/i18n-ot20-semilla c4cad5b
feat/i18n-ot30-catalogo ec2c0b7
feat/i18n-ot30-catalogo-base e56bf07
feat/i18n-ot30-manejador ec2c0b7
feat/i18n-ot30-metadatos 8a3ebbf
feat/i18n-ot30-sobre 57645b3
feat/i18n-ot31-frontera a12bc52            (integrada en develop)
feat/i18n-ot32-normalizacion 10fe49f
feat/i18n-ot40-clave 6dee3b5
feat/i18n-ot41-identidades 79f052c         (integrada en develop)
feat/i18n-ot41-reservados 79f052c          (mismo commit)
feat/i18n-ot50-layout-confirmacion b204afe
feat/i18n-ot50-layout-recuperacion 4a40b22 (integrada en develop)
feat/i18n-ot50-layout-reenvio 16eb718
feat/i18n-ot50-servicio aa7c36b
feat/i18n-ot60-cliente ba54d54
feat/i18n-ot60-vistas 7995f39
feat/i18n-ot70-catalogo-transitorio 4e7d7ba
feat/i18n-ot70-metadatos-pruebas 6614fb8
feat/i18n-ot70-nucleo b00a1e2
```

Además se descartó el stash `respaldo ot13 aprobado antes de dividir entrega`
(`a46a12a`): se comprobó archivo por archivo que todo su contenido está en
`develop` (0 líneas exclusivas del stash en los archivos de specs/decisión; las
únicas diferencias eran estados de plan **anteriores** y una nota histórica
reemplazada).

Los worktrees de `/tmp/filmai-i18n-*` (ot01…ot70) también se eliminaron. Se
verificó antes, archivo por archivo, que su contenido estaba commiteado en
`develop` o supersuperado por las versiones aprobadas — la única excepción fue
OT-41B, que se rescató (ver §2).

---

## 6. Resumen de una línea

**Entorno: arreglado y verificado (frontend con `next-intl`, migraciones de
`Usuario.idioma` y `Lista.clave` aplicadas, login real OK). Código: todo en
`develop`, el resto de ramas borrado. Siguiente paso: OT-32 (códigos en listas y
catálogo), siguiendo el orden de `docs/plan-multiidioma.md`.**
