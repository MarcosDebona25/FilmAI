# Graph Report - FilmAI  (2026-09-10)

## Corpus Check
- 178 files · ~614,522 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2085 nodes · 4198 edges · 162 communities (116 shown, 26 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 208 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `422690bc`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TMDBClient
- Modelos de Datos y de Diseño (doc 03)
- usuarios/views.py
- FilmAI
- ResendBackend
- TMDBClientCache
- usuarios/models.py
- UsuarioFactory
- seed.py
- components.json
- GoogleOAuthTests
- package.json
- Lista
- register/page.tsx
- Command
- compilerOptions
- Usuario
- Navbar.tsx
- chatbot/factories.py
- completar-google/page.tsx
- login/page.tsx
- apiFetch
- google-auth.ts
- devDependencies
- dependencies
- UsuarioAccountAdapter
- button.tsx
- live-browser.js
- scripts
- ConfirmarCorreoTests
- RegisterPage
- eslint.config.mjs
- FilmAI Collage Poster Design — Option 2
- Command
- UsuarioManager
- Humanizer Skill
- resumeSession
- nombre_completo
- modern-screenshot.umd.js
- Conventional Commit Decision Gates
- vercel-quality Skill README
- manage.py
- signals.py
- initPageChat
- Collage Poster Option 3
- middleware.ts
- AI Review Job (Nikita-Filonov/ai-review)
- CatalogoConfig
- ChatbotConfig
- ListasConfig
- Migration
- next
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
- Gemini Generated Avatar Image
- File Icon (file.svg)
- Globe Icon (globe.svg)
- Movies Icon (icons8-movies-32.png)
- Window Icon (window.svg)
- setLiveState
- el
- captureElementToBlob
- renderDesignVisual
- showToast
- cleanup
- applyEditing
- initGlobalBar
- mountSvelteComponentVariant
- Responsive Design
- handleManualEditActivity
- onboard.md
- new-work.md
- impeccable/SKILL.md
- The Toolkit
- Humanizer
- resolveLiveInjectionAnchor
- createLiveBrowserSessionState
- createLiveBrowserDomHelpers
- animate.md
- live.md
- Handle `generate`
- Generate Report
- New visual work
- optimize.md
- Quality Rules
- serializers.py
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
- adapt.native.md
- Android platform
- colorize.md
- Persona-Based Design Testing
- doctor.md
- Extract Flow
- live-setup.md
- STYLE PATTERNS
- CONTENT PATTERNS
- Generate Report
- Cognitive Load Assessment
- Impeccable Asset Producer
- Impeccable Finish Reviewer
- Impeccable Manual Edit Applier
- live-browser-ignores.js
- vercel-quality
- RegisterSerializer
- Diagnostic Scan
- $impeccable hooks
- Visualize: Direction Comps & Asset Production
- impeccable
- LoginSerializer
- ComplejidadContrasenaValidator
- PERSONALITY AND SOUL
- Impeccable Documenter
- COMMUNICATION PATTERNS
- Heuristics Scoring Guide

## God Nodes (most connected - your core abstractions)
1. `setLiveState()` - 32 edges
2. `resumeSession()` - 32 edges
3. `connectSSE()` - 31 edges
4. `showToast()` - 30 edges
5. `el()` - 29 edges
6. `initGlobalBar()` - 29 edges
7. `TMDBClient` - 28 edges
8. `Command` - 28 edges
9. `Usuario` - 28 edges
10. `handleKeyDown()` - 27 edges

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
- **Cache-Aside Implementation Mechanisms** — tmdb_client_cache, cache_aside_pattern, per_endpoint_ttl, stable_cache_key, json_round_trip [EXTRACTED 1.00]
- **Docker Compose Services** — docker_compose_db, docker_compose_redis, docker_compose_backend, docker_compose_frontend, docker_compose_network [EXTRACTED 1.00]
- **FilmAI Tech Stack** — readme_django, readme_django_rest_framework, readme_postgresql, readme_redis, readme_celery, readme_nextjs, readme_tailwind, readme_shadcn [EXTRACTED 1.00]
- **SDD Change Artifact Chain** — openspec_changes_archive_2026_09_03_catalog_tmdb_cache_proposal, openspec_changes_archive_2026_09_03_catalog_tmdb_cache_design, openspec_changes_archive_2026_09_03_catalog_tmdb_cache_specs_tmdb_cache_spec, openspec_changes_archive_2026_09_03_catalog_tmdb_cache_tasks, openspec_changes_archive_2026_09_03_catalog_tmdb_cache_verify_report, openspec_changes_archive_2026_09_03_catalog_tmdb_cache_archive_report [EXTRACTED 1.00]
- **Casos de Uso del sistema FilmAI** — docs_02_especificacion_de_requerimientos_cu_001, docs_02_especificacion_de_requerimientos_cu_003, docs_02_especificacion_de_requerimientos_cu_008, docs_02_especificacion_de_requerimientos_cu_013, docs_02_especificacion_de_requerimientos_cu_015, docs_02_especificacion_de_requerimientos_cu_021 [EXTRACTED 1.00]
- **Catálogo híbrido y corpus semántico** — docs_decisiones_arquitectura_hibrida, docs_03_modelos_de_datos_y_de_diseno_catalogo_materializado, docs_03_modelos_de_datos_y_de_diseno_produccion_embedding, docs_03_modelos_de_datos_y_de_diseno_busqueda_semantica, docs_03_modelos_de_datos_y_de_diseno_sincronizacion_celery [INFERRED 0.85]
- **Opencode Skills Collection** — _opencode_skills_conventional_commits_skill_doc, _opencode_skills_humanizer_skill_doc, _opencode_skills_vercel_quality_skill_doc [INFERRED 0.85]
- **Redis Failure and Error Boundaries** — graceful_degradation, redis_error_boundary, tmdb_client, tmdb_error_hierarchy [INFERRED 0.85]
- **Stack de autenticación y modelo de usuario** — docs_03_modelos_de_datos_y_de_diseno_modelo_usuario, docs_decisiones_usuario_unificado, docs_decisiones_autenticacion_allauth, docs_decisiones_cookies_http_only_csrf, docs_decisiones_estado_ciclo_vida [INFERRED 0.85]

## Communities (162 total, 26 thin omitted)

### Community 0 - "TMDBClient"
Cohesion: 0.06
Nodes (27): _build_key(), get_redis(), TMDBClientCache, TMDBClient, Exception, TMDB rejected the request because its rate limit was exceeded., TMDB could not find the requested resource., TMDB rejected the request as invalid. (+19 more)

### Community 1 - "Modelos de Datos y de Diseño (doc 03)"
Cohesion: 0.09
Nodes (57): Chatbot basado en LLM para recomendaciones personalizadas, Presentación de la Idea-Proyecto (doc 01), FilmAI — Plataforma Web de Reseñas Cinematográficas con Recomendaciones Inteligentes, CU-001: Crear cuenta de usuario, CU-003: Iniciar sesión, CU-008: Visualizar Catálogo, CU-013: Interactuar con el chatbot, CU-015: Gestionar Reseña y Calificación (ABM) (+49 more)

### Community 2 - "usuarios/views.py"
Cohesion: 0.07
Nodes (28): APIView, URL configuration for filmai project. Rutas de autenticación (docs/05 —…, Solicitud de restablecimiento de contraseña (CU-020). Envía un email con un…, Confirmación del restablecimiento con nueva contraseña (CU-020). Valida el par…, RecuperarContrasenaSerializer, RestablecerContrasenaSerializer, ConfirmarCorreoView, CSRFTokenView (+20 more)

### Community 3 - "FilmAI"
Cohesion: 0.07
Nodes (52): Backend CI Job (Ruff), CI GitHub Workflow, ESLint, Frontend CI Job (ESLint + Prettier), .husky/pre-commit Hook, Prettier, Ruff, docs/decisiones.md Decision Log (+44 more)

### Community 4 - "ResendBackend"
Cohesion: 0.11
Nodes (15): Backend de email de Django sobre la API HTTP de Resend. Motivación y diseño…, Devuelve la parte HTML si el mensaje es multipart/alternative., Envía `EmailMessage` vía `resend.Emails.send` (API REST de Resend). - Requiere…, ResendBackend, Validación de la configuración de email al arranque. En producción la ausencia…, Levanta ``ImproperlyConfigured`` si la config de email es inválida. Solo aplica…, validar_configuracion_email(), Django settings for filmai project. Generated by 'django-admin startproject'… (+7 more)

### Community 5 - "TMDBClientCache"
Cohesion: 0.20
Nodes (33): Cache-Aside Pattern, Composition Over Inheritance, fakeredis Test Backend, get_redis() Factory, Graceful Degradation on Redis Failure, httpx.MockTransport Testing, JSON Serialization Round-Trip, Apply Progress: TMDB Redis Cache (C-02) (+25 more)

### Community 6 - "usuarios/models.py"
Cohesion: 0.14
Nodes (15): Adaptadores de allauth para el modelo de usuario personalizado de FilmAI.…, Adaptador social (Google OAuth) para `usuarios.Usuario`., Construye el `Usuario` a partir del perfil de Google. Se llama únicamente en el…, UsuarioSocialAccountAdapter, Factories de factory_boy para la app `usuarios`. Se usan únicamente para…, Migration, EstadoCuenta, Modelos de la app `usuarios`. FilmAI usa un único modelo de usuario (`Usuario`)… (+7 more)

### Community 7 - "UsuarioFactory"
Cohesion: 0.11
Nodes (10): Meta, Crea un `Usuario` con estado Activa y una contraseña por defecto. La contraseña…, UsuarioFactory, CsrfCookieTests, Recuperación de contraseña (CU-020 / A-07). Cubre: envío del email con enlace…, Sin nombre ni apellido, el saludo es "Hola usuario"., Protección CSRF del access token en cookie httpOnly (JWT_AUTH_COOKIE_USE_CSRF).…, RecuperarContrasenaTests (+2 more)

### Community 8 - "seed.py"
Cohesion: 0.16
Nodes (17): CalificacionFactory, Meta, ProduccionAudiovisualFactory, Factories de factory_boy para la app `catalogo`. Se usan únicamente para…, Crea una producción audiovisual simulando un registro de TMDB. Los campos de…, ResenaFactory, Calificacion, Meta (+9 more)

### Community 9 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 10 - "GoogleOAuthTests"
Cohesion: 0.29
Nodes (7): GoogleOAuthTests, Regresión del 500 en `/api/auth/google/` (RawPostDataException) y del flujo…, Construye el serializer con el request en el estado post-parseo de DRF. Deja…, Fija `SocialAccount.objects.filter(...).exists()` al valor deseado., Regresión: una cuenta de Google ya vinculada inicia sesión SIN los campos extra…, Una cuenta de Google NUEVA (sin SocialAccount) exige los campos que Google no…, Regresión: el chequeo de email duplicado case-insensitive corre ANTES de…

### Community 11 - "package.json"
Cohesion: 0.10
Nodes (19): name, private, version, @base-ui/react, clsx, eslint, eslint-config-next, husky (+11 more)

### Community 12 - "Lista"
Cohesion: 0.18
Nodes (11): ListaFactory, Meta, Factories de factory_boy para la app `listas`. Se usan únicamente para sembrar…, Lista, Meta, Modelos de la app `listas`. Implementa las listas de contenidos del usuario y…, Tipo de lista (doc 03: 'Predeterminada' | 'Personalizada')., Lista de producciones de un usuario. Cada usuario tiene por defecto las listas… (+3 more)

### Community 13 - "register/page.tsx"
Cohesion: 0.18
Nodes (14): Campo, Errores, GENEROS, VALIDADORES, decodificarParametro(), EnlaceInvalido, Estado, RestablecerContrasenaPage() (+6 more)

### Community 14 - "Command"
Cohesion: 0.15
Nodes (9): atomic, Command, BaseCommand, Crea el catálogo repartido entre películas y series., Cada usuario califica un subconjunto aleatorio del catálogo. Se pasan `usuario`…, Crea las 3 listas predeterminadas y algunas personalizadas por usuario., Usa el chat por defecto (creado por la señal) y agrega mensajes., Borra los datos de las apps de negocio (orden de hijos a padres). El borrado en… (+1 more)

### Community 15 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 16 - "Usuario"
Cohesion: 0.12
Nodes (12): AbstractBaseUser, Admin para el modelo personalizado de usuario. Adapta `UserAdmin` de Django a…, UsuarioAdmin, Meta, Logueable solo si la cuenta está en estado Activa. Se deriva de `estado` para…, Permite que Django/allauth activen la cuenta (`is_active = True`). Solo actúa…, Cliente de la plataforma y, según sus flags, administrador del panel. Concentra…, Usuario (+4 more)

### Community 17 - "Navbar.tsx"
Cohesion: 0.16
Nodes (11): inter, metadata, roboto, iniciales(), NAV_LINKS, Navbar(), logout(), noImplementado() (+3 more)

### Community 18 - "chatbot/factories.py"
Cohesion: 0.19
Nodes (12): ChatFactory, MensajeFactory, Meta, Factories de factory_boy para la app `chatbot`. Se usan únicamente para sembrar…, Chat, Mensaje, Meta, Modelos de la app `chatbot`. Implementa la conversación del chatbot (doc 03):… (+4 more)

### Community 19 - "completar-google/page.tsx"
Cohesion: 0.20
Nodes (12): Campo, CompletarGooglePage(), onBlurCampo(), onGoogle(), validarCampo(), Errores, GENEROS, maxFechaNacimiento() (+4 more)

### Community 20 - "login/page.tsx"
Cohesion: 0.18
Nodes (10): LoginForm(), cerrarModalRecuperar(), onSubmitRecuperar(), GoogleButton(), GoogleButtonProps, GoogleCredentialResponse, Window, validarCorreo() (+2 more)

### Community 21 - "apiFetch"
Cohesion: 0.27
Nodes (9): ConfirmarCorreoPage(), Estado, ApiError, apiFetch(), ApiOptions, apiUrl(), extractError(), getCsrfToken() (+1 more)

### Community 22 - "google-auth.ts"
Cohesion: 0.21
Nodes (11): onGoogle(), GoogleLinkButton(), extraerErroresPorCampo(), CAMPOS_FALTANTES, CompletarGoogleResult, completarRegistroGoogle(), esFaltaDeCamposGoogle(), GoogleLoginResult (+3 more)

### Community 23 - "devDependencies"
Cohesion: 0.15
Nodes (13): devDependencies, eslint, eslint-config-next, eslint-config-prettier, @eslint/eslintrc, husky, prettier, tailwindcss (+5 more)

### Community 24 - "dependencies"
Cohesion: 0.17
Nodes (12): dependencies, @base-ui/react, class-variance-authority, clsx, lucide-react, next, react, react-dom (+4 more)

### Community 25 - "UsuarioAccountAdapter"
Cohesion: 0.22
Nodes (6): Adaptador de cuenta para el registro tradicional (dj-rest-auth)., Persiste los campos propios del modelo `Usuario`. Reemplaza el mapeo por…, Al confirmar el email, la cuenta pasa a estado `activa`. `is_active` es una…, El link de confirmación apunta al frontend (SPA Next.js). El frontend recibe la…, UsuarioAccountAdapter, DefaultAccountAdapter

### Community 26 - "button.tsx"
Cohesion: 0.21
Nodes (11): POSTERS, Button(), buttonVariants, cn(), Collage Posters Set (3 Design Options), Opcion 1 Collage Poster Image, FilmAI Landing Marketing / Hero Visual, Movie Poster Collage (Depicted Content) (+3 more)

### Community 27 - "live-browser.js"
Cohesion: 0.04
Nodes (92): applyPlaceholderDimensions(), applyPlaceholderSizingStyles(), bindEditBadgeProxy(), buildColorModels(), buildPlaceholderResizeHandles(), buildTypographyModels(), checkpointPayload(), clampVariantIndex() (+84 more)

### Community 28 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, format, format:check, lint, prepare, start

### Community 30 - "RegisterPage"
Cohesion: 0.33
Nodes (5): maxFechaNacimiento(), RegisterPage(), onBlurCampo(), onSubmit(), validarCampo()

### Community 31 - "eslint.config.mjs"
Cohesion: 0.29
Nodes (6): compat, __dirname, eslintConfig, __filename, eslint-config-prettier, @eslint/eslintrc

### Community 32 - "FilmAI Collage Poster Design — Option 2"
Cohesion: 0.29
Nodes (7): FilmAI Collage Poster Design — Option 2, Collage Poster Design Option 2 of 3, FilmAI Branding / Hero Identity, Opcion 2 Collage Poster Image, Marketing / Hero Visual Asset, Movie/Series Poster Collage (Visual Content), Collage Poster Design Options Set (1–3)

### Community 33 - "Command"
Cohesion: 0.33
Nodes (3): Command, BaseCommand, Comando de desarrollo: verifica la integración con Resend. Uso: python…

### Community 34 - "UsuarioManager"
Cohesion: 0.47
Nodes (3): Manager que usa `correo` como identificador de autenticación.…, UsuarioManager, BaseUserManager

### Community 35 - "Humanizer Skill"
Cohesion: 0.70
Nodes (5): Humanizer Skill README, 33 AI Writing Patterns, Humanizer Skill, Voice Calibration, Wikipedia: Signs of AI writing

### Community 36 - "resumeSession"
Cohesion: 0.09
Nodes (65): applyParamDefaults(), applyParamValue(), applySavedSessionMeta(), buildParamsPanel(), clearSession(), closedClipPath(), commitAcceptedVariantToDom(), completeParameterGenerationIfReady() (+57 more)

### Community 37 - "nombre_completo"
Cohesion: 0.40
Nodes (4): nombre_completo(), Filtros de template para saludos en emails transaccionales., Devuelve "Nombre Apellido"; "usuario" si ambos están vacíos. Regla global para…, filter

### Community 38 - "modern-screenshot.umd.js"
Cohesion: 0.09
Nodes (55): ae(), be(), bt(), Ce(), s(), Ct(), de(), dt() (+47 more)

### Community 39 - "Conventional Commit Decision Gates"
Cohesion: 0.83
Nodes (4): Commit Type Examples, Conventional Commit Decision Gates, Conventional Commits Skill, No AI Attribution Rule

### Community 40 - "vercel-quality Skill README"
Cohesion: 0.83
Nodes (4): vercel-quality Skill README, emil-design-eng Skill, vercel-quality Skill, MUST/SHOULD/NEVER Quality Rules

### Community 41 - "manage.py"
Cohesion: 0.50
Nodes (3): main(), Django's command-line utility for administrative tasks., Run administrative tasks.

### Community 42 - "signals.py"
Cohesion: 0.22
Nodes (6): AppConfig, UsuariosConfig, crear_recursos_por_defecto(), Señales de la app `usuarios`. Al crear un `Usuario` (por cualquier vía:…, Crea listas predeterminadas y chat por defecto para usuarios nuevos., receiver

### Community 43 - "initPageChat"
Cohesion: 0.07
Nodes (56): agentHasWorkInFlight(), applyGlobalBarLabelState(), armPageChatForTyping(), attachSteerFocusDebug(), attachSteerFocusGuard(), buildSteerProcessingDots(), buildSteerQueueHint(), clearSteerAwaitTimer() (+48 more)

### Community 44 - "Collage Poster Option 3"
Cohesion: 0.50
Nodes (4): FilmAI Collage Poster Design, FilmAI Hero/Marketing Asset, FilmAI Project, Collage Poster Option 3

### Community 46 - "AI Review Job (Nikita-Filonov/ai-review)"
Cohesion: 0.67
Nodes (3): AI Review GitHub Workflow, AI Review Job (Nikita-Filonov/ai-review), OpenRouter LLM Provider

### Community 90 - "setLiveState"
Cohesion: 0.15
Nodes (40): beginNewLiveConfiguration(), cancelEditing(), cancelEditingToPicking(), cancelInsertConfigure(), cleanupAcceptedSession(), clearAnnotations(), clearInsertPicking(), closeTunePopover() (+32 more)

### Community 91 - "el"
Cohesion: 0.11
Nodes (37): actionLabel(), bindConfigureCountPillTooltip(), bindConfigureInlineControlHover(), bindConfigureModifierPillHover(), buildConfigureActionControl(), buildConfigureCountControl(), buildConfigureRow(), buildConfigureSubmitButton() (+29 more)

### Community 92 - "captureElementToBlob"
Cohesion: 0.08
Nodes (37): averageRgb01(), beginEditPin(), bufferToBase64(), buildAnnotationsForCapture(), buildPinElement(), cancelEditingPin(), captureChromeNodes(), captureElementFromRenderedAncestor() (+29 more)

### Community 93 - "renderDesignVisual"
Cohesion: 0.09
Nodes (34): buildCollapsible(), buildDesignHeader(), buildListHtml(), buildRadiiModels(), copyToClipboard(), cssSafe(), designEmptyMessage(), escapeHtml() (+26 more)

### Community 94 - "showToast"
Cohesion: 0.11
Nodes (29): abandonForeignSession(), applyConfigureBarChrome(), buildCyclingRow(), buildDots(), buildGeneratingRow(), cycleVariant(), cyclingCounterText(), cyclingShownVariant() (+21 more)

### Community 95 - "cleanup"
Cohesion: 0.11
Nodes (30): abortSvelteComponentInjection(), buildInsertPlaceholderSnapshotFromDom(), buildPickedAnchorSnapshot(), captureAndEmit(), cleanup(), clearHandled(), clearMountErrorCard(), clearScrollY() (+22 more)

### Community 96 - "applyEditing"
Cohesion: 0.09
Nodes (30): addManualContextText(), applyEditing(), buildLocatorForLeaf(), canRestoreManualEditElement(), collectManualContextPieces(), walk(), contextElementForManualEdit(), copyEditContainerContext() (+22 more)

### Community 97 - "initGlobalBar"
Cohesion: 0.11
Nodes (28): agentStatusText(), barPaletteForTheme(), brandMarkSvg(), buildSavingRow(), designPanelCss(), detectPageTheme(), ensureAgentPollTooltip(), ensureSpinKeyframes() (+20 more)

### Community 98 - "mountSvelteComponentVariant"
Cohesion: 0.12
Nodes (27): acceptedDomAlreadyClean(), applyOriginalAttrsToSvelteAnchor(), clearHandledWrapperReloadStamp(), commitAcceptedSvelteComponentToDom(), componentModuleCandidates(), deferredRecoverySuperseded(), describeMountFailure(), detectDevServerBase() (+19 more)

### Community 99 - "Responsive Design"
Cohesion: 0.08
Nodes (25): Assess Adaptation Challenge, Breakpoints: Content-Driven, Content Adaptation, Desktop Adaptation (Mobile → Desktop), Detect Input Method, Not Just Screen Size, Email Adaptation (Web → Email), Implement Adaptations, Layout Adaptation Patterns (+17 more)

### Community 100 - "handleManualEditActivity"
Cohesion: 0.19
Nodes (24): clearStoredManualApplyState(), fetchPendingCount(), handleManualEditActivity(), hidePendingApplyDock(), manualApplyLoadingText(), manualApplyStateKey(), manualEditEventForCurrentPage(), numberOrNull() (+16 more)

### Community 101 - "onboard.md"
Cohesion: 0.09
Nodes (22): Assess Onboarding Needs, Context Over Ceremony, Contextual Help, Design Onboarding Experiences, Documentation & Help, Empty State Design, Feature Discovery & Adoption, Guided Tours & Walkthroughs (+14 more)

### Community 102 - "new-work.md"
Cohesion: 0.13
Nodes (14): Recommended Actions, Craft (deprecated alias), Apply, Live-mode signature params, Set the spatial thesis, Two isolated assessments, Verify, Visitor mode (+6 more)

### Community 103 - "impeccable/SKILL.md"
Cohesion: 0.10
Nodes (15): Before you finish, Scope is sovereign, The amplification, The skeleton test, Why it reads flat, Craft floor, Refuse, Verify (+7 more)

### Community 104 - "The Toolkit"
Cohesion: 0.10
Nodes (20): Animate complex properties, Assess What "Extraordinary" Means Here, For data-heavy interfaces, For functional UI, For performance-critical UI, For visual/marketing surfaces, Implement with Discipline, Interact with the device (+12 more)

### Community 105 - "Humanizer"
Cohesion: 0.10
Nodes (19): 33 Patterns Detected (with Before/After Examples), Claude Code plugin, Communication Patterns, Content Patterns, Filler and Hedging, Full Example, Humanizer, Installation (+11 more)

### Community 106 - "resolveLiveInjectionAnchor"
Cohesion: 0.16
Nodes (19): buildSvelteExpressionTextMap(), buildSveltePropValuesFromLiveElement(), buildSveltePropValuesV2(), cloneWithoutElements(), collectTextNodes(), collectVisibleTexts(), cssEscapeIdent(), elementMatchesOriginalMarkup() (+11 more)

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
Cohesion: 0.13
Nodes (14): 1. Accessibility (A11y), 2. Performance, 3. Theming, 4. Responsive Design, 5. Implementation Integrity (CRITICAL), Audit Health Score, Detailed Findings by Severity, Diagnostic Scan (+6 more)

### Community 113 - "New visual work"
Cohesion: 0.14
Nodes (14): 1. Decide what is already true, 2. Ask what will change the work, 3. Choose the right amount of invention, 4. Commit the world, 5. Record the decision, 6. Build with full commitment, 7. Inspect and finish, Both paths (+6 more)

### Community 114 - "optimize.md"
Cohesion: 0.14
Nodes (13): Animation Performance, Assess Performance Issues, Core Web Vitals Optimization, Cumulative Layout Shift (CLS < 0.1), Interaction to Next Paint (INP < 200ms), Largest Contentful Paint (LCP < 2.5s), Loading Performance, Network Optimization (+5 more)

### Community 115 - "Quality Rules"
Cohesion: 0.14
Nodes (13): Activation Contract, Animation, Content & Accessibility, Dark Mode & Theming, Decision Gates, Design, Execution Steps, Hard Rules (+5 more)

### Community 116 - "serializers.py"
Cohesion: 0.14
Nodes (10): EnlaceRestablecimientoInvalido, GoogleSocialLoginSerializer, Meta, Exception, Serializers de autenticación: registro tradicional (CU-001) y Google OAuth. -…, Login/registro con Google OAuth (flujo `id_token`). Distingue dos casos según…, Representación del usuario autenticado (endpoints `/api/auth/user/`). El…, El `uid` o el `token` del enlace de restablecimiento son inválidos. Se lanza… (+2 more)

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
Cohesion: 0.22
Nodes (9): Color, Components, Layout, Motion, Operate mode depth (and Read notes), Product constraints, Product permissions, The product slop test (+1 more)

### Community 133 - "Shape"
Cohesion: 0.22
Nodes (8): Cadence, Confirm and stop, Phase 1: Discovery interview, Phase 2: Resolve the design direction, Phase 3: Write the brief, Round 1: purpose, people, and outcome, Round 2: material, behavior, and boundaries, Shape

### Community 134 - "LANGUAGE AND GRAMMAR PATTERNS"
Cohesion: 0.25
Nodes (8): 10. Rule of Three Overuse, 11. Elegant Variation (Synonym Cycling), 12. False Ranges, 13. Passive Voice and Subjectless Fragments, 7. Overused "AI Vocabulary" Words, 8. Avoidance of "is"/"are" (Copula Avoidance), 9. Negative Parallelisms and Tailing Negations, LANGUAGE AND GRAMMAR PATTERNS

### Community 135 - "adapt.native.md"
Cohesion: 0.25
Nodes (7): Adaptation Strategies, Assess Adaptation Challenge, Implement & Verify, Orientation & foldables, Phone → Tablet (iPad / large screens), Platform → platform (iOS ↔ Android), Web → native (porting a website or web app)

### Community 136 - "Android platform"
Cohesion: 0.25
Nodes (8): Android platform, Color & theming, Components & motion, Layout & structure, The Android slop test, Touch targets, Typography, Verifying the build

### Community 137 - "colorize.md"
Cohesion: 0.25
Nodes (7): Apply at system scale, Audit before choosing, Choose a strategy, Contrast and perception, Live-mode signature params, Verify, Visitor mode

### Community 138 - "Persona-Based Design Testing"
Cohesion: 0.25
Nodes (8): 1. Impatient Power User: "Alex", 2. Confused First-Timer: "Jordan", 3. Accessibility-Dependent User: "Sam", 4. Deliberate Stress Tester: "Riley", 5. Distracted Mobile User: "Casey", Persona-Based Design Testing, Project-Specific Personas, Selecting Personas

### Community 139 - "doctor.md"
Cohesion: 0.25
Nodes (7): Monorepo notes, Opting out of the boot check, Step 1: Run the pass, Step 2: Act by severity, Step 3: Deprecated fields are binding, Step 4: Do not overclaim on truth drift, What this owns, and what it does not

### Community 140 - "Extract Flow"
Cohesion: 0.25
Nodes (7): Extract Flow, Step 1: Discover the Design System, Step 2: Identify Patterns, Step 3: Plan Extraction, Step 4: Extract & Enrich, Step 5: Migrate, Step 6: Document

### Community 141 - "live-setup.md"
Cohesion: 0.25
Nodes (7): append-arrays, append-string, Config drift, Consent prompt (use this phrasing), CSP detection (first-time only), Troubleshooting, Write the config

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

### Community 152 - "Diagnostic Scan"
Cohesion: 0.33
Nodes (6): 1. Accessibility (VoiceOver / TalkBack), 2. Performance, 3. Appearance & Theming, 4. Platform Conformance (CRITICAL), 5. Adaptivity, Diagnostic Scan

### Community 153 - "$impeccable hooks"
Cohesion: 0.33
Nodes (6): Constraints, Failure modes, Flow, $impeccable hooks, Routing, Triage findings

### Community 154 - "Visualize: Direction Comps & Asset Production"
Cohesion: 0.33
Nodes (5): After approval: the comp becomes a spec, Generate three compositional options, One approval point, Plates and provenance, Visualize: Direction Comps & Asset Production

### Community 155 - "impeccable"
Cohesion: 0.60
Nodes (5): impeccable script, check_download(), fetch_url(), probe_ok(), setup_help()

### Community 156 - "LoginSerializer"
Cohesion: 0.40
Nodes (3): LoginSerializer, Login por credenciales distinguiendo cuenta no activada (403). El backend por…, No-op: la verificación de email la cubre el ciclo `estado`. dj-rest-auth…

### Community 157 - "ComplejidadContrasenaValidator"
Cohesion: 0.33
Nodes (3): ComplejidadContrasenaValidator, Validadores de autenticación (CU-001). - `ComplejidadContrasenaValidator`:…, Validador de contraseña según las reglas del CU-001 (docs/02).

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

## Ambiguous Edges - Review These
- `FilmAI Landing Marketing / Hero Visual` → `Poster Title Text (Unverified Visual Content)`  [AMBIGUOUS]
  frontend/public/collage-posters/Opcion 1.jpg · relation: conceptually_related_to
- `Poster Title Text (Unverified Visual Content)` → `Opcion 1 Collage Poster Image`  [AMBIGUOUS]
  frontend/public/collage-posters/Opcion 1.jpg · relation: conceptually_related_to
- `FilmAI Hero/Marketing Asset` → `Collage Poster Option 3`  [AMBIGUOUS]
  frontend/public/collage-posters/Opcion 3.jpg · relation: conceptually_related_to

## Knowledge Gaps
- **616 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+611 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 858 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `FilmAI Landing Marketing / Hero Visual` and `Poster Title Text (Unverified Visual Content)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Poster Title Text (Unverified Visual Content)` and `Opcion 1 Collage Poster Image`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `FilmAI Hero/Marketing Asset` and `Collage Poster Option 3`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Reference Material` connect `Heuristics Scoring Guide` to `Cognitive Load Assessment`, `Persona-Based Design Testing`, `critique.md`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Why does `Usuario` connect `Usuario` to `usuarios/views.py`, `usuarios/models.py`, `UsuarioFactory`, `seed.py`, `signals.py`, `GoogleOAuthTests`, `Command`, `serializers.py`, `RegisterSerializer`, `LoginSerializer`, `ConfirmarCorreoTests`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Why does `Handle `generate`` connect `Handle `generate`` to `live.md`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **What connects `Migration`, `Migration`, `Migration` to the rest of the system?**
  _616 weakly-connected nodes found - possible documentation gaps or missing edges._