# Decisiones y Cambios — FilmAI

Registro de decisiones de diseño y cambios relevantes del proyecto.
Formato: fecha (DD/MM/AAAA), título y descripción (qué, por qué, archivos afectados).

---
## 12/09/2026 — C-03: endpoints de catálogo públicos con AllowAny explícito

- **Descripción**: los 7 endpoints de catálogo (`/api/catalogo/trending/`,
  `now-playing/`, `discover/`, `search/`, `movie/<id>/`, `tv/<id>/`,
  `keywords/`) se sirven con `authentication_classes = []` y
  `permission_classes = [AllowAny]` en `CatalogoBaseView`, sobrescribiendo
  explícitamente el `DEFAULT_PERMISSION_CLASSES = IsAuthenticated` introducido
  en PR #9. El catálogo (trending, búsqueda, detalle) es accesible sin login,
  consistente con docs 04 y 05 (Home y Buscador muestran contenido a usuarios
  no autenticados). El throttle `catalogo: 60/min` aplica a todos igualmente.
- **Motivo**: arquitectura del Módulo 2 (docs/05) describe discovery público;
  el usuario confirmó explícitamente que el catálogo es público.
- **Archivos**: `backend/catalogo/views.py`, `backend/catalogo/urls.py`,
  `backend/filmai/urls.py`, `backend/catalogo/tests.py`,
  `openspec/changes/catalog-tmdb-endpoints/`.

---

## 12/09/2026 — Skills centralizadas para todos los harnesses

- **Descripción**: `.agents/skills/` es la única fuente versionada de skills
  para Codex, OpenCode y Antigravity CLI. Se migró `conventional-commits` desde
  `.opencode/skills/` y se eliminaron de allí las copias de `humanizer` y
  `vercel-quality`. `AGENTS.md` instruye a los tres harnesses a consultar la
  fuente central antes de implementar.
- **Motivo**: evitar definiciones divergentes de una misma skill y conservar
  una revisión única y auditable de las instrucciones del proyecto.
- **Archivos afectados**: `AGENTS.md`, `.agents/skills/`,
  `.opencode/skills/` y `docs/decisiones.md`.

---

## 12/09/2026 — Contrato API centralizado y perfiles sociales inmutables al login

- **Descripción**: se incorpora OpenAPI con Swagger UI en `/api/docs/` y su
  esquema en `/api/schema/`; la documentación de parámetros deja de vivir en
  docstrings extensos de rutas. Las URLs de API usan slash final de forma
  explícita (`APPEND_SLASH=True`) y el helper del frontend lo normaliza antes
  de cada request. El handler global conserva los mapeos de TMDB y agrega
  respuestas consistentes para 404, 405 y 429. En Google OAuth, una cuenta ya
  vinculada devuelve el perfil FilmAI existente sin modificar estado ni datos
  personales; Google solo precarga una cuenta nueva.
- **Motivo**: consolidar el contrato público de la API, evitar discrepancias de
  rutas entre frontend y backend y proteger las modificaciones de perfil hechas
  dentro de FilmAI.
- **Archivos afectados**: `backend/requirements.txt`, `backend/filmai/settings.py`,
  `backend/filmai/urls.py`, `backend/filmai/exceptions.py`,
  `backend/filmai/views.py`, `backend/usuarios/adapter.py`,
  `backend/usuarios/avatares.py`, `backend/usuarios/factories.py`,
  `frontend/lib/api.ts` y sus pruebas asociadas.

---

## 11/09/2026 — El perfil de FilmAI prevalece sobre el perfil de Google

- **Descripción**: Google provee nombre y apellido solo para precargar el alta
  de una cuenta nueva. Una vez creada, el perfil de FilmAI es la fuente de
  verdad: un inicio de sesión posterior con una cuenta Google ya vinculada no
  actualiza `nombre` ni `apellido`. Se agregó una prueba de regresión que crea
  una cuenta social vinculada y verifica que conserva ambos valores locales.
- **Motivo**: permitir que la persona edite su identidad visible en FilmAI sin
  que cambios posteriores en su perfil de Google reviertan esa elección.
- **Archivos afectados**:
  - `backend/usuarios/adapter.py` — el mapeo de nombre y apellido permanece
    limitado a `populate_user`, usada para altas sociales nuevas.
  - `backend/usuarios/tests.py` — prueba de preservación del perfil local.

---

## 10/09/2026 — Tests en CI, AGENTS.md con reglas de testing y skills, limpieza de archivos raíz

- **Descripción**: se integraron los tests de Django al pipeline de CI (`ci.yml`) con un servicio PostgreSQL 16 en GitHub Actions. Se hizo configurable el host de base de datos en `settings.py` (`DATABASE_HOST`, default `"db"`) para permitir que CI use `localhost`. Se actualizó `AGENTS.md` agregando reglas de tests unitarios (§5) y consulta de skills (§6). Se limpió `.env.example` eliminando boilerplate. Se actualizó `.gitignore` agregando `.codegraph/` y `.ruff_cache/`. Se reescribió la Problemática del `README.md` y se agregó un diagrama ER Mermaid del modelo de datos. Testing del frontend queda pendiente para implementar cuando se analice el stack del frontend (Next.js no tiene framework de tests configurado aún).
- **Motivo**: análisis de Etapa 1 del proyecto detectó que el CI solo verificaba lint/formato pero no ejecutaba los tests existentes. Las NOTAs del usuario solicitaron los cambios en los demás archivos.
- **Archivos afectados**:
  - `.github/workflows/ci.yml` — agregado job de tests con PostgreSQL service.
  - `backend/filmai/settings.py` — `DATABASE_HOST` configurable.
  - `AGENTS.md` — nuevas reglas §5 y §6, renumeración.
  - `.gitignore` — agregadas entradas para `.codegraph/` y `.ruff_cache/`.
  - `.env.example` — eliminado boilerplate de títulos con `===`.
  - `README.md` — reescrita Problemática, agregado diagrama ER, ñ en todo el documento.

---

## 10/09/2026 — Grafo de conocimiento con graphify y directiva de actualización periódica

