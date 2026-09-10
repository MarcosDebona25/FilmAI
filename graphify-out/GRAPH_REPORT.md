# Graph Report - FilmAI  (2026-09-10)

## Corpus Check
- 124 files · ~484,204 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 848 nodes · 1489 edges · 89 communities (43 shown, 26 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 148 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `118eea5e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TMDBClient
- Modelos de Datos y de Diseño (doc 03)
- usuarios/views.py
- FilmAI
- ResendBackend
- TMDBClientCache
- UsuarioFactory
- RecuperarContrasenaTests
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
- Frontend CI Job (ESLint + Prettier)
- scripts
- ConfirmarCorreoTests
- RegisterPage
- eslint.config.mjs
- FilmAI Collage Poster Design — Option 2
- Command
- UsuarioManager
- Humanizer Skill
- UsuarioAdmin
- nombre_completo
- Conventional Commit Decision Gates
- vercel-quality Skill README
- manage.py
- UsuariosConfig
- .is_active
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

## God Nodes (most connected - your core abstractions)
1. `TMDBClient` - 28 edges
2. `Command` - 28 edges
3. `Usuario` - 28 edges
4. `UsuarioFactory` - 27 edges
5. `apiFetch()` - 19 edges
6. `TMDBClientTest` - 18 edges
7. `RecuperarContrasenaTests` - 17 edges
8. `GoogleOAuthTests` - 17 edges
9. `FilmAI` - 17 edges
10. `TMDBClientCache` - 16 edges

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

## Communities (89 total, 26 thin omitted)

### Community 0 - "TMDBClient"
Cohesion: 0.06
Nodes (27): _build_key(), get_redis(), TMDBClientCache, TMDBClient, Exception, TMDB rejected the request because its rate limit was exceeded., TMDB could not find the requested resource., TMDB rejected the request as invalid. (+19 more)

### Community 1 - "Modelos de Datos y de Diseño (doc 03)"
Cohesion: 0.09
Nodes (57): Chatbot basado en LLM para recomendaciones personalizadas, Presentación de la Idea-Proyecto (doc 01), FilmAI — Plataforma Web de Reseñas Cinematográficas con Recomendaciones Inteligentes, CU-001: Crear cuenta de usuario, CU-003: Iniciar sesión, CU-008: Visualizar Catálogo, CU-013: Interactuar con el chatbot, CU-015: Gestionar Reseña y Calificación (ABM) (+49 more)

### Community 2 - "usuarios/views.py"
Cohesion: 0.05
Nodes (34): APIView, URL configuration for filmai project. Rutas de autenticación (docs/05 —…, EnlaceRestablecimientoInvalido, Exception, El `uid` o el `token` del enlace de restablecimiento son inválidos. Se lanza…, Solicitud de restablecimiento de contraseña (CU-020). Envía un email con un…, Confirmación del restablecimiento con nueva contraseña (CU-020). Valida el par…, RecuperarContrasenaSerializer (+26 more)

### Community 3 - "FilmAI"
Cohesion: 0.09
Nodes (44): docs/decisiones.md Decision Log, AGENTS.md Agent Conventions, Domain Documentation (docs 01-05), django-allauth 65.19.1, usuarios.views.ConfirmarCorreoView, Backend Python Requirements, Resend Email Provider, djangorestframework-simplejwt (+36 more)

### Community 4 - "ResendBackend"
Cohesion: 0.11
Nodes (15): Backend de email de Django sobre la API HTTP de Resend. Motivación y diseño…, Devuelve la parte HTML si el mensaje es multipart/alternative., Envía `EmailMessage` vía `resend.Emails.send` (API REST de Resend). - Requiere…, ResendBackend, Validación de la configuración de email al arranque. En producción la ausencia…, Levanta ``ImproperlyConfigured`` si la config de email es inválida. Solo aplica…, validar_configuracion_email(), Django settings for filmai project. Generated by 'django-admin startproject'… (+7 more)

### Community 5 - "TMDBClientCache"
Cohesion: 0.20
Nodes (33): Cache-Aside Pattern, Composition Over Inheritance, fakeredis Test Backend, get_redis() Factory, Graceful Degradation on Redis Failure, httpx.MockTransport Testing, JSON Serialization Round-Trip, Apply Progress: TMDB Redis Cache (C-02) (+25 more)

### Community 6 - "UsuarioFactory"
Cohesion: 0.13
Nodes (18): Adaptadores de allauth para el modelo de usuario personalizado de FilmAI.…, Adaptador social (Google OAuth) para `usuarios.Usuario`., Construye el `Usuario` a partir del perfil de Google. Se llama únicamente en el…, UsuarioSocialAccountAdapter, Meta, Factories de factory_boy para la app `usuarios`. Se usan únicamente para…, Crea un `Usuario` con estado Activa y una contraseña por defecto. La contraseña…, UsuarioFactory (+10 more)

### Community 7 - "RecuperarContrasenaTests"
Cohesion: 0.11
Nodes (7): CsrfCookieTests, Recuperación de contraseña (CU-020 / A-07). Cubre: envío del email con enlace…, Sin nombre ni apellido, el saludo es "Hola usuario"., Protección CSRF del access token en cookie httpOnly (JWT_AUTH_COOKIE_USE_CSRF).…, RecuperarContrasenaTests, UsernameDisponibleTests, TestCase

### Community 8 - "seed.py"
Cohesion: 0.16
Nodes (17): CalificacionFactory, Meta, ProduccionAudiovisualFactory, Factories de factory_boy para la app `catalogo`. Se usan únicamente para…, Crea una producción audiovisual simulando un registro de TMDB. Los campos de…, ResenaFactory, Calificacion, Meta (+9 more)

### Community 9 - "components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 10 - "GoogleOAuthTests"
Cohesion: 0.18
Nodes (10): GoogleSocialLoginSerializer, Login/registro con Google OAuth (flujo `id_token`). Distingue dos casos según…, GoogleOAuthTests, Regresión del 500 en `/api/auth/google/` (RawPostDataException) y del flujo…, Construye el serializer con el request en el estado post-parseo de DRF. Deja…, Fija `SocialAccount.objects.filter(...).exists()` al valor deseado., Regresión: una cuenta de Google ya vinculada inicia sesión SIN los campos extra…, Una cuenta de Google NUEVA (sin SocialAccount) exige los campos que Google no… (+2 more)

### Community 11 - "package.json"
Cohesion: 0.10
Nodes (19): name, private, version, @base-ui/react, clsx, eslint, eslint-config-next, husky (+11 more)

### Community 12 - "Lista"
Cohesion: 0.14
Nodes (15): ListaFactory, Meta, Factories de factory_boy para la app `listas`. Se usan únicamente para sembrar…, Lista, Meta, Modelos de la app `listas`. Implementa las listas de contenidos del usuario y…, Tipo de lista (doc 03: 'Predeterminada' | 'Personalizada')., Lista de producciones de un usuario. Cada usuario tiene por defecto las listas… (+7 more)

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
Cohesion: 0.10
Nodes (14): AbstractBaseUser, Meta, Cliente de la plataforma y, según sus flags, administrador del panel. Concentra…, Usuario, LoginSerializer, Meta, Serializers de autenticación: registro tradicional (CU-001) y Google OAuth. -…, Representación del usuario autenticado (endpoints `/api/auth/user/`). El… (+6 more)

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

### Community 27 - "Frontend CI Job (ESLint + Prettier)"
Cohesion: 0.29
Nodes (8): Backend CI Job (Ruff), CI GitHub Workflow, ESLint, Frontend CI Job (ESLint + Prettier), .husky/pre-commit Hook, Prettier, Ruff, Lint/Format Gate

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

### Community 36 - "UsuarioAdmin"
Cohesion: 0.40
Nodes (4): Admin para el modelo personalizado de usuario. Adapta `UserAdmin` de Django a…, UsuarioAdmin, BaseUserAdmin, register

### Community 37 - "nombre_completo"
Cohesion: 0.40
Nodes (4): nombre_completo(), Filtros de template para saludos en emails transaccionales., Devuelve "Nombre Apellido"; "usuario" si ambos están vacíos. Regla global para…, filter

### Community 39 - "Conventional Commit Decision Gates"
Cohesion: 0.83
Nodes (4): Commit Type Examples, Conventional Commit Decision Gates, Conventional Commits Skill, No AI Attribution Rule

### Community 40 - "vercel-quality Skill README"
Cohesion: 0.83
Nodes (4): vercel-quality Skill README, emil-design-eng Skill, vercel-quality Skill, MUST/SHOULD/NEVER Quality Rules

### Community 41 - "manage.py"
Cohesion: 0.50
Nodes (3): main(), Django's command-line utility for administrative tasks., Run administrative tasks.

### Community 43 - ".is_active"
Cohesion: 0.50
Nodes (3): Logueable solo si la cuenta está en estado Activa. Se deriva de `estado` para…, Permite que Django/allauth activen la cuenta (`is_active = True`). Solo actúa…, setter

### Community 44 - "Collage Poster Option 3"
Cohesion: 0.50
Nodes (4): FilmAI Collage Poster Design, FilmAI Hero/Marketing Asset, FilmAI Project, Collage Poster Option 3

### Community 46 - "AI Review Job (Nikita-Filonov/ai-review)"
Cohesion: 0.67
Nodes (3): AI Review GitHub Workflow, AI Review Job (Nikita-Filonov/ai-review), OpenRouter LLM Provider

## Ambiguous Edges - Review These
- `FilmAI Landing Marketing / Hero Visual` → `Poster Title Text (Unverified Visual Content)`  [AMBIGUOUS]
  frontend/public/collage-posters/Opcion 1.jpg · relation: conceptually_related_to
- `Poster Title Text (Unverified Visual Content)` → `Opcion 1 Collage Poster Image`  [AMBIGUOUS]
  frontend/public/collage-posters/Opcion 1.jpg · relation: conceptually_related_to
- `FilmAI Hero/Marketing Asset` → `Collage Poster Option 3`  [AMBIGUOUS]
  frontend/public/collage-posters/Opcion 3.jpg · relation: conceptually_related_to

## Knowledge Gaps
- **158 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+153 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 376 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `FilmAI Landing Marketing / Hero Visual` and `Poster Title Text (Unverified Visual Content)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Poster Title Text (Unverified Visual Content)` and `Opcion 1 Collage Poster Image`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `FilmAI Hero/Marketing Asset` and `Collage Poster Option 3`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Usuario` connect `Usuario` to `usuarios/views.py`, `UsuarioAdmin`, `UsuarioFactory`, `seed.py`, `GoogleOAuthTests`, `.is_active`, `Lista`, `Command`, `ConfirmarCorreoTests`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `UsuarioFactory` connect `UsuarioFactory` to `RecuperarContrasenaTests`, `seed.py`, `GoogleOAuthTests`, `Lista`, `Command`, `Usuario`, `chatbot/factories.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `Command` connect `Command` to `UsuarioFactory`, `seed.py`, `Lista`, `Usuario`, `chatbot/factories.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `TMDBClient` (e.g. with `TMDBBadRequest` and `TMDBError`) actually correct?**
  _`TMDBClient` has 9 INFERRED edges - model-reasoned connections that need verification._