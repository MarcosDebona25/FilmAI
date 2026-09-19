# Graph Report - FilmAI  (2026-09-19)

## Corpus Check
- 191 files · ~632,357 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2724 nodes · 5343 edges · 189 communities (138 shown, 36 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 310 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6450a446`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TMDBClient
- Modelos de Datos y de Diseño (doc 03)
- usuarios/views.py
- FilmAI
- ResendBackend
- Canonical Spec: tmdb-client
- UsuarioPerfilSerializer
- UsuarioFactory
- filmai/tests.py
- components.json
- ._serializer_google
- package.json
- resumeSession
- register/page.tsx
- Command
- compilerOptions
- initGlobalBar
- Navbar.tsx
- EndpointIntegrationTest
- completar-google/page.tsx
- login/page.tsx
- apiFetch
- materializar
- devDependencies
- dependencies
- Usuario
- button.tsx
- live-browser.js
- scripts
- ConfirmarCorreoTests
- [token]/page.tsx
- ValidadoresContrasenaTests
- FilmAI Collage Poster Design — Option 2
- Command
- UsuarioManager
- TMDBError
- connectSSE
- nombre_completo
- modern-screenshot.umd.js
- ListasEndpointsTests
- usuarios/tests.py
- manage.py
- scheduleAcceptCleanup
- initPageChat
- Collage Poster Option 3
- middleware.ts
- construir_texto_canonico
- CatalogoConfig
- ChatbotConfig
- ListasConfig
- Migration
- sync_catalogo_diaria
- pre-commit
- catalogo/migrations/0001_initial.py
- catalogo/migrations/0002_initial.py
- 0003_produccionaudiovisual_keywords.py
- chatbot/migrations/0001_initial.py
- chatbot/migrations/0002_initial.py
- entrypoint.sh
- asgi.py
- wsgi.py
- listas/migrations/0001_initial.py
- listas/migrations/0002_initial.py
- 0003_alter_usuario_nombre_usuario.py
- postcss.config.mjs
- Requirements
- catalogo/views.py
- celery.py
- Requirements
- listas/views.py
- Gemini Generated Avatar Image
- File Icon (file.svg)
- Globe Icon (globe.svg)
- Movies Icon (icons8-movies-32.png)
- Window Icon (window.svg)
- setLiveState
- el
- catalogo/tests.py
- renderDesignVisual
- Requirements
- backfill_embeddings
- provisionar_recursos_por_defecto
- 0004_alter_usuario_avatar_id_alter_usuario_correo_and_more.py
- captureElementToBlob
- Responsive Design
- handleManualEditActivity
- onboard.md
- impeccable/SKILL.md
- bolder.md
- The Toolkit
- Humanizer
- Requirements
- createLiveBrowserSessionState
- createLiveBrowserDomHelpers
- animate.md
- live.md
- Handle `generate`
- Generate Report
- New visual work
- optimize.md
- Quality Rules
- TMDBClientCache
- Scan mode (approach C: auto-extract, then confirm descriptive language)
- FILLER AND HEDGING
- critique.md
- Simplify the Design
- Hardening Dimensions
- Humanizer: Remove AI Writing Patterns
- clarify.md
- Nielsen's 10 Heuristics
- Generate Combined Critique Report
- document.md
- polish.md
- quieter.md
- Init flow
- Common Cognitive Load Violations
- iOS platform
- Operate mode depth (and Read notes)
- Shape
- LANGUAGE AND GRAMMAR PATTERNS
- Adaptation Strategies
- Android platform
- colorize.md
- Persona-Based Design Testing
- 0003_chat_unico_por_usuario_mvp.py
- Extract Flow
- resolveLiveInjectionAnchor
- STYLE PATTERNS
- CONTENT PATTERNS
- Generate Report
- Cognitive Load Assessment
- Impeccable Asset Producer
- Impeccable Finish Reviewer
- Impeccable Manual Edit Applier
- live-browser-ignores.js
- vercel-quality
- LoginDualTests
- Diagnostic Scan
- seed.py
- Visualize: Direction Comps & Asset Production
- impeccable
- TMDBClientCacheTest
- ProduccionAudiovisual
- PERSONALITY AND SOUL
- Impeccable Documenter
- COMMUNICATION PATTERNS
- Heuristics Scoring Guide
- onAnnotDown
- patch
- Design: Daily Catalog Sync + Embedding Backfill (C-04b)
- Proposal: Daily Catalog Sync + Embedding Backfill (C-04b, CU-021)
- Reglas
- ProduccionEmbedding
- Requirements
- LoginSerializer
- TMDBClientTest
- Tasks: Daily Catalog Sync + Embedding Backfill (C-04b)
- Conventional Commits
- listas/serializers.py
- Tiene
- examples.md
- Lista
- OpenSpec Config
- 0004_produccionembedding.py
- 0005_produccionaudiovisual_fecha_enriquecimiento.py
- services/__init__.py
- 0003_lista_nombre_case_insensitive.py
- doctor.md
- live-setup.md
- _ids_cambiados
- Diagnostic Scan
- GoogleSocialLoginSerializer
- ListaItemCursorPagination
- Command guidance

## God Nodes (most connected - your core abstractions)
1. `UsuarioFactory` - 42 edges
2. `TMDBClient` - 39 edges
3. `materializar()` - 37 edges
4. `Usuario` - 34 edges
5. `setLiveState()` - 32 edges
6. `resumeSession()` - 32 edges
7. `connectSSE()` - 31 edges
8. `showToast()` - 30 edges
9. `ListasEndpointsTests` - 30 edges
10. `el()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `Lint/Format Gate` --semantically_similar_to--> `Backend CI Job (Ruff)`  [INFERRED] [semantically similar]
  AGENTS.md → .github/workflows/ci.yml
- `Lint/Format Gate` --semantically_similar_to--> `Frontend CI Job (ESLint + Prettier)`  [INFERRED] [semantically similar]
  AGENTS.md → .github/workflows/ci.yml
- `Backend Service (filmai_backend)` --semantically_similar_to--> `Django`  [INFERRED] [semantically similar]
  docker-compose.yml → README.md
- `PostgreSQL Service (filmai_db)` --semantically_similar_to--> `PostgreSQL 16`  [INFERRED] [semantically similar]
  docker-compose.yml → README.md
- `Frontend Service (filmai_frontend)` --semantically_similar_to--> `Next.js 15 (App Router)`  [INFERRED] [semantically similar]
  docker-compose.yml → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Docker Compose Services** — docker_compose_db, docker_compose_redis, docker_compose_backend, docker_compose_frontend, docker_compose_network [EXTRACTED 1.00]
- **FilmAI Tech Stack** — readme_django, readme_django_rest_framework, readme_postgresql, readme_redis, readme_celery, readme_nextjs, readme_tailwind, readme_shadcn [EXTRACTED 1.00]
- **Casos de Uso del sistema FilmAI** — docs_02_especificacion_de_requerimientos_cu_001, docs_02_especificacion_de_requerimientos_cu_003, docs_02_especificacion_de_requerimientos_cu_008, docs_02_especificacion_de_requerimientos_cu_013, docs_02_especificacion_de_requerimientos_cu_015, docs_02_especificacion_de_requerimientos_cu_021 [EXTRACTED 1.00]
- **Catálogo híbrido y corpus semántico** — docs_decisiones_arquitectura_hibrida, docs_03_modelos_de_datos_y_de_diseno_catalogo_materializado, docs_03_modelos_de_datos_y_de_diseno_produccion_embedding, docs_03_modelos_de_datos_y_de_diseno_busqueda_semantica, docs_03_modelos_de_datos_y_de_diseno_sincronizacion_celery [INFERRED 0.85]
- **Stack de autenticación y modelo de usuario** — docs_03_modelos_de_datos_y_de_diseno_modelo_usuario, docs_decisiones_usuario_unificado, docs_decisiones_autenticacion_allauth, docs_decisiones_cookies_http_only_csrf, docs_decisiones_estado_ciclo_vida [INFERRED 0.85]

## Communities (189 total, 36 thin omitted)

### Community 0 - "TMDBClient"
Cohesion: 0.12
Nodes (7): TMDBClient, CatalogoSettingsTest, SimpleTestCase, Reparto y directores (C-04a). Los endpoints de detalle de TMDB NO traen cast ni…, Lista de cambios (C-04b, fase 2). `/{tipo}/changes` devuelve los IDs que TMDB…, TMDBChangesTest, TMDBCreditsTest

### Community 1 - "Modelos de Datos y de Diseño (doc 03)"
Cohesion: 0.11
Nodes (47): Chatbot basado en LLM para recomendaciones personalizadas, Presentación de la Idea-Proyecto (doc 01), FilmAI — Plataforma Web de Reseñas Cinematográficas con Recomendaciones Inteligentes, CU-001: Crear cuenta de usuario, CU-003: Iniciar sesión, CU-008: Visualizar Catálogo, CU-013: Interactuar con el chatbot, CU-015: Gestionar Reseña y Calificación (ABM) (+39 more)

### Community 2 - "usuarios/views.py"
Cohesion: 0.05
Nodes (39): EnlaceRestablecimientoInvalido, Exception, Señala un ``uid`` o token de restablecimiento inválido o vencido., Solicitud de restablecimiento sin revelar si un correo está registrado., Valida el enlace y persiste la nueva contraseña., RecuperarContrasenaSerializer, RestablecerContrasenaSerializer, EmailRateThrottle (+31 more)

### Community 3 - "FilmAI"
Cohesion: 0.07
Nodes (52): Backend CI Job (Ruff), CI GitHub Workflow, ESLint, Frontend CI Job (ESLint + Prettier), .husky/pre-commit Hook, Prettier, Ruff, docs/decisiones.md Decision Log (+44 more)

### Community 4 - "ResendBackend"
Cohesion: 0.24
Nodes (7): Devuelve la parte HTML si el mensaje es multipart/alternative., Envía `EmailMessage` vía `resend.Emails.send` (API REST de Resend). - Requiere…, ResendBackend, override_settings, patch, ResendBackendTests, BaseEmailBackend

### Community 5 - "Canonical Spec: tmdb-client"
Cohesion: 0.33
Nodes (10): httpx.MockTransport Testing, Canonical Spec: tmdb-cache, Canonical Spec: tmdb-client, Thin Client (Raw JSON), TMDBClient (C-01), TMDBClient Configuration, TMDB Detail Methods, TMDB Discovery Methods (+2 more)

### Community 6 - "UsuarioPerfilSerializer"
Cohesion: 0.07
Nodes (17): Meta, Representación del usuario autenticado (endpoints `/api/auth/user/`). El…, Serializer para actualizar el perfil del usuario. Solo permite modificar campos…, Valida que avatar_id sea uno de los avatares disponibles., Valida que la fecha de nacimiento no sea futura y el usuario tenga al menos 13…, UsuarioDetallesSerializer, UsuarioPerfilSerializer, AvatarValidacionTests (+9 more)

### Community 7 - "UsuarioFactory"
Cohesion: 0.11
Nodes (13): Meta, Crea usuarios activos con contraseña hasheada., UsuarioFactory, CsrfCookieTests, Recuperación de contraseña (CU-020 / A-07). Cubre: envío del email con enlace…, Sin nombre ni apellido, el saludo es "Hola usuario"., El throttle por email permite 5 solicitudes por día, luego bloquea., Protección CSRF del access token en cookie httpOnly (JWT_AUTH_COOKIE_USE_CSRF).… (+5 more)

### Community 8 - "filmai/tests.py"
Cohesion: 0.09
Nodes (15): Backend de email de Django sobre la API HTTP de Resend. Motivación y diseño…, Validación de la configuración de email al arranque. En producción la ausencia…, Levanta ``ImproperlyConfigured`` si la config de email es inválida. Solo aplica…, validar_configuracion_email(), Django settings for filmai project. Generated by 'django-admin startproject'…, CeleryAppTests, ConfiguracionEmailTests, SimpleTestCase (+7 more)

### Community 9 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 10 - "._serializer_google"
Cohesion: 0.24
Nodes (6): Construye el serializer con el request en el estado post-parseo de DRF. Deja…, Fija `SocialAccount.objects.filter(...).exists()` al valor deseado., Regresión: una cuenta de Google ya vinculada inicia sesión SIN los campos extra…, El login no debe sobrescribir cambios de perfil hechos en FilmAI., Una cuenta de Google NUEVA (sin SocialAccount) exige los campos que Google no…, Regresión: el chequeo de email duplicado case-insensitive corre ANTES de…

### Community 11 - "package.json"
Cohesion: 0.08
Nodes (23): compat, __dirname, eslintConfig, __filename, name, private, version, @base-ui/react (+15 more)

### Community 12 - "resumeSession"
Cohesion: 0.07
Nodes (65): applyParamDefaults(), applyParamValue(), applyPlaceholderDimensions(), applySavedSessionMeta(), buildInsertPlaceholderSnapshotFromDom(), clampVariantIndex(), clearHandled(), closedClipPath() (+57 more)

### Community 13 - "register/page.tsx"
Cohesion: 0.14
Nodes (12): Campo, Errores, GENEROS, maxFechaNacimiento(), RegisterPage(), onBlurCampo(), validarCampo(), VALIDADORES (+4 more)

### Community 14 - "Command"
Cohesion: 0.15
Nodes (9): atomic, Command, BaseCommand, Crea el catálogo repartido entre películas y series., Cada usuario califica un subconjunto aleatorio del catálogo. Se pasan `usuario`…, Crea las 3 listas predeterminadas y algunas personalizadas por usuario., Usa el chat por defecto (creado por la señal) y agrega mensajes., Borra los datos de las apps de negocio (orden de hijos a padres). El borrado en… (+1 more)

### Community 15 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 16 - "initGlobalBar"
Cohesion: 0.12
Nodes (28): agentStatusText(), barPaletteForTheme(), brandMarkSvg(), buildParamsPanel(), cursorForInsertAxis(), detectPageTheme(), ensureAgentPollTooltip(), formatRangeValue() (+20 more)

### Community 17 - "Navbar.tsx"
Cohesion: 0.13
Nodes (13): inter, metadata, roboto, iniciales(), NAV_LINKS, Navbar(), logout(), noImplementado() (+5 more)

### Community 19 - "completar-google/page.tsx"
Cohesion: 0.19
Nodes (13): Campo, CompletarGooglePage(), onBlurCampo(), onGoogle(), validarCampo(), Errores, GENEROS, maxFechaNacimiento() (+5 more)

### Community 20 - "login/page.tsx"
Cohesion: 0.16
Nodes (13): LoginForm(), cerrarModalRecuperar(), onGoogle(), onSubmitRecuperar(), GoogleButton(), GoogleButtonProps, GoogleCredentialResponse, Window (+5 more)

### Community 21 - "apiFetch"
Cohesion: 0.16
Nodes (17): ConfirmarCorreoPage(), Estado, onSubmit(), API_URL, ApiError, apiFetch(), ApiOptions, apiUrl() (+9 more)

### Community 22 - "materializar"
Cohesion: 0.11
Nodes (9): materializar(), Garantiza que la producción exista en la base con su embedding encolado. Recibe…, MaterializacionIdempotenteTests, MaterializacionPeliculaTests, MaterializacionSerieTests, Alta de una película nueva: mapeo de campos y encolado (C-04a)., El worker nunca debe recibir el id de una fila que aún no existe.…, Alta de una serie: TMDB usa otras claves para la misma información. (+1 more)

### Community 23 - "devDependencies"
Cohesion: 0.15
Nodes (13): devDependencies, eslint, eslint-config-next, eslint-config-prettier, @eslint/eslintrc, husky, prettier, tailwindcss (+5 more)

### Community 24 - "dependencies"
Cohesion: 0.17
Nodes (12): dependencies, @base-ui/react, class-variance-authority, clsx, lucide-react, next, react, react-dom (+4 more)

### Community 25 - "Usuario"
Cohesion: 0.07
Nodes (17): AbstractBaseUser, register, Admin para el modelo personalizado de usuario. Adapta `UserAdmin` de Django a…, UsuarioAdmin, Meta, Logueable solo si la cuenta está en estado Activa., Permite que Django/allauth activen la cuenta (`is_active = True`), Cliente de la plataforma y, según sus flags, administrador del panel. (+9 more)

### Community 26 - "button.tsx"
Cohesion: 0.17
Nodes (13): POSTERS, Button(), buttonVariants, cn(), Collage Posters Set (3 Design Options), Opcion 1 Collage Poster Image, FilmAI Landing Marketing / Hero Visual, Movie Poster Collage (Depicted Content) (+5 more)

### Community 27 - "live-browser.js"
Cohesion: 0.04
Nodes (113): addManualContextText(), applyEditing(), applyGlobalBarLabelState(), applyPlaceholderSizingStyles(), attachSteerFocusGuard(), bindEditBadgeProxy(), bufferToBase64(), buildColorModels() (+105 more)

### Community 28 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, format, format:check, lint, prepare, start

### Community 30 - "[token]/page.tsx"
Cohesion: 0.39
Nodes (7): decodificarParametro(), EnlaceInvalido, Estado, RestablecerContrasenaPage(), onSubmit(), validarConfirmacion(), validarPassword()

### Community 31 - "ValidadoresContrasenaTests"
Cohesion: 0.07
Nodes (16): Contraseñas con menos de 8 caracteres deben ser rechazadas., Contraseñas con más de 20 caracteres deben ser rechazadas., Contraseñas sin mayúsculas deben ser rechazadas., Contraseñas sin minúsculas deben ser rechazadas., Contraseñas sin dígitos deben ser rechazadas., Contraseñas sin caracteres especiales deben ser rechazadas., Cada carácter especial permitido debe ser aceptado individualmente., Una contraseña de exactamente 8 caracteres debe ser aceptada si cumple todas… (+8 more)

### Community 32 - "FilmAI Collage Poster Design — Option 2"
Cohesion: 0.29
Nodes (7): FilmAI Collage Poster Design — Option 2, Collage Poster Design Option 2 of 3, FilmAI Branding / Hero Identity, Opcion 2 Collage Poster Image, Marketing / Hero Visual Asset, Movie/Series Poster Collage (Visual Content), Collage Poster Design Options Set (1–3)

### Community 33 - "Command"
Cohesion: 0.33
Nodes (3): Command, BaseCommand, Comando de desarrollo: verifica la integración con Resend. Uso: python…

### Community 34 - "UsuarioManager"
Cohesion: 0.47
Nodes (3): Manager que usa `correo` como identificador de autenticación.…, UsuarioManager, BaseUserManager

### Community 35 - "TMDBError"
Cohesion: 0.14
Nodes (19): Exception, TMDB rejected the request because its rate limit was exceeded., TMDB could not find the requested resource., TMDB rejected the request as invalid., TMDB returned a server-side error., The request could not reach TMDB or its response could not be read., Base exception for TMDB client failures., tmdb_exception_handler() (+11 more)

### Community 36 - "connectSSE"
Cohesion: 0.08
Nodes (49): abandonForeignSession(), applyOriginalAttrsToSvelteAnchor(), clearMountErrorCard(), commitAcceptedSvelteComponentToDom(), componentModuleCandidates(), connectSSE(), describeMountFailure(), detectDevServerBase() (+41 more)

### Community 37 - "nombre_completo"
Cohesion: 0.40
Nodes (4): nombre_completo(), Filtros de template para saludos en emails transaccionales., Devuelve "Nombre Apellido"; "usuario" si ambos están vacíos. Regla global para…, filter

### Community 38 - "modern-screenshot.umd.js"
Cohesion: 0.09
Nodes (55): ae(), be(), bt(), Ce(), s(), Ct(), de(), dt() (+47 more)

### Community 39 - "ListasEndpointsTests"
Cohesion: 0.07
Nodes (22): ListaFactory, Meta, ListasEndpointsTests, patch, TestCase, Evita dos cards que para el usuario representan la misma lista., El límite se aplica tras normalizar y tampoco se admiten guiones., La API sostiene la regla incluso si un cliente evita el menú UI. (+14 more)

### Community 40 - "usuarios/tests.py"
Cohesion: 0.07
Nodes (30): Adaptadores de allauth para el modelo de usuario de FilmAI., Adaptador de cuenta para el registro tradicional (dj-rest-auth)., Mapea los campos de allauth a los de ``Usuario``., Activa la cuenta al confirmar su correo de forma atómica., Envía la confirmación a la pantalla correspondiente de la SPA., Adaptador social (Google OAuth) para `usuarios.Usuario`., Persiste el alta social de forma atómica., Construye un perfil nuevo sin sobrescribir una cuenta vinculada. (+22 more)

### Community 41 - "manage.py"
Cohesion: 0.50
Nodes (3): main(), Django's command-line utility for administrative tasks., Run administrative tasks.

### Community 42 - "scheduleAcceptCleanup"
Cohesion: 0.31
Nodes (11): acceptedDomAlreadyClean(), clearHandledWrapperReloadStamp(), deferredRecoverySuperseded(), ensureAcceptedDomClean(), findAcceptedRuntimeWrappers(), handledWrapperReloadKey(), reloadAfterMissingAcceptedDom(), restoreAcceptedDomFromSnapshot() (+3 more)

### Community 43 - "initPageChat"
Cohesion: 0.09
Nodes (47): agentHasWorkInFlight(), armPageChatForTyping(), attachSteerFocusDebug(), buildSteerProcessingDots(), buildSteerQueueHint(), clearSteerAwaitTimer(), collapsePageChat(), configureVoiceContext() (+39 more)

### Community 44 - "Collage Poster Option 3"
Cohesion: 0.50
Nodes (4): FilmAI Collage Poster Design, FilmAI Hero/Marketing Asset, FilmAI Project, Collage Poster Option 3

### Community 46 - "construir_texto_canonico"
Cohesion: 0.15
Nodes (10): construir_texto_canonico(), _lista_normalizada(), Ordena alfabéticamente y descarta vacíos. TMDB no garantiza un orden estable…, Arma el texto que representa a la producción para la búsqueda semántica. Recibe…, _necesita_enriquecimiento(), Decide si hay que traer el detalle de TMDB para esta fila. Reemplaza el…, MaterializacionFrescuraTests, Cuándo una fila necesita (re)traer el detalle de TMDB (C-04b, fase 1).… (+2 more)

### Community 51 - "sync_catalogo_diaria"
Cohesion: 0.23
Nodes (5): Sync nocturna del catálogo (C-04b): refresco + descubrimiento. Dos pasadas con…, sync_catalogo_diaria(), La pasada de descubrimiento de la sync nocturna (C-04b, fase 2). `materializar`…, Hace que TMDB reporte estos IDs como modificados hoy., SyncCatalogoTests

### Community 65 - "Requirements"
Cohesion: 0.07
Nodes (26): catalog-materialization Specification, Purpose, Requirement: Concurrency safety, Requirement: Embedding enqueue, Requirement: Enrichment is recorded, not inferred, Requirement: Failure isolation, Requirement: Forced refresh, Requirement: Single materialization entry point (+18 more)

### Community 68 - "catalogo/views.py"
Cohesion: 0.17
Nodes (14): CatalogoBaseView, DiscoverView, _float_param(), _int_param(), KeywordsView, _materializar_sin_interrumpir(), MovieDetailView, NowPlayingView (+6 more)

### Community 78 - "Requirements"
Cohesion: 0.08
Nodes (25): catalog-daily-sync Specification, Known limitations, Purpose, Requirement: Discovery pass, Requirement: Embedding backfill, Requirement: Failures are per item, Requirement: Refresh pass driven by TMDB's change list, Requirement: Refresh precedes discovery (+17 more)

### Community 79 - "listas/views.py"
Cohesion: 0.13
Nodes (20): APIException, CalificacionImpideQuitarDeVistas, ItemDuplicado, ListaConflict, ListaPredeterminadaProtegida, NombreListaDuplicado, Errores de dominio que la API de listas comunica como conflictos., Conflicto de negocio con un código estable para el frontend. (+12 more)

### Community 90 - "setLiveState"
Cohesion: 0.11
Nodes (56): abortSvelteComponentInjection(), beginNewLiveConfiguration(), cancelEditing(), cancelEditingToPicking(), cancelInsertConfigure(), cleanup(), cleanupAcceptedSession(), clearAnnotations() (+48 more)

### Community 91 - "el"
Cohesion: 0.07
Nodes (56): actionLabel(), applyConfigureBarChrome(), bindConfigureCountPillTooltip(), bindConfigureInlineControlHover(), bindConfigureModifierPillHover(), buildConfigureActionControl(), buildConfigureCountControl(), buildConfigureRow() (+48 more)

### Community 92 - "catalogo/tests.py"
Cohesion: 0.08
Nodes (29): get_redis(), Modelos de la app `catalogo`. Implementa las entidades del dominio de…, dominio_a_tmdb(), Traducción entre el vocabulario de TMDB y el del dominio (C-04a). TMDB dice…, `"movie"` → `TipoProduccion.PELICULA`, `"tv"` → `TipoProduccion.SERIE`. Lanza…, Inversa de `tmdb_a_dominio`, para construir llamadas a la API de TMDB., tmdb_a_dominio(), EmbeddingProviderError (+21 more)

### Community 93 - "renderDesignVisual"
Cohesion: 0.08
Nodes (37): buildCollapsible(), buildDesignHeader(), buildListHtml(), buildRadiiModels(), copyToClipboard(), cssSafe(), designEmptyMessage(), designPanelCss() (+29 more)

### Community 94 - "Requirements"
Cohesion: 0.08
Nodes (23): Purpose, Requirement: Detail views materialize as a side effect, Requirement: Endpoint surface, Requirement: Error mapping, Requirement: Pagination passthrough, Requirement: Parameter pass-through, Requirement: Public access, Requirements (+15 more)

### Community 95 - "backfill_embeddings"
Cohesion: 0.18
Nodes (10): EstadoEmbedding, Ciclo de vida del embedding (decisión 08/09/2026). `pending` → `processing` →…, calcular_source_hash(), Huella del texto embebido (SHA-256 hexadecimal, 64 caracteres). Se guarda junto…, backfill_embeddings(), Recupera el trabajo de embeddings que quedó sin completar (C-04b).…, BackfillEmbeddingsTests, BackfillIntegracionTests (+2 more)

### Community 96 - "provisionar_recursos_por_defecto"
Cohesion: 0.13
Nodes (12): AppConfig, UsuariosConfig, Command, BaseCommand, Repara listas predeterminadas y chat faltantes de usuarios existentes., provisionar_recursos_por_defecto(), Provisión consistente de los recursos iniciales de un usuario., Asegura las listas y el único chat requeridos por el MVP. (+4 more)

### Community 98 - "captureElementToBlob"
Cohesion: 0.11
Nodes (23): averageRgb01(), captureAndEmit(), captureChromeNodes(), captureElementFromRenderedAncestor(), captureElementToBlob(), checkpointPayload(), compileShader(), cssColorToRgb01() (+15 more)

### Community 99 - "Responsive Design"
Cohesion: 0.08
Nodes (25): Assess Adaptation Challenge, Breakpoints: Content-Driven, Content Adaptation, Desktop Adaptation (Mobile → Desktop), Detect Input Method, Not Just Screen Size, Email Adaptation (Web → Email), Implement Adaptations, Layout Adaptation Patterns (+17 more)

### Community 100 - "handleManualEditActivity"
Cohesion: 0.19
Nodes (24): clearStoredManualApplyState(), fetchPendingCount(), handleManualEditActivity(), hidePendingApplyDock(), manualApplyLoadingText(), manualApplyStateKey(), manualEditEventForCurrentPage(), numberOrNull() (+16 more)

### Community 101 - "onboard.md"
Cohesion: 0.09
Nodes (22): Assess Onboarding Needs, Context Over Ceremony, Contextual Help, Design Onboarding Experiences, Documentation & Help, Empty State Design, Feature Discovery & Adoption, Guided Tours & Walkthroughs (+14 more)

### Community 102 - "impeccable/SKILL.md"
Cohesion: 0.09
Nodes (21): Assess Adaptation Challenge, Implement & Verify, Recommended Actions, Recommended Actions, Craft (deprecated alias), Apply, Live-mode signature params, Set the spatial thesis (+13 more)

### Community 103 - "bolder.md"
Cohesion: 0.33
Nodes (5): Before you finish, Scope is sovereign, The amplification, The skeleton test, Why it reads flat

### Community 104 - "The Toolkit"
Cohesion: 0.10
Nodes (20): Animate complex properties, Assess What "Extraordinary" Means Here, For data-heavy interfaces, For functional UI, For performance-critical UI, For visual/marketing surfaces, Implement with Discipline, Interact with the device (+12 more)

### Community 105 - "Humanizer"
Cohesion: 0.10
Nodes (19): 33 Patterns Detected (with Before/After Examples), Claude Code plugin, Communication Patterns, Content Patterns, Filler and Hedging, Full Example, Humanizer, Installation (+11 more)

### Community 106 - "Requirements"
Cohesion: 0.11
Nodes (17): embedding-infrastructure Specification, Purpose, Requirement: Broker topology, Requirement: Canonical text and source hash, Requirement: Database-level invariants, Requirement: Embedding lifecycle, Requirement: Provider call isolation, Requirement: Provider extension point (+9 more)

### Community 107 - "createLiveBrowserSessionState"
Cohesion: 0.21
Nodes (15): createLiveBrowserSessionState(), clearHandled(), clearScrollY(), clearSession(), isHandled(), loadSession(), markHandled(), nextCheckpointRevision() (+7 more)

### Community 108 - "createLiveBrowserDomHelpers"
Cohesion: 0.16
Nodes (11): createLiveBrowserDomHelpers(), cssId(), liveUiRoot(), makeFrozenAnchor(), own(), pickable(), rectIsUsableAnchor(), uiAppend() (+3 more)

### Community 109 - "animate.md"
Cohesion: 0.12
Nodes (14): Accessibility and control, Choose material by meaning, Find the job, Implement to the runtime, Set the motion thesis, Timing and easing, Verify, Visitor mode (+6 more)

### Community 110 - "live.md"
Cohesion: 0.12
Nodes (15): Cleanup, Exit, First-time setup, Handle `accept`, Handle `discard`, Handle fallback, Handle `manual_edit_apply`, Handle `prefetch` (+7 more)

### Community 111 - "Handle `generate`"
Cohesion: 0.12
Nodes (16): 1. Read the screenshot (if present), 2. Wrap the element, 3. Load the action's reference, 4. Plan three variants: identity first, then mode, then axes, 5. Apply the freeform prompt (if present), 6. Deliver variants, 7. Parameters (composition-sized, 0-4 per variant), 8. Signal done (+8 more)

### Community 112 - "Generate Report"
Cohesion: 0.29
Nodes (7): Audit Health Score, Detailed Findings by Severity, Executive Summary, Generate Report, Implementation Integrity Verdict, Patterns & Systemic Issues, Positive Findings

### Community 113 - "New visual work"
Cohesion: 0.14
Nodes (14): 1. Decide what is already true, 2. Ask what will change the work, 3. Choose the right amount of invention, 4. Commit the world, 5. Record the decision, 6. Build with full commitment, 7. Inspect and finish, Both paths (+6 more)

### Community 114 - "optimize.md"
Cohesion: 0.14
Nodes (13): Animation Performance, Assess Performance Issues, Core Web Vitals Optimization, Cumulative Layout Shift (CLS < 0.1), Interaction to Next Paint (INP < 200ms), Largest Contentful Paint (LCP < 2.5s), Loading Performance, Network Optimization (+5 more)

### Community 115 - "Quality Rules"
Cohesion: 0.14
Nodes (13): Activation Contract, Animation, Content & Accessibility, Dark Mode & Theming, Decision Gates, Design, Execution Steps, Hard Rules (+5 more)

### Community 117 - "Scan mode (approach C: auto-extract, then confirm descriptive language)"
Cohesion: 0.15
Nodes (13): Component translation rules, Narrative mapping, Scan mode (approach C: auto-extract, then confirm descriptive language), Schema, Step 1: Find the design assets, Step 2: Auto-extract what can be auto-extracted, Step 2b: Stage the frontmatter, Step 3: Ask the user for qualitative language (+5 more)

### Community 118 - "FILLER AND HEDGING"
Cohesion: 0.17
Nodes (12): 23. Filler Phrases, 24. Excessive Hedging, 25. Generic Positive Conclusions, 26. Hyphenated Word Pair Overuse, 27. Persuasive Authority Tropes, 28. Signposting and Announcements, 29. Fragmented Headers, 30. Diff-Anchored Writing (+4 more)

### Community 119 - "critique.md"
Cohesion: 0.17
Nodes (11): Action Summary, Ask the User, Assessment A: Design Review, Assessment B: Detector + Browser Evidence, Assessment Orchestration, Deliver the Report, Hard Invariants, Persist the Snapshot (+3 more)

### Community 120 - "Simplify the Design"
Cohesion: 0.17
Nodes (11): Assess Current State, Code Simplification, Content Simplification, Document Removed Complexity, Information Architecture, Interaction Simplification, Layout Simplification, Plan Simplification (+3 more)

### Community 121 - "Hardening Dimensions"
Cohesion: 0.17
Nodes (11): Accessibility Resilience, Assess Hardening Needs, Edge Cases & Boundary Conditions, Error Handling, Hardening Dimensions, Input Validation & Sanitization, Internationalization (i18n), Performance Resilience (+3 more)

### Community 122 - "Humanizer: Remove AI Writing Patterns"
Cohesion: 0.18
Nodes (10): DETECTION GUIDANCE, Full Example, How to provide a sample, Humanizer: Remove AI Writing Patterns, Process and Output, Reference, Signs of human writing (preserve these), Voice Calibration (Optional) (+2 more)

### Community 123 - "clarify.md"
Cohesion: 0.18
Nodes (10): Actions and navigation, Audit the language, Errors and permissions, Forms, Help and instructional text, Loading, empty, and success states, Rewrite by function, Set the message hierarchy (+2 more)

### Community 124 - "Nielsen's 10 Heuristics"
Cohesion: 0.18
Nodes (11): 10. Help and Documentation, 1. Visibility of System Status, 2. Match Between System and Real World, 3. User Control and Freedom, 4. Consistency and Standards, 5. Error Prevention, 6. Recognition Rather Than Recall, 7. Flexibility and Efficiency of Use (+3 more)

### Community 125 - "Generate Combined Critique Report"
Cohesion: 0.18
Nodes (11): Design Health Score, Design Specificity Verdict, Generate Combined Critique Report, Minor Observations, Overall Impression, Persona Red Flags, Priority Issues, Questions to Consider (+3 more)

### Community 126 - "document.md"
Cohesion: 0.18
Nodes (10): Pitfalls, Seed mode, Step 1: Route through new-work's workshop, Step 2: Write seed DESIGN.md, Step 3: Confirm, Style guidelines, The frontmatter: token schema, The markdown body: eight sections (canonical order) (+2 more)

### Community 127 - "polish.md"
Cohesion: 0.18
Nodes (10): 1. Establish the system, 2. Gather the evidence, 3. Triage, 4. Polish the whole path, 5. Verify and finish, Color, imagery, and icons, Content and code, Flow and hierarchy (+2 more)

### Community 128 - "quieter.md"
Cohesion: 0.18
Nodes (10): Assess Current State, Color Refinement, Composition Refinement, Motion Reduction, Plan Refinement, Refine the Design, Simplification, Verify Quality (+2 more)

### Community 129 - "Init flow"
Cohesion: 0.20
Nodes (10): Completion gate, Init flow, Step 1: Load current state, Step 2: Explore the project, Step 3: Interview for product truth, Step 4: Write PRODUCT.md, Step 5: Record workflow defaults, Step 6: Wrap up or resume (+2 more)

### Community 130 - "Common Cognitive Load Violations"
Cohesion: 0.22
Nodes (9): 1. The Wall of Options, 2. The Memory Bridge, 3. The Hidden Navigation, 4. The Jargon Barrier, 5. The Visual Noise Floor, 6. The Inconsistent Pattern, 7. The Multi-Task Demand, 8. The Context Switch (+1 more)

### Community 131 - "iOS platform"
Cohesion: 0.22
Nodes (9): Color & materials, Components & controls, iOS platform, Layout & structure, Motion, The iOS slop test, Touch targets, Typography (+1 more)

### Community 132 - "Operate mode depth (and Read notes)"
Cohesion: 0.10
Nodes (18): Craft floor, Refuse, Verify, Constraints, Failure modes, Flow, $impeccable hooks, Routing (+10 more)

### Community 133 - "Shape"
Cohesion: 0.25
Nodes (8): Cadence, Confirm and stop, Phase 1: Discovery interview, Phase 2: Resolve the design direction, Phase 3: Write the brief, Round 1: purpose, people, and outcome, Round 2: material, behavior, and boundaries, Shape

### Community 134 - "LANGUAGE AND GRAMMAR PATTERNS"
Cohesion: 0.25
Nodes (8): 10. Rule of Three Overuse, 11. Elegant Variation (Synonym Cycling), 12. False Ranges, 13. Passive Voice and Subjectless Fragments, 7. Overused "AI Vocabulary" Words, 8. Avoidance of "is"/"are" (Copula Avoidance), 9. Negative Parallelisms and Tailing Negations, LANGUAGE AND GRAMMAR PATTERNS

### Community 135 - "Adaptation Strategies"
Cohesion: 0.40
Nodes (5): Adaptation Strategies, Orientation & foldables, Phone → Tablet (iPad / large screens), Platform → platform (iOS ↔ Android), Web → native (porting a website or web app)

### Community 136 - "Android platform"
Cohesion: 0.25
Nodes (8): Android platform, Color & theming, Components & motion, Layout & structure, The Android slop test, Touch targets, Typography, Verifying the build

### Community 137 - "colorize.md"
Cohesion: 0.25
Nodes (7): Apply at system scale, Audit before choosing, Choose a strategy, Contrast and perception, Live-mode signature params, Verify, Visitor mode

### Community 138 - "Persona-Based Design Testing"
Cohesion: 0.25
Nodes (8): 1. Impatient Power User: "Alex", 2. Confused First-Timer: "Jordan", 3. Accessibility-Dependent User: "Sam", 4. Deliberate Stress Tester: "Riley", 5. Distracted Mobile User: "Casey", Persona-Based Design Testing, Project-Specific Personas, Selecting Personas

### Community 140 - "Extract Flow"
Cohesion: 0.25
Nodes (7): Extract Flow, Step 1: Discover the Design System, Step 2: Identify Patterns, Step 3: Plan Extraction, Step 4: Extract & Enrich, Step 5: Migrate, Step 6: Document

### Community 141 - "resolveLiveInjectionAnchor"
Cohesion: 0.16
Nodes (19): buildSvelteExpressionTextMap(), buildSveltePropValuesFromLiveElement(), buildSveltePropValuesV2(), cloneWithoutElements(), collectTextNodes(), collectVisibleTexts(), cssEscapeIdent(), elementMatchesOriginalMarkup() (+11 more)

### Community 142 - "STYLE PATTERNS"
Cohesion: 0.29
Nodes (7): 14. Em Dashes (and En Dashes): Cut Them, 15. Overuse of Boldface, 16. Inline-Header Vertical Lists, 17. Title Case in Headings, 18. Emojis, 19. Curly Quotation Marks, STYLE PATTERNS

### Community 143 - "CONTENT PATTERNS"
Cohesion: 0.29
Nodes (7): 1. Undue Emphasis on Significance, Legacy, and Broader Trends, 2. Undue Emphasis on Notability and Media Coverage, 3. Superficial Analyses with -ing Endings, 4. Promotional and Advertisement-like Language, 5. Vague Attributions and Weasel Words, 6. Outline-like "Challenges and Future Prospects" Sections, CONTENT PATTERNS

### Community 144 - "Generate Report"
Cohesion: 0.29
Nodes (7): Audit Health Score, Detailed Findings by Severity, Executive Summary, Generate Report, Patterns & Systemic Issues, Platform Conformance Verdict, Positive Findings

### Community 145 - "Cognitive Load Assessment"
Cohesion: 0.29
Nodes (7): Cognitive Load Assessment, Cognitive Load Checklist, Extraneous Load: Bad Design, Germane Load: Learning Effort, Intrinsic Load: The Task Itself, The Working Memory Rule, Three Types of Cognitive Load

### Community 146 - "Impeccable Asset Producer"
Cohesion: 0.29
Nodes (6): Core Rule, Decision Comps, Impeccable Asset Producer, Input Contract, Output Contract, The job

### Community 147 - "Impeccable Finish Reviewer"
Cohesion: 0.29
Nodes (6): Checks, in order, Disposition, Impeccable Finish Reviewer, Input Contract, Output Contract, Verdict Pass

### Community 148 - "Impeccable Manual Edit Applier"
Cohesion: 0.29
Nodes (6): Checks, Entry Atomicity, Impeccable Manual Edit Applier, Input Contract, Output Contract, Workflow

### Community 149 - "live-browser-ignores.js"
Cohesion: 0.52
Nodes (6): globToRegex(), matchesScope(), normalizeIgnoreRule(), normalizeIgnoreValue(), pageCandidates(), resolveDetectIgnores()

### Community 150 - "vercel-quality"
Cohesion: 0.29
Nodes (6): Cuándo usarla, Dónde encaja, Flujo, Instalación, Qué hace, vercel-quality

### Community 151 - "LoginDualTests"
Cohesion: 0.10
Nodes (11): LoginDualTests, Tests de integración para ambos mecanismos de autenticación. Verifica que tanto…, Login con correo electrónico y contraseña debe funcionar., Login con nombre de usuario y contraseña debe funcionar., El login por correo debe ser insensible a mayúsculas., El login por nombre de usuario debe ser insensible a mayúsculas., Login con correo incorrecto debe fallar., Login con nombre de usuario incorrecto debe fallar. (+3 more)

### Community 152 - "Diagnostic Scan"
Cohesion: 0.33
Nodes (6): 1. Accessibility (VoiceOver / TalkBack), 2. Performance, 3. Appearance & Theming, 4. Platform Conformance (CRITICAL), 5. Adaptivity, Diagnostic Scan

### Community 153 - "seed.py"
Cohesion: 0.20
Nodes (13): ChatFactory, MensajeFactory, Meta, Factories de factory_boy para la app `chatbot`. Se usan únicamente para sembrar…, Chat, Mensaje, Meta, Modelos de la app `chatbot`. Implementa la conversación del chatbot (doc 03):… (+5 more)

### Community 154 - "Visualize: Direction Comps & Asset Production"
Cohesion: 0.33
Nodes (5): After approval: the comp becomes a spec, Generate three compositional options, One approval point, Plates and provenance, Visualize: Direction Comps & Asset Production

### Community 155 - "impeccable"
Cohesion: 0.60
Nodes (5): impeccable script, check_download(), fetch_url(), probe_ok(), setup_help()

### Community 157 - "ProduccionAudiovisual"
Cohesion: 0.10
Nodes (24): CalificacionFactory, Meta, ProduccionAudiovisualFactory, Factories de factory_boy para la app `catalogo`. Se usan únicamente para…, Crea una producción audiovisual simulando un registro de TMDB. Los campos de…, ResenaFactory, Calificacion, Meta (+16 more)

### Community 158 - "PERSONALITY AND SOUL"
Cohesion: 0.40
Nodes (5): After (has a pulse):, Before (clean but soulless):, How to add voice:, PERSONALITY AND SOUL, Signs of soulless writing (even if technically "clean"):

### Community 159 - "Impeccable Documenter"
Cohesion: 0.40
Nodes (4): Impeccable Documenter, Input Contract, Output Contract, Workflow

### Community 160 - "COMMUNICATION PATTERNS"
Cohesion: 0.50
Nodes (4): 20. Collaborative Communication Artifacts, 21. Knowledge-Cutoff Disclaimers and Speculative Gap-Filling, 22. Sycophantic/Servile Tone, COMMUNICATION PATTERNS

### Community 161 - "Heuristics Scoring Guide"
Cohesion: 0.50
Nodes (4): Heuristics Scoring Guide, Issue Severity (P0–P3), Reference Material, Score Summary

### Community 162 - "onAnnotDown"
Cohesion: 0.16
Nodes (20): beginEditPin(), buildAnnotationsForCapture(), buildPinElement(), cancelEditingPin(), clampPlaceholderSize(), finalizeEditingPin(), initAnnotOverlay(), localCoords() (+12 more)

### Community 163 - "patch"
Cohesion: 0.08
Nodes (13): generar_embedding(), Genera el vector semántico de una producción ya materializada. Nunca lanza: si…, GenerarEmbeddingTaskTests, MaterializacionCarreraTests, ParamValidationTest, patch, Doble del `TMDBClientCache`: enriquecimiento (C-04a) y listados (C-04b)., Dos requests simultáneos sobre la misma producción (C-04a). La constraint… (+5 more)

### Community 164 - "Design: Daily Catalog Sync + Embedding Backfill (C-04b)"
Cohesion: 0.13
Nodes (14): Architecture Decisions, Backfill Task, Data Model Change, Design: Daily Catalog Sync + Embedding Backfill (C-04b), Docker Compose, Freshness: three layers, one question each, Materialization Changes, Migration / Rollout (+6 more)

### Community 165 - "Proposal: Daily Catalog Sync + Embedding Backfill (C-04b, CU-021)"
Cohesion: 0.13
Nodes (14): Affected Areas, Approach, Capabilities, Dependencies, In Scope, Intent, Modified Capabilities, New Capabilities (+6 more)

### Community 166 - "Reglas"
Cohesion: 0.14
Nodes (13): 1. No dar por sabido ningún concepto de framework, 2. Diagrama cuando se toque arquitectura o comunicación entre componentes, 3. Explicar cada test al escribirlo, 4. Breve, pero sin perder claridad, 5. Avanzar en unidades chicas, 6. Explicar un archivo antes de tocarlo si está abierto, 7. Ofrecer opciones solo cuando son reales, 8. Verificar antes de afirmar (+5 more)

### Community 167 - "ProduccionEmbedding"
Cohesion: 0.08
Nodes (17): ProduccionEmbeddingAdmin, register, Configuración del admin de Django para el catálogo. Por ahora solo se registra…, ProduccionEmbedding, Representación semántica de una producción para búsqueda por similitud. Se crea…, _encolar_embedding(), Crea el embedding en `pending` y encola la tarea, una sola vez. `get_or_create`…, MaterializacionBase (+9 more)

### Community 168 - "Requirements"
Cohesion: 0.25
Nodes (7): Errors and ownership, Items, List endpoints, List management, Purpose, Requirements, Summary and membership

### Community 169 - "LoginSerializer"
Cohesion: 0.29
Nodes (4): LoginSerializer, Login por credenciales con errores específicos para cuentas inactivas., La activación por ``estado`` reemplaza el chequeo de allauth., BaseLoginSerializer

### Community 171 - "Tasks: Daily Catalog Sync + Embedding Backfill (C-04b)"
Cohesion: 0.29
Nodes (6): Phase 1: Changes to existing C-04a code, Phase 2: Scheduler and daily sync, Phase 3: Backfill, documentation and verification, Review Workload Forecast, Suggested Work Units, Tasks: Daily Catalog Sync + Embedding Backfill (C-04b)

### Community 172 - "Conventional Commits"
Cohesion: 0.25
Nodes (7): Activation Contract, Conventional Commits, Decision Gates, Execution Steps, Hard Rules, Output Contract, References

### Community 173 - "listas/serializers.py"
Cohesion: 0.23
Nodes (9): AgregarItemSerializer, ListaItemSerializer, PertenenciaQuerySerializer, Serializers de entrada y salida para la API de listas., Valida la producción cuya pertenencia a listas se quiere consultar., Payload de alta de un ítem, en el vocabulario público de TMDB., _lista_propia(), ListaItemsView (+1 more)

### Community 174 - "Tiene"
Cohesion: 0.22
Nodes (8): Meta, Tabla intermedia N:N entre `Lista` y `ProduccionAudiovisual`. Registra el…, Tiene, _agregar_previews(), _listas_del_usuario(), Lista resúmenes con contadores, preview y pertenencia opcional., Adjunta hasta el máximo configurado de pósters recientes por lista., _resumen_response()

### Community 176 - "Lista"
Cohesion: 0.28
Nodes (6): Factories de factory_boy para la app `listas`. Se usan únicamente para sembrar…, Lista, Modelos de la app `listas`. Implementa las listas de contenidos del usuario y…, Tipo de lista (doc 03: 'Predeterminada' | 'Personalizada')., Lista de producciones de un usuario. Cada usuario tiene por defecto las listas…, TipoLista

### Community 177 - "OpenSpec Config"
Cohesion: 1.00
Nodes (3): OpenSpec Config, Spec-Driven Development Workflow, Strict TDD

### Community 182 - "doctor.md"
Cohesion: 0.25
Nodes (7): Monorepo notes, Opting out of the boot check, Step 1: Run the pass, Step 2: Act by severity, Step 3: Deprecated fields are binding, Step 4: Do not overclaim on truth drift, What this owns, and what it does not

### Community 183 - "live-setup.md"
Cohesion: 0.25
Nodes (7): append-arrays, append-string, Config drift, Consent prompt (use this phrasing), CSP detection (first-time only), Troubleshooting, Write the config

### Community 184 - "_ids_cambiados"
Cohesion: 0.39
Nodes (4): _ids_cambiados(), IDs que TMDB reporta como modificados en las últimas 24 h., IdsCambiadosTests, El paginador de la lista de cambios de TMDB (C-04b, fase 2). `_ids_cambiados`…

### Community 185 - "Diagnostic Scan"
Cohesion: 0.33
Nodes (6): 1. Accessibility (A11y), 2. Performance, 3. Theming, 4. Responsive Design, 5. Implementation Integrity (CRITICAL), Diagnostic Scan

### Community 186 - "GoogleSocialLoginSerializer"
Cohesion: 0.33
Nodes (3): GoogleSocialLoginSerializer, Login y registro con Google mediante ``id_token``., BaseSocialLoginSerializer

### Community 187 - "ListaItemCursorPagination"
Cohesion: 0.40
Nodes (4): ListaItemCursorPagination, Paginación de los ítems de una lista., Cursor estable para el scroll infinito del detalle de lista., CursorPagination

### Community 188 - "Command guidance"
Cohesion: 0.50
Nodes (3): Command guidance, No-argument routing: the context-aware menu, Workflow questions

## Ambiguous Edges - Review These
- `FilmAI Landing Marketing / Hero Visual` → `Poster Title Text (Unverified Visual Content)`  [AMBIGUOUS]
  frontend/public/collage-posters/Opcion 1.jpg · relation: conceptually_related_to
- `Poster Title Text (Unverified Visual Content)` → `Opcion 1 Collage Poster Image`  [AMBIGUOUS]
  frontend/public/collage-posters/Opcion 1.jpg · relation: conceptually_related_to
- `FilmAI Hero/Marketing Asset` → `Collage Poster Option 3`  [AMBIGUOUS]
  frontend/public/collage-posters/Opcion 3.jpg · relation: conceptually_related_to

## Knowledge Gaps
- **722 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+717 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1158 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `FilmAI Landing Marketing / Hero Visual` and `Poster Title Text (Unverified Visual Content)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Poster Title Text (Unverified Visual Content)` and `Opcion 1 Collage Poster Image`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `FilmAI Hero/Marketing Asset` and `Collage Poster Option 3`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `UsuarioFactory` connect `UsuarioFactory` to `UsuarioPerfilSerializer`, `ListasEndpointsTests`, `usuarios/tests.py`, `._serializer_google`, `Command`, `Lista`, `LoginDualTests`, `seed.py`, `ProduccionAudiovisual`, `Usuario`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `Usuario` connect `Usuario` to `provisionar_recursos_por_defecto`, `usuarios/views.py`, `UsuarioPerfilSerializer`, `UsuarioFactory`, `usuarios/tests.py`, `LoginSerializer`, `Command`, `seed.py`, `GoogleSocialLoginSerializer`, `ConfirmarCorreoTests`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `TipoProduccion` connect `ProduccionAudiovisual` to `patch`, `ProduccionEmbedding`, `ListasEndpointsTests`, `Tiene`, `listas/views.py`, `Command`, `sync_catalogo_diaria`, `materializar`, `seed.py`, `catalogo/tests.py`, `backfill_embeddings`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `UsuarioFactory` (e.g. with `CalificacionFactory` and `ChatFactory`) actually correct?**
  _`UsuarioFactory` has 16 INFERRED edges - model-reasoned connections that need verification._