- **Descripción**: se incorporó un grafo de conocimiento del repositorio generado
  con **graphify** (`/graphify`, outputs en `graphify-out/`: `graph.html`,
  `graph.json`, `GRAPH_REPORT.md`). Se agregó la directiva en `AGENTS.md` (§5)
  de ejecutar `graphify update .` periódicamente para mantener el grafo al día.
  Momento conveniente elegido: al finalizar una tarea que haya creado o modificado
  archivos relevantes, ANTES de dar el OK al usuario o de crear el commit, para que
  el grafo actualizado quede versionado en el mismo commit. `graphify-out/` se
  versiona en git excepto `cache/`, `.graphify_python`, `.graphify_root`, la firma
  de labels y los backups automáticos (en `.gitignore`).
- **Motivo**: el usuario pidió mantener actualizado el grafo tras cada commit,
  y que la actualización ocurra ANTES del commit para que el grafo actualizado se
  suba con el cambio.
- **Archivos**: `AGENTS.md`, `.gitignore`, `graphify-out/` (nuevo).

---

## 08/09/2026 — Auditoría de consistencia y normalización documental end-to-end

- **Descripción**: se auditó el estado real del repositorio contra los docs 01–06,
  `README.md`, el diagrama de datos y OpenSpec. Resultado: en `main` están
  implementados autenticación (A-01..A-09), modelos base, seed, CI, C-01
  (cliente TMDB) y C-02 (caché Redis); siguen pendientes C-03 (endpoints de
  catálogo), C-04a (materialización), infraestructura pgvector/Ollama,
  `ProduccionEmbedding`, C-04b (sync Celery), APIs/UI de listas, reseñas,
  perfil y chatbot. Se corrigieron las contradicciones detectadas:
  1. README describía la jerarquía Persona/Usuario/Administrador ya eliminada.
  2. Docs 02/03 hablaban de "cron job" mientras el plan y la infraestructura
     prevista usan Celery Beat + workers.
  3. Docs 05 mencionaba `embedding IS NULL` en `ProduccionAudiovisual` mientras
     docs 03 definía la tabla `ProduccionEmbedding`: gana la tabla separada.
  4. El diagrama de tablas no incluía `keywords` ni `ProduccionEmbedding`.
  5. Docs 03 describía el chat persistido "al primer mensaje", pero la
     implementación (B-01) crea el chat por defecto al registrar el usuario.
  6. Docs 04 marcaba Sprint 1 (Home, Buscar) como completado sin código.
  7. Docs/decisiones documentaba CI como pendiente pese a que
     `.github/workflows/ci.yml` ya existe.
  Se actualizó el plan de desarrollo con el estado real por tarea, los
  próximos trabajos (catálogo, materialización, embeddings, sync, listas,
  chatbot/RAG) y el reparto vigente. No se crearon archivos nuevos: todo el
  trabajo futuro queda especificado dentro de la documentación existente.
- **Motivo**: el usuario aprobó ejecutar solo la normalización documental (pasos
  1 y 2 del plan); la implementación de código queda para fases posteriores.
- **Archivos**: `README.md`, `docs/02_Especificación de Requerimientos.md`,
  `docs/03_Modelos de Datos y de Diseño.md`,
  `docs/03_DiagramaClases_DiagramaTablas.json`, `docs/03_DiagramaCU.md`,
  `docs/04_Lineamientos_UI.md`, `docs/05_Plan_de_Desarrollo.md`,
  `docs/06_TMDB_API_Referencia.md`, `docs/decisiones.md`.

## 08/09/2026 — Embeddings asíncronos con Celery e idempotencia (reemplaza embeddings síncronos)

