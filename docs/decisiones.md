# Decisiones y Cambios — FilmAI

Registro de decisiones de diseño y cambios relevantes del proyecto.
Formato: fecha (DD/MM/AAAA), título y descripción (qué, por qué, archivos afectados).

---

## 22/08/2026 — Datepicker de fecha de nacimiento: máximo hoy −13 años

- **Descripción**: los inputs `type="date"` de fecha de nacimiento (registro
  tradicional y completado de Google) definen `max` como la fecha de hoy menos
  13 años. Esto brinda feedback visual inmediato al usuario, impidiendo
  seleccionar fechas que el backend rechazaría. La validación backend
  (`validate_fecha_nacimiento` en `serializers.py`) sigue siendo la enforcement
  definitiva.
- **Motivo**: mejorar la UX del datepicker sin duplicar lógica de negocio;
  el navegador grisará las fechas no elegibles.
- **Archivos**: `frontend/app/(public)/register/page.tsx`,
  `frontend/app/completar-google/page.tsx`.

## 22/08/2026 — JWT_AUTH_SECURE derivado del entorno; JWTCookieAuthentication

- **Descripción**: `JWT_AUTH_SECURE` ahora se lee de la variable de entorno
  (default `True`); en desarrollo local se puede setear `False` en `.env`.
  Además, se reemplazó `JWTAuthentication` de simplejwt por
  `JWTCookieAuthentication` de dj-rest-auth para soportar autenticación tanto
  por header Bearer como por la cookie httpOnly `access`.
- **Motivo**: seguridad en producción (cookies Secure) y compatibilidad con
  el flujo de cookies httpOnly que ya usa dj-rest-auth.
- **Archivos**: `backend/filmai/settings.py`.

## 22/08/2026 — Registro de Usuario en Django Admin

- **Descripción**: se registró `usuarios.Usuario` en `admin.py` con un
  `UsuarioAdmin` personalizado que adapta los fieldsets de `UserAdmin` a los
  campos del modelo (`correo`, `nombre_usuario`, `nombre`, `apellido`, etc.).
- **Motivo**: permitir la gestión de usuarios desde el panel de administración
  de Django (Módulo 6); el archivo estaba vacío y el modelo no aparecía.
- **Archivos**: `backend/usuarios/admin.py`.

## 22/08/2026 — transaction.atomic en señal de aprovisionamiento

- **Descripción**: el handler `crear_recursos_por_defecto` (señal `post_save`
  de `Usuario`) ahora envuelve la creación de listas y chat en
  `transaction.atomic()`, de modo que un fallo en cualquier escritura revierte
  todas las creaciones parciales.
- **Motivo**: garantizar consistencia: si la creación del Chat falla, las
  listas tampoco se persisten.
- **Archivos**: `backend/usuarios/signals.py`.

## 22/08/2026 — Validación de campos Google antes de complete_social_login

- **Descripción**: en `GoogleSocialLoginSerializer.validate`, la validación de
  `CAMPOS_FALTANTES_GOOGLE` ahora se ejecuta antes de `complete_social_login`
  para evitar que allauth persista un usuario incompleto cuando faltan
  `nombre_usuario`, `fecha_nacimiento` o `genero`.
- **Motivo**: prevenir usuarios huérfanos en la BD cuando la pantalla de
  completación aún no envió los campos faltantes.
- **Archivos**: `backend/usuarios/serializers.py`.

## 22/08/2026 — Refresh token fuera de localStorage

- **Descripción**: `storeTokens` del frontend ya no persiste el refresh token
  en localStorage; el refresh token viaja exclusivamente como cookie httpOnly
  seteada por el backend (`JWT_AUTH_HTTPONLY: True`). Se eliminó
  `getRefreshToken` y `REFRESH_KEY`.
- **Motivo**: reducir la superficie de ataque XSS; el refresh token solo debe
  ser accesible por el navegador (cookie httpOnly), no por JavaScript.
- **Archivos**: `frontend/lib/api.ts`.

## 22/08/2026 — Fecha de nacimiento con datepicker nativo

- **Descripción**: el campo "Fecha de nacimiento" (registro tradicional y
  completado de Google) usa el input HTML nativo `type="date"`, que valida
  automáticamente y envía el valor en ISO `YYYY-MM-DD` (el backend ya acepta
  `%Y-%m-%d` y `%d/%m/%Y`). El orden de visualización lo decide el locale del
  navegador (mm/dd/aaaa en en-US, dd/mm/aaaa en es-ES).
- **Motivo**: evitar la validación manual de texto libre y sus dolores de
  cabeza; el datepicker nativo ya la hace. Se acepta la variación visual por
  locale a cambio de validación automática.
- **Archivos**: `frontend/app/(public)/register/page.tsx`,
  `frontend/app/completar-google/page.tsx`,
  `docs/02_Especificación de Requerimientos.md`, `docs/04_Lineamientos_UI.md`.

## 22/08/2026 — Adopción de dj-rest-auth + django-allauth para autenticación

- **Descripción**: Se adoptó `dj-rest-auth` + `django-allauth` como stack de
  autenticación, cubriendo tanto el registro tradicional (email + contraseña)
  como el inicio de sesión con Google OAuth (proveedor `socialaccount` de
  allauth, expuesto vía `dj-rest-auth`). La confirmación de cuenta utiliza el
  token de confirmación de email propio de allauth (no un JWT de un solo uso).
- **Referencia**: [django-allauth](https://docs.allauth.org/en/dev/index.html).
- **Motivo**: No reinventar el intercambio de tokens OAuth ni la verificación
  de email; aprovechar librerías mantenidas y estándar para SPA + JWT.
- **Decisiones asociadas**:
  - **bcrypt** como hasher (`PASSWORD_HASHERS` con `BCryptSHA256PasswordHasher`
    + dependencia `bcrypt`); cumple RNF #2 / RNF #12.
  - **`is_active` (Opción A1)**: propiedad derivada de `estado` (getter
    `estado == ACTIVA`) con *setter* (`True → estado = ACTIVA`, `False` =
    no-op). Se elimina la columna huérfana `is_active` de la BD. `estado`
    (PENDIENTE/ACTIVA/BAJA) es la única fuente de verdad.
  - **Usuario Google nuevo**: `estado = ACTIVA` directo (Google ya verifica el
    email, sin confirmación por correo) + pantalla intermedia de UI para
    completar `nombre_usuario`, `fecha_nacimiento` y `genero` (campos que
    Google no provee). `google_id` se mantiene y se sincroniza desde
    `SocialAccount.uid`.
- **Archivos afectados**: `docs/05_Plan_de_Desarrollo.md` (A-01..A-08),
  `docs/04_Lineamientos_UI.md`, `docs/03_Modelos de Datos y de Diseño.md`,
  `docs/02_Especificación de Requerimientos.md` (CU-002); pendientes de
  implementación: `backend/usuarios/models.py`, `backend/filmai/settings.py`,
  `backend/requirements.txt`.

## 22/08/2026 — Carácter `!` permitido en la contraseña

- **Descripción**: Se amplió el conjunto de caracteres especiales válidos de la
  contraseña (CU-001) para incluir `!`: ahora es `@#$%&*!`. Se actualizó el
  validador (`usuarios/validators.py`) y la documentación (docs/02, docs/04 y
  el wireframe).
- **Motivo**: `!` es un carácter especial de uso común y el password de seed
  (`Password123!`) ya lo usaba; se unifica para coherencia entre validación,
  documentación y datos de desarrollo.
- **Archivos**: `backend/usuarios/validators.py`,
  `docs/02_Especificación de Requerimientos.md`,
  `docs/04_Lineamientos_UI.md`, `docs/wireframes/Opcion 1/app.html`.

## 18/08/2026 — Renombrado completo de la aplicación: FilmIA → FilmAI

- **Descripción**: Se realizó un análisis end-to-end del repositorio para
  reemplazar todas las ocurrencias del nombre incorrecto "FilmIA" por el
  nombre oficial "FilmAI". El cambio afectó tanto el nombre visible de la
  marca como los identificadores técnicos internos (`filmia` → `filmai`).
- **Motivo**: El nombre correcto y definitivo de la aplicación es "FilmAI"
  (con la sigla AI en mayúsculas, haciendo referencia a Artificial Intelligence).
  "FilmIA" era un error de escritura que se había propagado en todo el proyecto.
- **Archivos afectados**:
  - `README.md`, `AGENTS.md`, `.gitignore`, `.env.example`
  - `.husky/pre-commit`
  - `docker-compose.yml` (header, container names: `filmai_db`, `filmai_redis`,
    `filmai_backend`, `filmai_frontend`; red: `filmai_network`)
  - `backend/filmia/` → renombrado a `backend/filmai/` (módulo Django)
  - `backend/filmai/settings.py`, `asgi.py`, `wsgi.py`, `urls.py`
  - `backend/manage.py`, `backend/Dockerfile`, `backend/entrypoint.sh`
  - `backend/pyproject.toml`, `backend/requirements.txt`
  - `backend/usuarios/models.py`, `factories.py`,
    `management/commands/seed.py`
  - `frontend/Dockerfile`, `frontend/app/layout.tsx`,
    `frontend/app/globals.css`, `frontend/app/(public)/page.tsx`
  - `docs/decisiones.md`, `docs/01_Presentación...`, `docs/03_Modelos...`,
    `docs/04_Lineamientos_UI.md`, `docs/05_Plan_de_Desarrollo.md`,
    `docs/06_TMDB_API_Referencia.md`
  - `docs/wireframes/Opcion 1/app.html`
- **Nota**: Las variables de entorno de PostgreSQL (`POSTGRES_DB=filmai_dev`,
  `POSTGRES_USER=filmai_user`) y los emails ficticios de prueba
  (`@filmai.com`) también fueron actualizados para mantener coherencia.
  Si ya existe un volumen Docker con datos de desarrollo bajo el nombre
  anterior, es necesario recrearlo (`docker compose down -v`).

## 13/08/2026 — Unificación de Persona/Usuario/Administrador en un único `Usuario`

- **Descripción**: Se eliminaron las entidades `Persona` y `Administrador`.
  El modelo quedó con una única entidad `Usuario` que es el `AUTH_USER_MODEL`
  de Django, heredando de `AbstractBaseUser` + `PermissionsMixin`. Sus campos
  de identidad (`nombreUsuario`, `correo`, `contraseña`, `googleId`) se absorben
  en `Usuario`.
- **Motivo**: La gestión de administradores se realiza a través del Django Admin
  nativo (Módulo 6), que usa flags `is_staff`/`is_superuser` y no una entidad
  separada. La herencia multi-tabla era especulativa (una sola subclase) y
  chocaba con el `AUTH_USER_MODEL`.
- **Archivos**: `backend/usuarios/models.py`, `backend/filmai/settings.py`,
  `backend/entrypoint.sh`.

## 13/08/2026 — `estado` como fuente única de verdad del ciclo de vida

- **Descripción**: `is_active` dejó de ser un campo de BD; ahora es una propiedad
  derivada de `estado` (`is_active` es `True` solo si `estado == Activa`).
- **Motivo**: evitar una doble fuente de verdad; `estado` representa el ciclo
  completo pendiente → activa → baja (CU-001, CU-002, CU-007).
- **Archivos**: `backend/usuarios/models.py`.

## 13/08/2026 — `contraseña` VARCHAR(50) → VARCHAR(128)

- **Descripción**: el hash de bcrypt mide 60+ caracteres; el campo se amplió a
  128 caracteres (coherente con RNF #2).
- **Archivos**: `backend/usuarios/models.py` (campo `password` heredado de
  `AbstractBaseUser`), `docs/03_DiagramaClases_DiagramaTablas.json`,
  `docs/03_Modelos de Datos y de Diseño.md`.

## 13/08/2026 — `Mensaje.texto` VARCHAR(250) → TextField

- **Descripción**: una respuesta del LLM puede superar 250 caracteres; se usa
  `TextField` para no truncar el contenido.
- **Motivo**: el límite VARCHAR(250) del diagrama de tablas no era adecuado
  para respuestas conversacionales del chatbot.
- **Archivos**: `backend/chatbot/models.py`.

## 13/08/2026 — Unicidades añadidas (integridad a nivel BD)

- **Descripción**: se añadieron restricciones de unicidad compuestas exigidas
  por los casos de uso, aunque no estuvieran explícitas en el diagrama:
  - `(idTMDB, tipo)` en `ProduccionAudiovisual` — los IDs de TMDB no son únicos
    entre películas y series.
  - `(usuario, produccion)` en `Calificacion` — una calificación por usuario y producción.
  - `(usuario, nombre)` en `Lista` — nombre de lista único por usuario.
  - `(lista, produccion)` en `Tiene` — PK compuesta del diagrama (no duplicar ítem).
- **Motivo**: integridad referencial a nivel de base de datos (última línea de defensa).
- **Archivos**: `backend/catalogo/models.py`, `backend/listas/models.py`.

## 13/08/2026 — Nombres camelCase → snake_case

- **Descripción**: los nombres de atributos del diagrama (camelCase, ej.
  `nombreUsuario`, `fechaNacimiento`) se normalizaron a snake_case en el código
  (`nombre_usuario`, `fecha_nacimiento`) por convención de Django/Python.
- **Archivos**: todos los `models.py`.

## 13/08/2026 — `Reseña` → `Calificacion` modelada como OneToOne

- **Descripción**: la composición "una calificación tiene 0..1 reseña" se modeló
  con `OneToOneField` (no FK simple), según el diagrama de clases.
- **Archivos**: `backend/catalogo/models.py`.

## 18/08/2026 — Seeds de desarrollo con factory_boy (F-05)

- **Descripción**: se implementó el comando `python manage.py seed` que puebla
  la BD con datos consistentes para desarrollar la UI: 3 usuarios de prueba
  (contraseña común `Password123!`), 50 producciones (25 películas + 25 series),
  calificaciones y reseñas asociadas, listas predeterminadas (Favoritos,
  Pendientes, Vistas) + personalizadas, y un chat con mensajes por usuario.
  El comando es **destructivo e idempotente**: borra los datos de las apps de
  negocio y los recrea en cada ejecución.
- **Motivo**: facilitar el desarrollo de la UI (Módulos 2-5) sin depender de la
  API de TMDB ni de datos reales.
- **Archivos**: `backend/usuarios/factories.py`, `backend/catalogo/factories.py`,
  `backend/listas/factories.py`, `backend/chatbot/factories.py`,
  `backend/usuarios/management/commands/seed.py` (+ `management/__init__.py`).
- **Convención**: los factories viven en `factories.py` dentro de cada app; el
  comando `seed` vive en `usuarios/management/commands/` (no hay app `core`).
  El password se aplica vía `create_user` (override de `_create` en el factory)
  para que quede hasheado.

## 18/08/2026 — Reset de BD por InconsistentMigrationHistory

- **Descripción**: al intentar `migrate` con el `AUTH_USER_MODEL` custom ya
  declarado, Django lanzó `InconsistentMigrationHistory` porque `auth`/`admin`
  estaban aplicadas sobre el `User` por defecto (migradas antes del F-04) pero
  sus dependencias swappable (`usuarios.0001_initial`) no. Se resolvió con un
  reset del schema (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`) y
  re-migración limpia. La BD no tenía datos de negocio (solo el superuser
  auto-generado por `entrypoint.sh`, que se recrea al reiniciar el contenedor).
- **Motivo**: documentar el gotcha para futuros resets/migraciones del entorno
  de desarrollo.
- **Archivos**: ninguno (operación de base de datos).

## 18/08/2026 — Ruff como linter + formatter único (F-06)

- **Descripción**: se configuró Ruff como linter **y** formatter (`ruff check` +
  `ruff format`) en `backend/pyproject.toml`. `ruff format` reemplaza a `black`
  (compatible: line-length 88, doble comilla). Config: `target-version = py312`,
  `exclude = ["*/migrations/*"]`, `per-file-ignores` de `RUF012` en `models.py`
  (falso positivo de Django: `ordering`, `constraints` y `REQUIRED_FIELDS` son
  metadatos, no defaults mutables). Se omitió `E501`: la longitud la controla
  el formatter, no el linter.
- **Motivo**: el plan F-06 pedía "ruff o flake8 + black". Se usó el formatter de
  Ruff en lugar de instalar `black` por separado (ya venía con ruff, es drop-in
  compatible y evita una dependencia redundante).
- **Archivos**: `backend/pyproject.toml` + reformateo de los `models.py`,
  `settings.py`, `manage.py`, `admin.py`/`apps.py`/`tests.py`/`views.py`
  (quita imports sin usar) y los `factories.py`.

## 18/08/2026 — Arquitectura de retrieval del chatbot: tool calling + pgvector + BGE-M3

- **Descripción**: se definió la arquitectura de retrieval del chatbot (Módulo 5)
  para desarrollo posterior. Consta de tres decisiones:
  1. **Tool calling obligatorio** (no se embebe el contexto del usuario): el LLM
     recibe herramientas `buscar_por_titulo`, `top_por_genero`, `similares_a`
     (TMDB) y `buscar_semantico` (pgvector). El historial de gustos del usuario
     (calificaciones, reseñas, vistas) se obtiene por SQL y se inyecta
     anonimizado al prompt (B-05), sin pasar por ningún vector store.
  2. **Embeddings locales con BGE-M3 vía Ollama** (gratis, cross-lingual): el
     corpus (sinopsis de TMDB) está en inglés pero el usuario consulta en
     español, por lo que se necesita un modelo multilingüe. Se descarta
     `nomic-embed-text` por ser monolingüe (inglés).
  3. **pgvector sobre el PostgreSQL 16 existente**: imagen
     `pgvector/pgvector:pg16-alpine`, `CREATE EXTENSION vector`, vector(1024),
     índice HNSW.
- **Texto a embebear** (plantilla en inglés con labels):
  `Title + Genres + Directors + Cast + Keywords + Synopsis`. Los campos
  cuantitativos (`calificacion_promedio`, `fecha_lanzamiento`, `duracion`,
  `tipo`, `estatus`) **no** van al vector: se aplican como filtros SQL
  post-recuperación.
- **Cambios de modelo asociados**: nuevo campo `keywords` (ArrayField) en
  `ProduccionAudiovisual` sincronizado desde TMDB en C-04
  (`/movie/{id}/keywords`, `/tv/{id}/keywords`); nuevo modelo
  `ProduccionEmbedding` (FK + `VectorField(1024)` + índice HNSW).
- **Motivo**: personalización basada en historial sin pagar por embeddings ni
  exponer datos del usuario; consultas conceptuales sobre el catálogo que TMDB
  `discover` no expresa; grounding contra datos reales para evitar
  alucinaciones del LLM.
- **Archivos**: `docs/05_Plan_de_Desarrollo.md` (Módulo 5, C-01, C-04),
  `docs/06_TMDB_API_Referencia.md` (nuevo), futuros: `docker-compose.yml`
  (servicio `ollama`), `backend/requirements.txt` (`httpx`, `pgvector`,
  `django-pgvector`), `backend/catalogo/models.py`.

## 18/08/2026 — Documento de referencia de la API de TMDB

- **Descripción**: se creó `docs/06_TMDB_API_Referencia.md` con el listado
  completo de endpoints de TMDB API v3 (base URL, autenticación, secciones y
  notas de uso para el tool calling del chatbot). Sirve como referencia rápida
  para implementar `TMDBClient` (C-01) y las herramientas del LLM.
- **Motivo**: tener a mano y de forma consultable qué expone la API externa
  integrada (RNF #14) al momento de implementar catálogo y chatbot.
- **Archivos**: `docs/06_TMDB_API_Referencia.md`.

## 18/08/2026 — Prettier + ESLint + Husky en frontend (F-06)

- **Descripción**: Prettier (`.prettierrc` + `.prettierignore`) + integración de
  `eslint-config-prettier` en `eslint.config.mjs` (flat config). Scripts `format`
  y `format:check` en `package.json`. Husky con hook `pre-commit` que corre
  backend (ruff vía `docker compose exec`) y frontend (eslint + prettier con las
  dependencias del host).
- **Motivo**: por el layout monorepo (`package.json` en `frontend/`, `.git` en la
  raíz), husky 9 exige ejecutarse desde el directorio que contiene `.git`; por
  eso `prepare = "cd .. && husky"` y el hook vive en `.husky/` (raíz).
- **Archivos**: `frontend/.prettierrc`, `frontend/.prettierignore`,
  `frontend/eslint.config.mjs`, `frontend/package.json`,
  `frontend/package-lock.json`, `.husky/pre-commit`.

## 24/08/2026 — A-04/A-05: link de recuperación solo visual, error genérico de login y endpoint de disponibilidad de username

- **Descripción**: se cerraron los criterios pendientes de A-04 y A-05 (docs/05).
  1. **"¿Olvidaste tu contraseña?" solo visual (A-04)**: el link aparece en la
     pantalla de login alineado a la derecha, sin acción asociada. El mecanismo
     completo (modal con email + "Enviar enlace", CU-020) se implementa en
     A-07, tal como lo separa el plan. El wireframe ya lo dejaba como
     placeholder (`alert('Modal: recuperar contraseña')`).
  2. **Error genérico de login**: ante cualquier fallo de login por credenciales,
     el frontend muestra el mensaje genérico "Email, usuario o contraseña
     incorrectos." en lugar del mensaje crudo del backend (docs/04:634). No
     revela si el email o el username existen.
  3. **Endpoint custom de disponibilidad de username (A-05)**:
     `GET /api/auth/username-available/?username=X` → `{"disponible": bool}`.
     dj-rest-auth no provee este chequeo; se agregó `UsernameDisponibleView`
     que valida formato (CU-001: alfanumérico 5–25, misma regex de
     `validators.py`) y unicidad insensible a mayúsculas (`iexact`, igual que
     `validate_nombre_usuario`). Formato inválido también responde
     `{"disponible": false}` para simplificar el cliente.
  4. **Validaciones inline onBlur + disponibilidad debounced (A-05)**:
     nuevo `frontend/lib/validation.ts` con las reglas de CU-001; cada campo
     valida al perder foco con mensaje inline bajo el input; el username hace
     el chequeo de disponibilidad contra el endpoint con debounce de 400 ms
     ("Verificando…" / "Disponible" / "No disponible"). Los errores de campo
     del backend (DRF `{campo: [msgs]}`) se mapean a errores inline vía
     `extraerErroresPorCampo` en `lib/api.ts`.
  - **Nota sobre nombres/apellidos**: la restricción "solo letras" se interpreta
    permitiendo espacios internos simples (nombres compuestos); sin números ni
    símbolos.
- **Motivo**: cumplir los criterios de aceptación de A-04/A-05 sin adelantar
  A-07; unificar las reglas de validación del lado cliente con las del backend.
- **Archivos**: `frontend/app/(public)/login/page.tsx`,
  `frontend/app/(public)/register/page.tsx`, `frontend/lib/api.ts`,
  `frontend/lib/validation.ts` (nuevo), `backend/usuarios/views.py`,
  `backend/usuarios/tests.py`, `backend/filmai/urls.py`.

## 24/08/2026 — Menú de avatar con solo "Cerrar sesión", navbar oculto en auth y toasts con sonner

- **Descripción**:
  1. **Menú del avatar (alcance reducido de P-07/A-08)**: el navbar
     autenticado muestra un avatar circular con las iniciales del usuario
     (nombre + apellido) que despliega un menú con el único ítem "Cerrar
     sesión" (divider + color danger). El dropdown se cierra al clickear fuera
     o presionar Escape (criterio de aceptación de P-07). Antes de cerrar la
     sesión aparece el modal de confirmación "¿Está seguro que desea cerrar
     sesión?" (CU-004 / A-08); al confirmar se llama a `dj-rest-auth`
     (`POST /api/auth/logout/`), se limpian los tokens y se redirige a Home.
     *Desviación consciente del plan*: P-07 define 4 ítems (Mi perfil, Mis
     reseñas, Preferencias, Cerrar sesión), pero esas pantallas dependen de
     P-02+ que aún no existen. Los ítems restantes se agregan cuando se
     implementen.
  2. **Navbar oculto en /login y /register**: según los wireframes de auth
     (docs/04 §5f), login y registro son pantalla completa con la caja
     centrada y el wordmark "FilmAI" DENTRO de la caja — no llevan navbar.
     Se agregó el check junto al existente para la landing ("/") y se agregó
     el wordmark a ambas cajas. Esto elimina la duplicación de opciones
     (Iniciar sesión/Registrarse) entre navbar y formulario.
  3. **Toast de bienvenida post-login (CU-003)**: se adoptó `sonner` como
     librería de toasts (estándar de shadcn; los docs ya prevén toasts en
     flujos futuros: cuenta confirmada, recuperar contraseña, guardar perfil).
     `<Toaster position="top-center">` montado en el layout raíz. Login por
     formulario y Google muestran "¡Hola de nuevo, @{usuario}!" antes de
     redirigir al Home. Destino actual: "/" (landing); cuando exista el
     catálogo (A-06) se apunta allí — docs/04:635 dice "Redirect al Home".
- **Motivo**: pedido del usuario; cumplir CU-003/CU-004 sin adelantar pantallas
  inexistentes y resolver la duplicación visual en las rutas de autenticación.
- **Archivos**: `frontend/components/Navbar.tsx`, `frontend/app/layout.tsx`,
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/(public)/register/page.tsx`, `frontend/lib/google-auth.ts`,
  `frontend/package.json`.

## 24/08/2026 — Envío de emails transaccionales vía Resend (backend de email custom)

- **Descripción**: se reemplaza el console backend por un `EMAIL_BACKEND`
  custom sobre la API HTTP de Resend para los emails de allauth/dj-rest-auth
  (confirmación de cuenta CU-002; a futuro A-07 password reset).
  1. **`filmai.email_backends.ResendBackend`**: traduce `EmailMessage` a
     `resend.Emails.send` (SDK oficial, `resend>=2.0`). Soporta texto y
     alternativa HTML (`EmailMultiAlternatives`). Sin `RESEND_API_KEY` no
     envía y loguea error en vez de romper el request.
  2. **Redirección de destinatario para testing sin dominio propio**: Resend
     solo permite enviar desde `onboarding@resend.dev` y únicamente al email
     dueño de la cuenta (403 con cualquier otro destinatario). Si
     `RESEND_TEST_RECIPIENT` está definido, TODO email saliente se redirige a
     esa dirección: la confirmación de cualquier registro llega a esa bandeja
     y el link sigue siendo válido para la cuenta registrada. Con dominio
     propio verificado: borrar la variable y cambiar `DEFAULT_FROM_EMAIL`.
  3. **Variables** (`.env` + `.env.example`): `EMAIL_BACKEND`,
     `RESEND_API_KEY`, `RESEND_TEST_RECIPIENT`, `DEFAULT_FROM_EMAIL`. Sin
     configurar Resend, se usa console backend como antes.
  4. **Comando de prueba**: `python manage.py send_test_email [destino]`.
  5. **Logging**: `LOGGING` mínimo en settings para ver cada envío
     (id de Resend) en `docker compose logs -f backend`.
  6. Tests unitarios con mock del SDK en `filmai/tests.py` (envío básico,
     redirección de destinatarios, HTML alternativo, falta de API key,
     propagación de errores).
- **Motivo**: poder probar CU-002 end-to-end con emails reales sin dominio
  propio ni SMTP local; dejar lista la infraestructura para A-07.
- **Limitación conocida**: mientras no haya dominio verificado, solo recibe
  emails reales el dueño de la API key.
- **Archivos**: `backend/filmai/email_backends.py` (nuevo),
  `backend/filmai/tests.py` (nuevo), `backend/filmai/settings.py`,
  `backend/requirements.txt`, `backend/usuarios/management/commands/send_test_email.py`
  (nuevo), `.env.example`, `.env` (local, no versionado), `Dockerfile`
  (rebuild para incluir el SDK).

## 24/08/2026 — Confirmación de correo: validez 24h, templates propios en español y errores diferenciados (CU-002)

- **Descripción**:
  1. **Validez del enlace**: `ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1`
     (24 horas). Se descartó un token custom por horas: allauth solo soporta
     expiración en días enteros y 1 día resultó suficiente; se mantiene el
     mecanismo nativo de keys firmadas (HMAC + timestamp, sin tabla en DB).
  2. **Templates propios del email** (antes usaba los built-in de allauth, en
     inglés): `backend/templates/account/email/` con
     `email_confirmation_{signup_,}{subject,message.txt,message.html}`.
     Asunto "[FilmAI] Confirmación de cuenta" (se escribió completo en el
     template porque `ACCOUNT_EMAIL_SUBJECT_PREFIX` pasó a vacío para no
     duplicar la marca). Cuerpo en registro formal ("su cuenta", "ignore").
     El HTML es una card oscura con la paleta de la app (#161625 sobre
     #0d0d14, botón #e67e22), tablas y estilos inline para clientes de correo,
     botón + link plano de fallback. Ambas variantes (signup y genérica)
     quedan cubiertas para que los reenvíos también lleguen en español.
     La validez de 24 horas se informa en el propio email, en la pantalla
     "Revisá tu bandeja de entrada" del registro y en el mensaje de enlace
     expirado del frontend.
  3. **Errores diferenciados**: `ConfirmarCorreoView` reemplaza a
     `VerifyEmailView` de dj-rest-auth en la ruta existente
     `/api/auth/registration/verify-email/`. Decodifica la key firmada y
     responde `200 {"detail":"ok"}` o
     `400 {"codigo": "expirado"|"invalido"|"ya_confirmada"}`. El éxito delega
     en `mark_email_address_as_verified()` de allauth (mantiene la lógica del
     adapter). El frontend mapea cada código a su pantalla: ya_confirmada se
     muestra como estado positivo, expirado explica las 24h y cómo reenviar.
  4. **Bug corregido de paso**: `UsuarioAccountAdapter.confirm_email()`
     llamaba a `super()` sin hacer `return`, devolviendo siempre `None`.
     allauth usa ese retorno para considerar confirmada la dirección, así que
     cualquier flujo que dependiera del resultado fallaba silenciosamente.
  5. **Tests**: `ConfirmarCorreoTests` cubre flujo completo
     (registro → email → confirmar → ACTIVA → login), reuso de key,
     key corrupta y expiración (+25h mockeando `django.core.signing.time`).
- **Motivo**: pedido del usuario tras encontrar el mensaje genérico "No se pudo
  confirmar" (la cuenta ya estaba confirmada por una prueba previa) y necesidad
  de branding/copy propios.
- **Archivos**: `backend/filmai/settings.py`, `backend/templates/account/email/*`
  (nuevos), `backend/usuarios/views.py`, `backend/usuarios/adapter.py`,
  `backend/usuarios/tests.py`, `backend/filmai/urls.py`,
  `frontend/app/confirmar-correo/[key]/page.tsx`,
  `frontend/app/(public)/register/page.tsx`, `.env.example` (sin cambios).

## 24/08/2026 — A-07: Recuperación de contraseña (CU-020) conectada de punta a punta

- **Descripción**:
  1. **Solicitud**: `RecuperarContrasenaView` reemplaza a la de dj-rest-auth
     en `/api/auth/password/reset/` (rutas propias ANTES del `include()`).
     Envía el email solo si existe cuenta ACTIVA con ese correo; la respuesta
     HTTP es idéntica siempre (no revela si el correo está registrado,
     docs/02 CU-020 obs.). Cuentas pendientes o de baja no reciben email.
  2. **Email**: templates propios en
     `backend/templates/registration/recuperar_contrasena_{subject,message.txt,message.html}`
     — asunto "[FilmAI] Restablecimiento de contraseña", registro formal, card
     oscura con la paleta de la app, botón + link fallback. El enlace apunta a
     `{FRONTEND_URL}/restablecer-contrasena/{uid}/{token}/`.
  3. **Validez**: `PASSWORD_RESET_TIMEOUT = 3600` (1 hora, CU-020). Tokens del
     generador nativo (`allauth` `default_token_generator`, HMAC con timestamp;
     sin estado en DB). Un token usado queda invalidado porque `_make_hash_value`
     incluye el hash de la contraseña.
  4. **Confirmación**: `RestablecerContrasenaView` en
     `/api/auth/password/reset/confirm/`. Campos `password1`/`password2`
     (consistente con registro). Enlace inválido/vencido/usado →
     `400 {"codigo": "invalido"}` (mismo contrato que ConfirmarCorreoView);
     contraseña que no cumple CU-001 → errores de campo DRF (la política se
     aplica vía `validate_password` + `ComplejidadContrasenaValidator` que ya
     estaba en AUTH_PASSWORD_VALIDATORS).
  5. **Rate limit**: DRF `ScopedRateThrottle` con dos scopes:
     solicitud de email "recuperar_contrasena" 1/min (estricto, CU-020) y
     confirmación "restablecer_contrasena" 5/min (tolera reintentos por
     validación inline). Caché LocMem por proceso (suficiente para dev;
     producción usará Redis).
  6. **Frontend**: modal en login (campo email + validar formato + botones
     Enviar enlace/Cancelar, cierre por backdrop). Toast de éxito SIEMPRE
     ("Te enviamos un email..."); 429 → error inline pidiendo esperar un
     minuto. Página nueva `app/restablecer-contrasena/[uid]/[token]/` con dos
     campos + toggle visibilidad, validaciones inline onBlur reutilizando
     `validarPassword`/`validarConfirmacion`, pantallas de éxito y de enlace
     inválido (informa validez de 1 hora).
  7. **Tests**: `RecuperarContrasenaTests` (8 casos): envío con enlace válido,
   no-revelación, exclusión de no activas, cambio efectivo + login, enlace
   inválido, expiración (+2h mockeando `_now` del generador), contraseña débil
   y rate limit 429.
- **Motivo**: completar la última actividad del Módulo 1 Autenticación (A-07),
  conectando el link visual que quedó en A-04.
- **Archivos**: `backend/filmai/settings.py`, `backend/filmai/urls.py`,
  `backend/usuarios/serializers.py`, `backend/usuarios/views.py`,
  `backend/templates/registration/*` (nuevos), `backend/usuarios/tests.py`,
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx` (nueva).

## 24/08/2026 — Saludo de los emails: nombre + apellido con fallback "Hola usuario"

- **Descripción**: nuevo filtro de template `nombre_completo`
  (`usuarios/templatetags/nombres.py`) usado por TODOS los emails
  transaccionales (confirmación, reenvío y restablecimiento): el saludo muestra
  "Nombre Apellido"; si ambos están vacíos (seed, Google sin perfil) cae a
  "Hola usuario". Además se corrigió un bug real: el contexto del email de
  restablecimiento pasaba la clave `usuario` pero el template leía `{{ user }}`,
  por lo que el nombre salía SIEMPRE vacío ("Hola ,"). Ahora el serializer pasa
  `"user"` (misma convención que allauth).
- **Motivo**: reporte del usuario — el email decía "Hola ," al probar con una
  cuenta cuyo campo nombre estaba vacío.
- **Archivos**: `backend/usuarios/templatetags/{__init__,nombres}.py` (nuevos),
  los 6 templates de `backend/templates/{account/email,registration}/`,
  `backend/usuarios/serializers.py`, `backend/usuarios/tests.py`
  (asserts de saludo + test de fallback).