- **Descripción**: la generación de embeddings será asíncrona mediante Celery.
  La materialización persiste la producción y crea/encola un trabajo de
  embedding con estado `pending`, sin esperar al proveedor (Ollama BGE-M3).
  Estados: `pending`, `processing`, `ready`, `failed`. La búsqueda semántica
  solo considera embeddings `ready`; las producciones pendientes o fallidas
  siguen visibles en catálogo y son recuperables vía TMDB en vivo.
  **Reemplaza** la decisión del 25/08/2026 ("Embeddings síncronos en la
  materialización"), que quedaba sin efecto.
- **Motivo**: no bloquear catálogo ni detalle por una operación externa lenta;
  permitir reintentos con backoff, backfill y crecimiento progresivo del corpus
  sin degradar la experiencia (RNF #6/#7).
- **Idempotencia**: `ProduccionEmbedding` es 1:1 con `ProduccionAudiovisual`
  (`produccion_id` UNIQUE, no una FK común); no se aplica unicidad al vector
  (producciones distintas pueden tener vectores iguales). Antes de invocar al
  proveedor se compara el hash del texto canónico (`source_hash`) y la
  `model_version`: si no cambiaron y el estado es `ready`, no se recomputa.
  Celery puede duplicar tareas: la tarea usa claim/lease con actualización
  condicional y no mantiene transacciones abiertas durante la llamada externa.
  Garantía fuerte: nunca habrá dos embeddings persistidos por producción ni
  recomputación innecesaria; garantía imposible: un worker caído después de
  generar y antes de persistir puede haber invocado a Ollama dos veces.
- **Texto canónico a embeber**: `Title + Genres + Directors + Cast + Keywords
  + Synopsis` normalizado (espacios, vacíos y orden de arrays).
- **Archivos** (futuros): `backend/catalogo/models.py` (`ProduccionEmbedding`),
  `backend/catalogo/tasks.py`, `backend/catalogo/services/`,
  `docker-compose.yml` (worker + beat), `backend/requirements.txt`
  (`pgvector`, `django-pgvector`), `docs/05_Plan_de_Desarrollo.md`.

## 08/09/2026 — Corpus semántico global y progresivo + contrato TMDB → dominio

- **Descripción**: `ProduccionAudiovisual` se define como un catálogo global
  materializado progresivamente: la materialización no depende de que una
  producción pertenezca a una lista o tenga calificación. El corpus de
  búsqueda semántica es compartido por todos los usuarios; los datos personales
  (calificaciones, listas, historial) se usan vía SQL para personalizar y
  reordenar, nunca para acotar qué es buscable. Poblamiento:
  1. **Seed inicial global**: populares, tendencias, novedades y muestra
     diversa por género/año/tipo, para evitar cold start.
  2. **Materialización de lo expuesto**: cada producción servida por el
     catálogo/detalle se materializa y se enriquece (detalle + keywords)
     antes de encolar su embedding.
  3. **Cola larga**: producciones no materializadas se resuelven on-demand vía
     TMDB y se incorporan progresivamente al corpus.
  No se sincroniza todo TMDB de entrada. Además se fija el contrato canónico
  de tipos: TMDB usa `movie`/`tv` y el dominio local `pelicula`/`serie`; la
  conversión se hace en un único adaptador, nunca guardando valores TMDB
  crudos en `TipoProduccion`. La sincronización periódica (Celery Beat 3 AM)
  pasa a ser mantenimiento/seed, no prerrequisito del catálogo en vivo.
- **Motivo**: un corpus limitado a interacciones personales haría inútil la
  búsqueda semántica para descubrimiento; sincronizar todo TMDB no escala
  (decisión 25/08/2026 de arquitectura híbrida).
- **Archivos**: `docs/02_Especificación de Requerimientos.md` (CU-008, CU-013,
  CU-021), `docs/03_Modelos de Datos y de Diseño.md`,
  `docs/05_Plan_de_Desarrollo.md`, `docs/06_TMDB_API_Referencia.md`,
  `docs/decisiones.md`.

## 04/09/2026 — Corrección de arranque DRF y chequeo end-to-end

- **Descripción**: durante el chequeo end-to-end se corrigió la ruta de importación
  de `DEFAULT_PERMISSION_CLASSES` en `backend/filmai/settings.py`: DRF requiere
  `rest_framework.permissions.IsAuthenticated`, no `rest_framework.IsAuthenticated`.
  La imagen del backend también se reconstruyó para instalar las dependencias ya
  declaradas, incluida `fakeredis`. Se documentaron las cuentas y comandos de
  desarrollo en `README.md`.
- **Motivo**: el backend estaba en `Restarting (1)` y no podía ejecutar migraciones
  ni atender requests por el `ImportError` de DRF. El chequeo confirmó luego los
  servicios, la BD, el login, el envío de email y los 56 tests backend.
- **Archivos**: `backend/filmai/settings.py`, `README.md`, `docs/decisiones.md`.

## 26/08/2026 — Fix decodificación de parámetros en rutas dinámicas (useParams en Next.js)

- **Descripción**: se solucionó el fallo en la verificación de correo (`/confirmar-correo/[key]`) y restablecimiento de contraseña (`/restablecer-contrasena/[uid]/[token]`):
  1. `useParams()` de Next.js (App Router) retorna los segmentos de ruta URL-encoded.
  2. Las keys generadas por allauth (`signing.dumps`) contienen dos puntos (`:`) para separar payload, timestamp y firma HMAC (ej. `MjU:1wzFi6:sZEa...`).
  3. Al llegar a la página vía URL, `useParams()` devolvía la clave con `%3A` en vez de `:` (ej. `MjU%3A1wzFi6%3A...`). Al enviarla en el payload JSON a `/api/auth/registration/verify-email/`, `django.core.signing.loads` fallaba con `BadSignature: No ":" found in value`, respondiendo `400 {"codigo": "invalido"}`.
  4. Se aplicó `decodeURIComponent()` sobre los parámetros extraídos de `useParams` en `confirmar-correo/[key]/page.tsx` y `restablecer-contrasena/[uid]/[token]/page.tsx`.
- **Motivo**: corregir el error donde los enlaces de correo informaban "No se pudo confirmar" / "El enlace es inválido".
- **Archivos**: `frontend/app/confirmar-correo/[key]/page.tsx`, `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx`, `docs/decisiones.md`.

## 26/08/2026 — Cierre de gaps Fundación/Auth: keywords, navbar, A-09, bcrypt, Shadcn

- **Descripción**: se cerraron gaps detectados al comparar el código con docs 01–05:
  1. **`keywords` en `ProduccionAudiovisual`**: se agrega `ArrayField` (VARCHAR[])
     para keywords temáticos de TMDB (`/movie/{id}/keywords`, `/tv/{id}/keywords`).
     Queda vacío hasta C-04; se adelanta para no migrar después. Alimenta el texto
     a embeber de B-06 (`Title + Genres + Directors + Cast + Keywords + Synopsis`).
  2. **A-09 (middleware JWT) — opción B**: el middleware de Next.js solo comprueba
     presencia de la cookie `access` para redirigir a `/login`. La verificación
     real (firma, expiración, blacklist) queda en el backend
     (`JWTCookieAuthentication` + `IsAuthenticated`). Evita compartir
     `SECRET_KEY` con el frontend y duplicar lógica de auth.
  3. **bcrypt confirmado**: `PASSWORD_HASHERS` ya usa
     `BCryptSHA256PasswordHasher` y `bcrypt>=4.0` está en `requirements.txt`
     (RNF #2 cumplido). Sin cambio de código.
  4. **Shadcn sobre `@base-ui/react`**: desviación de F-03 (el plan decía
     shadcn/ui sobre Radix). El `components.json` usa `style: "base-nova"` y
     `@base-ui/react`. Se documenta para no romper expectativas en PRs futuros.
     Hoy solo está construido `components/ui/button.tsx`.
  5. **Navbar completa (doc 04 §4)**: links Inicio / Buscar / Listas + dropdown
     Mi perfil / Mis reseñas / Preferencias / Cerrar sesión. Las opciones aún
     no implementadas muestran toast `"Todavía no está implementado"`. Logo
     apunta a `/inicio`. Landing: CTA "Explorar catálogo" navega a `/inicio`
     (ya no `/catalogo`).
  6. **AGENTS.md §4**: los agentes deben correr `ruff format/check` y
     `prettier --check` antes de dar el OK.
- **Motivo**: auditoría end-to-end vs docs 01–05; el usuario confirmó opción B
  para A-09 y pidió adelantar `keywords`, completar la navbar visualmente y
  dejar el formateo como gate de entrega.
- **Archivos**: `backend/catalogo/models.py`,
  `backend/catalogo/migrations/0003_produccionaudiovisual_keywords.py`,
  `frontend/components/Navbar.tsx`, `frontend/app/(public)/page.tsx`,
  `docs/05_Plan_de_Desarrollo.md` (A-09), `AGENTS.md`.

## 26/08/2026 — Fix login Google vs registro + access token solo en cookie httpOnly

- **Descripción**: tres correcciones al flujo de autenticación:
  1. **Login con cuenta de Google existente (bug raíz)**: en
     `GoogleSocialLoginSerializer.validate`, el chequeo `if not
login.is_existing:` corría ANTES de `complete_social_login()`, que es donde
     allauth ejecuta el `lookup()`. Como `is_existing` es una property que
     devuelve `False` hasta ese lookup, SIEMPRE entraba a la rama de "cuenta
     nueva" y, al no recibir `nombre_usuario`/`fecha_nacimiento`/`genero` en el
     login, respondía 400 → el frontend mandaba a `/completar-google` incluso a
     cuentas ya vinculadas. Ahora se consulta `SocialAccount.objects.filter(
provider, uid).exists()` (mismo criterio que el `_lookup_by_socialaccount`
     interno de allauth) ANTES del chequeo: si existe, es login y no se exigen
     los campos extra.
  2. **Check de email duplicado muerto**: en el segundo `if not
login.is_existing`, `getattr(login.user, "email", None)` usaba `email`,
     pero el modelo expone `correo`; el chequeo nunca aplicaba. Corregido a
     `correo`.
  3. **Access token fuera de localStorage**: el frontend ya no persiste el
     access token en `localStorage` (superficie XSS). El backend autentica vía
     cookie httpOnly (`JWTCookieAuthentication` ya era el auth class por
     defecto) y el `Authorization: Bearer` desde localStorage era redundante. Se
     eliminaron `getAccessToken`/`storeTokens`/`clearTokens` y la opción `auth`
     de `apiFetch`; las cookies viajan con `credentials: "include"`.
- **Motivo**: corregir el bug reportado (iniciar sesión con Google mandaba a la
  pantalla de registro) y endurecer el manejo de tokens (el refresh ya estaba
  fuera de localStorage; ahora el access también).
- **Archivos**: `backend/usuarios/serializers.py`, `backend/usuarios/tests.py`
  (regresión: login de cuenta existente sin campos + cuenta nueva exige campos),
  `frontend/lib/api.ts`, `frontend/lib/google-auth.ts`,
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/(public)/register/page.tsx`,
  `frontend/app/confirmar-correo/[key]/page.tsx`,
  `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx`,
  `frontend/components/Navbar.tsx`.

## 26/08/2026 — CSRF para el access token en cookie httpOnly (JWT_AUTH_COOKIE_USE_CSRF)

- **Descripción**: al quedar el access token solo en cookie httpOnly (sin header
  Bearer), se habilitó protección CSRF explícita en lugar de descansar solo en
  `SameSite=Lax`:
  1. `JWT_AUTH_COOKIE_USE_CSRF=True`: `JWTCookieAuthentication` exige el header
     `X-CSRFToken` en las mutaciones autenticadas por la cookie `access` (los
     métodos seguros GET/HEAD/OPTIONS quedan exentos).
  2. `CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS`: el frontend es otro origen
     (localhost:3000), así que Django valida el `Origin` cross-origin contra
     estos orígenes; sin esto, cualquier mutación legítima se rechazaba con
     "Referer checking failed".
  3. Endpoint `GET /api/auth/csrf/` (`CSRFTokenView` + `ensure_csrf_cookie`):
     setea la cookie `csrftoken` (legible por JS) para que el frontend la
     reenvíe como header.
  4. Frontend: `apiFetch` lee la cookie `csrftoken` (o la pide al endpoint si
     aún no existe) y manda `X-CSRFToken` en toda mutación. Relee la cookie en
     cada request, por lo que la rotación del token tras el login (dj-rest-auth
     hace `django_login` con `SESSION_LOGIN=True`, que llama `rotate_token`) es
     transparente.
- **Motivo**: resolver el pendiente del tradeoff XSS/CSRF: con cookie httpOnly la
  protección CSRF ahora valida el token en cada mutación y no solo confía en el
  `SameSite` de la cookie.
- **Archivos**: `backend/filmai/settings.py`, `backend/usuarios/views.py`
  (`CSRFTokenView`), `backend/filmai/urls.py`, `backend/usuarios/tests.py`
  (`CsrfCookieTests`, 2 casos), `frontend/lib/api.ts`.

## 26/08/2026 — Google OAuth: login abre el selector y registro completa datos (flujos distintos)

- **Descripción**: se separan los dos flujos de Google. El botón de LOGIN
  ("Iniciar sesión con Google", `GoogleButton text="signin_with"`) abre el
  selector de cuentas de Google directamente; si la cuenta ya existe entra
  directo, y si es nueva se deriva a `/completar-google`. El botón de REGISTRO
  ("Crear cuenta con Google", `GoogleLinkButton`) no abre Google: marca el
  flujo pendiente (`google_signup_pending`) y navega a `/completar-google`,
  donde se completan los datos faltantes y se toca el botón de Google
  (`signup_with`) — un único popup en todo el flujo de registro. Se elimina el
  texto que explicaba el motivo de los tokens (no aporta al usuario final).
- **Motivo**: UX — dos situaciones distintas: iniciar sesión (abrir el
  selector) vs crear cuenta (completar datos + elegir cuenta una sola vez).
- **Archivos**: `frontend/components/GoogleLinkButton.tsx` (nuevo),
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/(public)/register/page.tsx`,
  `frontend/app/completar-google/page.tsx`, `frontend/lib/google-auth.ts`.

## 26/08/2026 — Fix del id_token de un solo uso en el flujo Google de 2 pasos

- **Descripción**: tras corregir el 500 (RawPostDataException), el flujo de
  completado de cuenta Google fallaba con `400 "No se pudo autenticar con
Google."` en el segundo POST. Causa: el `id_token` de Google es de UN SOLO
  USO — allauth implementa anti-replay (`verify_jti` en
  `allauth.socialaccount.internal.jwtkit`): la primera verificación marca el
  `jti` del token en caché y cualquier reenvío del mismo token lanza
  `OAuth2Error("token already used")`. El frontend reutilizaba el mismo
  id_token (guardado en `sessionStorage`) para el paso de completado.
- **Decisión (Opción 1)**: obtener un id_token FRESCO en la pantalla de
  completado mediante re-autenticación con Google. El frontend ya no guarda ni
  reutiliza el token: guarda solo un marcador (`google_signup_pending`) para
  proteger la ruta, y `/completar-google` pide un token nuevo (botón Google con
  `text="signup_with"` para distinguirlo del de login). Se mantiene intacta la
  garantía anti-replay de allauth.
- **Archivos**: `frontend/lib/google-auth.ts`,
  `frontend/app/completar-google/page.tsx`, `frontend/components/GoogleButton.tsx`.

## 26/08/2026 — Fix del 500 en Google OAuth: no releer `request.body` en `populate_user`

- **Descripción**: el login con Google (`POST /api/auth/google/`) respondía 500
  con `django.http.request.RawPostDataException: You cannot access body after
reading from request's data stream`. En un view de DRF, `self.request.data`
  consume el stream del body al parsear el JSON; luego
  `UsuarioSocialAccountAdapter.populate_user` releía `request.body` para obtener
  los campos que Google no provee (`nombre_usuario`, `fecha_nacimiento`,
  `genero`), lo que lanzaba la excepción y derivaba en 500.
- **Solución**: esos campos ahora viajan pegados al request
  (`request.google_extra`), seteado por `GoogleSocialLoginSerializer.validate`
  desde los `attrs` ya validados antes de llamar a `complete_login`. El adapter
  los lee con `getattr(request, "google_extra", {})` y ya no toca el body.
  Se eliminó el helper `_extra_from_body`.
- **Archivos**: `backend/usuarios/serializers.py`,
  `backend/usuarios/adapter.py`, `backend/usuarios/tests.py` (regresión:
  `GoogleOAuthTests`).

## 25/08/2026 — Pendientes de revisión del PR #3 de autenticación

- **Descripción**: durante la revisión del PR #3 se identificaron los siguientes
  pendientes para notificar a su autor:
  - El frontend almacena el access token, pero no implementa la renovación
    automática mediante el refresh token cuando aquel expira.
  - El parseo inicial del `id_token` de Google queda fuera del manejo de
    excepciones y podría responder con un error 500 ante un token malformado.
  - La validación de nombres de usuario usa comparación insensible a mayúsculas,
    pero la restricción `unique=True` de la base de datos no garantiza esa misma
    unicidad en condiciones de carrera.
  - Las rutas de confirmación de correo, completado de Google y restablecimiento
    de contraseña no están incluidas entre las pantallas sin Navbar.
  - `.env.example` deja Resend como backend activo con valores incompletos; al
    copiarlo sin configurar la API key, el registro puede informar que envió el
    correo aunque el backend no lo entregue.
- **Motivo**: dejar documentados los riesgos y las diferencias detectadas entre
  el comportamiento implementado y los criterios de autenticación, seguridad y
  UI antes de continuar con el desarrollo. Estos puntos quedan como pendientes,
  no como decisiones cerradas.
- **Archivos**: `frontend/lib/api.ts`, `backend/usuarios/serializers.py`,
  `backend/usuarios/models.py`, `frontend/components/Navbar.tsx`, `.env.example`,
  `docs/05_Plan_de_Desarrollo.md`, `docs/04_Lineamientos_UI.md`.

## 25/08/2026 — Limpieza de `storeTokens` (quitar parámetro `refresh`)

- **Descripción**: se eliminó el parámetro `refresh` de `storeTokens` en el
  frontend (`storeTokens(access)`), y se actualizaron sus tres llamadores (login
  por email/contraseña, login con Google y completado de cuenta Google). También
  se reformateó `Navbar.tsx` con Prettier (una línea JSX demasiado larga).
- **Motivo**: el refresh token ya viaja como cookie httpOnly y no se persiste en
  el cliente (ver decisión del 22/08/2026); el parámetro `_refresh` era un
  remanente sin uso que generaba un warning de ESLint (`--max-warnings=0`) y
  bloqueaba el hook de pre-commit de husky para cualquier commit.
- **Archivos**: `frontend/lib/api.ts`, `frontend/lib/google-auth.ts`,
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/completar-google/page.tsx`, `frontend/components/Navbar.tsx`.

## 25/08/2026 — El lint solo corre en local; pendiente agregar CI

- **Descripción**: un warning de ESLint (`_refresh` sin uso en `storeTokens`)
  entró a `main` porque el commit que lo introdujo (`2cc3ffe`) se integró vía
  "Merge pull request" desde GitHub, que no ejecuta el hook local de husky, y el
  repo no tiene CI (no hay `.github/workflows/`). El hook de pre-commit corre en
  toda rama pero solo en la máquina de cada dev (depende de husky instalado y
  `node_modules` sincronizado), y además saltea `ruff` si Docker no está
  levantado.
- **Motivo**: documentar la causa y dejar registrada la tarea pendiente de
  agregar CI para enforzar lint/format independientemente de la máquina de cada
  integrante.
- **Tarea pendiente (asignada a Gonza)**: crear un workflow de GitHub Actions
  que corra `eslint` + `prettier` (frontend) y `ruff` (backend) en cada PR a
  `main`.
- **Archivos**: `.husky/pre-commit`, `frontend/eslint.config.mjs`,
  `frontend/.prettierrc`. Pendiente: `.github/workflows/`.

## 25/08/2026 — Arquitectura híbrida del catálogo (TMDB + PostgreSQL)

- **Descripción**: el Módulo 2 (Catálogo) adopta un modelo híbrido. El
  descubrimiento (trending, discover, search) se sirve en vivo desde la API de
  TMDB con caché Redis; PostgreSQL es la fuente de verdad para los datos del
  usuario (calificaciones, reseñas, listas) y para la búsqueda semántica
  (pgvector). No se adopta una variante "BD como única fuente" porque
  sincronizar todo TMDB no escala y rompería la búsqueda en vivo de títulos no
  sincronizados.
- **Motivo**: el plan ya describe ambos mecanismos (C-03 en vivo + C-04 sync);
  se explicita para evitar interpretar que la BD reemplaza a TMDB en discovery.
- **Archivos**: `docs/05_Plan_de_Desarrollo.md`, `backend/catalogo/`.

## 25/08/2026 — Materialización on-demand con unicidad compuesta

- **Descripción**: cuando el usuario abre el detalle o interactúa con una
  producción, ésta se materializa en `ProduccionAudiovisual` mediante un helper
  centralizado (`catalogo/services/materialization.py`). La búsqueda se hace por
  `id_tmdb` + `tipo`; la creación es atómica y, ante `IntegrityError` por
  concurrencia, se resuelve con un `get()` posterior. No se ejecutan llamadas
  externas (TMDB/embeddings) dentro de una transacción abierta.
- **Motivo**: `id_tmdb` no es único entre películas y series; la unicidad real
  es compuesta `(id_tmdb, tipo)` (ya definida como `uq_produccion_tmdb_tipo`).
  Esto permite calificar o listar una producción encontrada por búsqueda aunque
  la sync diaria nunca la haya traído.
- **Archivos**: `backend/catalogo/models.py`, `backend/catalogo/services/`.

## 25/08/2026 — Embeddings síncronos en la materialización (adelanto parcial de B-06)

- **Descripción**: el embedding se genera de forma síncrona dentro del helper
  de materialización, después de persistir la producción. Si el proveedor de
  embeddings falla, la producción queda creada con `embedding IS NULL` y el
  backfill (C-04b) la completa después. Se registran `content_hash` y la versión
  del modelo para no recomputar embeddings innecesarios.
- **Motivo**: una producción materializada on-demand en Fase 1 quedaría sin
  embedding hasta el cron si no se genera acá, y entonces no aparecería en
  búsquedas semánticas. El costo es una llamada adicional similar a la de TMDB.
- **Implicación**: adelanta infraestructura de B-06 (pgvector,
  `ProduccionEmbedding`, servicio de embeddings y proveedor BGE-M3/Ollama).
- **Archivos**: `backend/catalogo/`, `docker-compose.yml`,
  `docs/05_Plan_de_Desarrollo.md`.

## 25/08/2026 — División de C-04 y caché Redis en todos los entornos

- **Descripción**: C-04 se divide en C-04a (Fase 1: materialización +
  embeddings) y C-04b (Fase 3: Celery para backfill, mantenimiento del catálogo
  popular, regeneración ante cambio de modelo y red de seguridad
  `embedding IS NULL`). La caché de TMDB usará Redis también en desarrollo (no
  LocMem) para probar el mismo comportamiento que en producción. El sync
  actualizará únicamente campos provenientes de TMDB, sin pisar metadatos
  locales.
- **Motivo**: desacoplar el funcionamiento del catálogo de la dependencia del
  cron; que la sync pase a ser mantenimiento y no un prerrequisito.
- **Archivos**: `docs/05_Plan_de_Desarrollo.md`, `backend/filmai/settings.py`,
  `backend/catalogo/`.

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
    - dependencia `bcrypt`); cumple RNF #2 / RNF #12.
  - **`is_active` (Opción A1)**: propiedad derivada de `estado` (getter
    `estado == ACTIVA`) con _setter_ (`True → estado = ACTIVA`, `False` =
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
     _Desviación consciente del plan_: P-07 define 4 ítems (Mi perfil, Mis
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
     alternativa HTML (`EmailMultiAlternatives`). Los destinatarios `to`,
     `cc` y `bcc` van como campos separados (sin fusionar en `to` para no
     exponer los BCC ni cambiar la semántica de los CC). En producción, la
     ausencia de `RESEND_API_KEY` rompe el arranque (`ImproperlyConfigured`
     vía `filmai.email_validation`) en lugar de degradar el envío a un
     "éxito" silencioso.
  2. **Redirección de destinatario para testing sin dominio propio**: Resend
     solo permite enviar desde `onboarding@resend.dev` y únicamente al email
     dueño de la cuenta (403 con cualquier otro destinatario). Si
     `RESEND_TEST_RECIPIENT` está definido, TODO email saliente se redirige a
     esa dirección (solo en entornos no productivos): la confirmación de
     cualquier registro llega a esa bandeja y el link sigue siendo válido para
     la cuenta registrada. En producción (`DEBUG=False`) la variable se
     rechaza al arranque. Con dominio propio verificado: borrar la variable y
     cambiar `DEFAULT_FROM_EMAIL`.
  3. **Variables** (`.env` + `.env.example`): `EMAIL_BACKEND`,
     `RESEND_API_KEY`, `RESEND_TEST_RECIPIENT`, `DEFAULT_FROM_EMAIL`. El
     fallback a console backend solo aplica en desarrollo (sin `EMAIL_BACKEND`
     configurado); en producción el backend debe elegirse explícitamente.
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
     Si el render o el envío del email falla, se loguea y se responde el
     mismo mensaje genérico (no se rompe el request ni se revela la cuenta).
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
     validación inline). `CACHES` usa Redis en producción (apunta al servicio
     `redis` de Docker Compose) y LocMem en desarrollo; así los límites
     aplican globalmente entre workers.
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

## 24/08/2026 — Revisión de calidad: rate limit de disponibilidad, contraste de emails y pin de allauth

- **Descripción**: se aplicaron correcciones surgidas de la revisión de
  calidad:
  1. **Rate limit de disponibilidad de username (A-05)**:
     `UsernameDisponibleView` agrega `ScopedRateThrottle` con el scope
     `username_disponible` (`30/min` por IP) registrado en
     `DEFAULT_THROTTLE_RATES`, para acotar la enumeración de usernames en un
     endpoint anónimo sin entorpecer el tipeo normal.
  2. **Contraste del email de restablecimiento**: el texto secundario (13px)
     del template `recuperar_contrasena_message.html` pasa de `#777777` a
     `#a0a0a8` para cumplir el contraste 4.5:1 contra `#161625`.
  3. **Pin de django-allauth**: se fija `django-allauth[socialaccount]==65.19.1`
     en `requirements.txt` (antes `>=64.0.0,<66.0`) porque
     `allauth.account.internal.flows.email_verification` (usado por
     `ConfirmarCorreoView`) no es API pública y puede cambiar entre releases
     menores; 65.19.1 es la versión instalada y probada en el contenedor.
- **Motivo**: hallazgos de la revisión de calidad (seguridad anti-enumeración,
  accesibilidad del correo y reproducibilidad de dependencias).
- **Archivos**: `backend/usuarios/views.py`, `backend/filmai/settings.py`,
  `backend/templates/registration/recuperar_contrasena_message.html`,
  `backend/requirements.txt`.

## 26/08/2026 — Revisión de PR: email duplicado en Google OAuth, CSRF del login, decodes de URL y sincronización de documentación

- **Descripción**: correcciones surgidas de la revisión del PR (feat/Autenticación):
  1. **Check de email duplicado movido ANTES de `complete_social_login`**:
     en `GoogleSocialLoginSerializer.validate`, el chequeo
     `Usuario.objects.filter(correo__iexact=...)` ahora corre dentro de la
     rama `not es_existente` (junto a la validación de campos faltantes),
     antes de llamar a allauth. Con `SOCIALACCOUNT_AUTO_SIGNUP=True`, allauth
     puede crear el usuario dentro de `complete_social_login`
     (`flows.signup.process_signup`) cuando el usuario existente no tiene
     `EmailAddress` (p.ej. los del seed): un chequeo a posteriori llegaba
     tarde y dejaba una segunda fila `Usuario` pese a responderse 400 (la
     unique de PostgreSQL solo cubre el caso exacto). Se agrega test de
     regresión que verifica el error 400, que la fila existente queda como
     única (`Usuario.objects.count() == 1`) y que
     `complete_social_login` no se invoca.
  2. **`LenientJWTCookieAuthentication` propaga `PermissionDenied`**: el
     `except Exception` genérico tragaba el `PermissionDenied` que
     `JWTCookieAuthentication.enforce_csrf` lanza al fallar CSRF
     (`JWT_AUTH_COOKIE_USE_CSRF=True`) cuando el browser trae una cookie
     `access` previa; el login quedaba sin protección CSRF (pasaba por
     anónimo). Ahora esa excepción se re-lanza (403) y solo las cookies
     inválidas/vencidas se tratan como anónimas.
  3. **URIError al decodificar parámetros URL**: `decodeURIComponent` lanza
     URIError ante secuencias inválidas (p.ej. "%" suelto). En
     `app/confirmar-correo/[key]/page.tsx` el throw dejaba la página trabada
     en "cargando": ahora el decode está protegido y deriva al estado de
     enlace inválido ("error"). En
     `app/restablecer-contrasena/[uid]/[token]/page.tsx` un URIError caía en
     el mensaje de fallo de contraseña: se clasifica como `enlace_invalido`.
  4. **Sincronización con la implementación real**:
     - A-08 (docs/05) ya no describe tokens en storage: logout basado en
       cookies (`POST /api/auth/logout/` invalida refresh y limpia las
       cookies httpOnly).
     - Filas C-08 y P-03 (docs/05): los pipes internos (`POST | PUT |
DELETE`, `GET | PUT`) van escapados para que cada fila tenga las 6
       columnas del encabezado; Q-05/Q-06 pierden la celda extra de
       responsable (lo cubren el título del módulo y el resumen final).
     - docs/03 JSON: arista e-usuario-calificacion pasa de `1..* ─ 0..*` a
       `1..1 ─ 0..*` (FK obligatoria: cada calificación pertenece a
       exactamente un usuario; un usuario puede tener cero o más).
     - Skill conventional-commits: "12 tipos" → "11 tipos" (la tabla tiene
       11 y coincide con references/examples.md).
     - Skill humanizer: el ejemplo de Lisboa elimina detalles inventados
       (fotos, popularidad del tranvía, filas, planes futuros); conserva
       solo hechos presentes en la entrada.
  5. **No aplicado (verificado contra settings.py)**: propuesta de
     `SameSite=None; Secure` para JWT/CSRF cookies. El despliegue actual es
     mismo sitio (localhost:3000 → localhost:8000 comparten host registrable)
     y la decisión del 26/08/2026 (`JWT_AUTH_COOKIE_USE_CSRF` +
     `CSRF_TRUSTED_ORIGINS`) hace que la protección CSRF no dependa del
     SameSite; forzar `SameSite=None` + `Secure=True` rompería las cookies en
     desarrollo http. Se reconsidera si el frontend y la API terminan en
     sitios distintos.
- **Motivo**: hallazgos verificados de la revisión del PR; el check duplicado
  y el manejo del CSRF eran huecos reales de seguridad/atrición de datos.
- **Archivos**: `backend/usuarios/serializers.py`, `backend/usuarios/views.py`,
  `backend/usuarios/tests.py`,
  `frontend/app/confirmar-correo/[key]/page.tsx`,
  `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx`,
  `docs/05_Plan_de_Desarrollo.md`,
  `docs/03_DiagramaClases_DiagramaTablas.json`,
  `.opencode/skills/conventional-commits/SKILL.md`,
  `.opencode/skills/humanizer/SKILL.md`.

## 26/08/2026 — Errores globales DRF excluidos del mapa de campos en el frontend (400 de /completar-google sin campos marcados)

- **Fecha**: 26/08/2026
- **Descripción**: al completar el registro con Google en `/completar-google`
  se mostraba "Corregí los campos marcados y tocá de nuevo el botón de
  Google." sin ningún campo resaltado, y el backend registraba
  `POST /api/auth/google/ 400` con body de 55 bytes. Verificación: renderizado
  con `JSONRenderer` (dentro del contenedor, settings reales) de todos los
  bodies posibles del endpoint; solo
  `{"non_field_errors":["El correo ya está registrado."]}` mide exactamente
  55 bytes. La causa era doble:
  1. **Backend (correcto, no modificado)**: la cuenta de Google usada tiene un
     correo que ya existe como `Usuario` local sin `SocialAccount` vinculado;
     el serializer toma la rama de registro nuevo y rechaza por email
     duplicado (`GoogleSocialLoginSerializer.validate`, chequeo UNIQUE_EMAIL).
     Es un error global (no de campo), y es el comportamiento previsto hasta
     decidir si se hace auto-vinculación.
  2. **Frontend (bug)**: `extraerErroresPorCampo` trataba TODAS las claves del
     body como si fueran campos, incluida `non_field_errors`. Con
     `{non_field_errors: ["El correo ya está registrado."]}` el objeto tenía
     claves > 0, así que `/completar-google` entraba en la rama de errores de
     campo, mostraba el mensaje genérico de "corregí los campos" e intentaba
     marcar el inexistente campo `non_field_errors`, que nunca se renderiza.
     Fix: `extraerErroresPorCampo` ahora omite `non_field_errors` y `detail`;
     esos mensajes llegan a las pantallas por la vía ya existente
     (`extractError` → `ApiError.message`). En `/completar-google` el usuario ve
     ahora "El correo ya está registrado."; los errores reales de campo (p.ej.
     nombre de usuario ocupado) siguen marcándose inline, y el banner genérico
     solo aparece cuando hay errores de campo genuinos. Los otros dos llamadores
     (`register`, restablecer contraseña) quedan verificados: no dependían de
     recibir claves globales en el mapa.
- **Motivo**: error reportado por el usuario; el mensaje genérico indicaba una
  acción imposible ("campos marcados") porque la clasificación backend/global
  vs campo se hacía mal en el frontend.
- **Archivos**: `frontend/lib/api.ts`.

## 26/08/2026 — Mensaje personalizado para correo ya registrado en Google OAuth (se mantiene el rechazo)

- **Fecha**: 26/08/2026
- **Descripción**: ante un registro con Google cuyo correo ya existe como
  cuenta tradicional (sin `SocialAccount` vinculado), se decide MANTENER el
  rechazo actual (no auto-vincular cuentas) pero reemplazar el mensaje
  genérico "El correo ya está registrado." por uno que explique la situación:
  "Ya existe una cuenta registrada con este correo. Iniciá sesión con tu
  contraseña." El mensaje viaja como error global (`non_field_errors`) y el
  frontend lo muestra en la parte superior del formulario de
  `/completar-google` gracias a la corrección previa de
  `extraerErroresPorCampo` (ver decisión anterior del mismo día). La prueba
  unitaria de email duplicado (`usuarios/tests.py`) se actualiza al nuevo
  texto.
- **Motivo**: pedido explícito del usuario; el mensaje anterior no explicaba
  por qué Google "no funciona" cuando el problema es una cuenta preexistente
  con contraseña.
- **Archivos**: `backend/usuarios/serializers.py`, `backend/usuarios/tests.py`.
## 11/09/2026 — Provisión atómica de recursos iniciales de usuario

- **Fecha**: 11/09/2026
- **Descripción**: se mantiene la señal `post_save` como disparador único de
  las listas y el chat inicial, pero cada flujo de alta se envuelve en una
  transacción para que un fallo revierta también el `Usuario`. El MVP requiere
  exactamente un chat por usuario; se agrega una restricción de unicidad sobre
  `Chat.usuario`. La futura funcionalidad de chats múltiples reemplazará esa
  restricción mediante una migración. Se incorpora el comando idempotente
  `reparar_recursos_usuarios` para auditar y reparar datos históricos o
  importados; no se ejecuta en el login ni en cada request.
- **Motivo**: antes, la transacción de la señal sólo protegía listas y chat,
  por lo que una falla podía dejar una cuenta persistida e incompleta.
- **Archivos**: `backend/usuarios/models.py`, `backend/usuarios/adapter.py`,
  `backend/usuarios/serializers.py`, `backend/usuarios/signals.py`,
  `backend/usuarios/provisioning.py`,
  `backend/usuarios/management/commands/reparar_recursos_usuarios.py`,
  `backend/chatbot/models.py`, su migración y pruebas.

## 13/09/2026 — Corrección de sintaxis en las rutas del catálogo

- **Fecha**: 13/09/2026
- **Descripción**: se restauraron las comas separadoras en las rutas de detalle
  de película y serie. Su ausencia impedía importar `catalogo.urls`, por lo que
  Django no podía ejecutar las migraciones ni sus system checks. Se ajustó además
  el formato de la ruta de Swagger para que Ruff valide el backend sin cambios
  pendientes.
- **Motivo**: el backend quedaba en bucle de reinicio y CI reportaba un error de
  sintaxis antes de evaluar los endpoints, incluido `KeywordsView`, que existe y
  está correctamente importado.
- **Archivos**: `backend/catalogo/urls.py`, `backend/filmai/urls.py`,
  `docs/decisiones.md`.

## 14/09/2026 — Rutas de detalle sin conversor `int:`: 400 en vez de 404 ante `id_tmdb` no entero

- **Fecha**: 14/09/2026
- **Descripción**: `catalogo/urls.py` declaraba la ruta de detalle de película
  con `<int:id_tmdb>` y la de serie con `<id_tmdb>`. Con el conversor `int:`,
  un `id_tmdb` no entero no matchea la URL y Django responde 404 antes de
  llegar a la vista, mientras que la ruta de serie sí llegaba a `_int_param` y
  devolvía 400: dos endpoints hermanos con comportamientos distintos ante la
  misma entrada inválida. La spec de C-03
  (`openspec/specs/tmdb-endpoints/spec.md`, "Invalid params rejected") exige
  400 sin llamar a TMDB. Se quita el conversor `int:` de la ruta de película
  para que ambas deleguen la validación en `_int_param`.
  El bug no fue detectado por `ParamValidationTest` porque ese test invoca
  `MovieDetailView.as_view()(request, id_tmdb="not-an-id")` directamente,
  salteando el ruteo de Django. Se agrega
  `EndpointIntegrationTest.test_non_integer_detail_id_returns_400_through_url_routing`,
  que recorre la URL real con `APIClient` sobre ambas rutas.
- **Motivo**: hallazgo durante la auditoría de `docs/05_Plan_de_Desarrollo.md`
  contra el código (14/09/2026); incumplía la spec ya archivada de C-03.
- **Archivos**: `backend/catalogo/urls.py`, `backend/catalogo/tests.py`.
