# Graph Report - FilmAI  (2026-09-18)

## Corpus Check
- Large corpus: 232 files · ~625,604 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 2608 nodes · 6040 edges · 165 communities (107 shown, 58 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 653 edges (avg confidence: 0.89)
- Token cost: 792,834 input · 0 output

## Community Hubs (Navigation)
- Impeccable live-browser UI (JS)
- Impeccable live session (JS)
- modern-screenshot (vendored JS)
- Impeccable configure bar (JS)
- Impeccable live editing (JS)
- Impeccable steer chat (JS)
- Embedding lifecycle & decisions
- TMDB cache & type adapter
- Catalog models & factories
- User serializers & tests
- Daily sync task & spec
- TMDB client & exceptions
- Requirements: use cases & vision
- Impeccable design panel (JS)
- Impeccable design models (JS)
- allauth integration & user serializers
- Materialization tests
- Chat & list models
- User model & repair command
- README & project rules
- Impeccable manual context (JS)
- Django migrations
- Impeccable finish reviewer
- Catalog views & param validation
- Global exception handler & Celery app
- Impeccable delight & distill
- Impeccable adapt (responsive)
- Frontend tooling config
- Password validators & tests
- Chatbot use cases & RNF
- Google OAuth adapter
- Impeccable documenter & doctor
- Impeccable Svelte injection (JS)
- Impeccable manual apply (JS)
- Auth views & allauth flows
- Impeccable manual edit applier
- Endpoint integration tests
- Frontend login & public home
- Humanizer skill
- Docker Compose services & infra spec
- shadcn components.json
- Impeccable craft floor & color
- TMDB cache layer & spec
- Canonical text & freshness tests
- Login tests
- Frontend register & confirm email
- Impeccable audit & critique
- Default resources rollback tests
- Frontend layout & navbar
- Frontend password reset
- Dev seed command
- Cache tests
- Materialization concurrency tests
- tsconfig
- Impeccable session state (JS)
- Embedding task & backfill integration tests
- Catalog settings & service tests
- TMDB client tests
- Resend email backend
- Email templates
- Backfill embeddings & tests
- Frontend complete Google signup
- Impeccable clarify & error states
- Impeccable DOM helper (JS)
- Django project entry (asgi/wsgi/celery)
- Email config validation
- Password reset & throttles
- Plan: UI tasks & accessibility
- Frontend login form & Google auth
- Impeccable iOS/Android platforms
- Impeccable annotation pins (JS)
- Python requirements
- Impeccable hooks & craft floor
- Django app configs
- allauth account adapter
- Profile use cases & shell layout
- CI workflow & pre-commit
- AGENTS.md rules
- Conventional commits skill
- TMDB changes list (get_changes)
- Catalog detail views & C-03
- Frontend devDependencies
- Avatars registry
- Account confirmation & recovery decisions
- Frontend dependencies
- explicar-al-implementar skill
- Impeccable colorize
- Impeccable bolder & polish
- Impeccable DOM recovery (JS)
- Catalog admin
- Auth screens & use cases
- Impeccable animate
- Impeccable asset producer
- Account creation & bcrypt
- Impeccable live setup
- Embedding model tests
- Reset link validation
- Confirm email tests
- CSRF token view
- Lint & CI decisions
- npm scripts
- Impeccable ignore rules (JS)
- send_test_email command
- Google OAuth decisions
- Impeccable CLI script
- UsuarioManager
- LoginSerializer
- visualize.md (small group)
- middleware.ts (small group)
- views.py (small group)
- decisiones.md (small group)
- nombres.py (small group)
- polish.md (small group)
- polish.md (small group)
- quieter.md (small group)
- visualize.md (small group)
- __init__.py (small group)
- entrypoint.sh (small group)
- decisiones.md (small group)
- postcss.config.mjs (small group)
- polish.md (small group)
- polish.md (small group)
- quieter.md (small group)
- quieter.md (small group)
- routing.md (small group)
- routing.md (small group)
- routing.md (small group)
- shape.md (small group)
- typeset.md (small group)
- typeset.md (small group)
- typeset.md (small group)
- typeset.md (small group)
- visualize.md (small group)
- visualize.md (small group)
- visualize.md (small group)
- visualize.md (small group)
- visualize.md (small group)
- SKILL.md (small group)
- SKILL.md (small group)
- SKILL.md (small group)
- SKILL.md (small group)
- SKILL.md (small group)
- SKILL.md (small group)
- recuperar_contrasena_subject.txt (small group)
- decisiones.md (small group)
- decisiones.md (small group)
- decisiones.md (small group)
- decisiones.md (small group)

## God Nodes (most connected - your core abstractions)
1. `materializar()` - 58 edges
2. `TMDBClient` - 54 edges
3. `New visual work (new-work flow)` - 48 edges
4. `sync_catalogo_diaria()` - 45 edges
5. `TMDBClientCache` - 42 edges
6. `ProduccionAudiovisual` - 42 edges
7. `ProduccionEmbedding` - 38 edges
8. `UsuarioFactory` - 38 edges
9. `Usuario` - 36 edges
10. `generar_embedding()` - 34 edges

## Surprising Connections (you probably didn't know these)
- `Pagination passthrough` --references--> `TMDBClientCache`  [INFERRED]
  openspec/specs/tmdb-endpoints/spec.md → backend/catalogo/cache.py
- `Actor: API TMDB` --references--> `TMDBClient`  [INFERRED]
  docs/03_DiagramaCU.md → backend/catalogo/client.py
- `TMDB API (catálogo, búsqueda, tendencias)` --references--> `TMDBClient`  [INFERRED]
  README.md → backend/catalogo/client.py
- `tmdb_a_dominio()` --implements--> `TMDB field mapping table`  [INFERRED]
  backend/catalogo/services/adapter.py → openspec/specs/catalog-materialization/spec.md
- `Ejemplo de diagrama: celery-beat → Redis DB 1 → celery-worker → TMDB (HTTP) / Postgres (SQL)` --conceptually_related_to--> `sync_catalogo_diaria()`  [INFERRED]
  .agents/skills/explicar-al-implementar/SKILL.md → backend/catalogo/tasks.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Humanizer AI-writing pattern catalog (representative patterns)** — agents_skills_humanizer_skill_ai_writing_pattern_catalog, agents_skills_humanizer_skill_1_undue_emphasis_on_significance_legacy_and_broader_trends, agents_skills_humanizer_skill_7_overused_ai_vocabulary_words, agents_skills_humanizer_skill_10_rule_of_three_overuse, agents_skills_humanizer_skill_13_passive_voice_and_subjectless_fragments, agents_skills_humanizer_skill_14_em_dashes_and_en_dashes_cut_them, agents_skills_humanizer_skill_20_collaborative_communication_artifacts, agents_skills_humanizer_skill_21_knowledge_cutoff_disclaimers_and_speculative_gap_filling, agents_skills_humanizer_skill_23_filler_phrases, agents_skills_humanizer_skill_30_diff_anchored_writing [EXTRACTED 1.00]
- **Impeccable critique flow: isolated dual assessment → synthesis → deliver → persist → ask** — agents_skills_impeccable_reference_critique_dual_agent_isolation, agents_skills_impeccable_reference_critique_assessment_a_design_review, agents_skills_impeccable_reference_critique_assessment_b_detector_browser_evidence, agents_skills_impeccable_reference_critique_design_specificity_verdict, agents_skills_impeccable_reference_critique_nielsen_s_10_heuristics, agents_skills_impeccable_reference_critique_deliver_the_report, agents_skills_impeccable_reference_critique_persist_the_snapshot, agents_skills_impeccable_reference_critique_ask_the_user_final_question_gate [EXTRACTED 1.00]
- **Impeccable command playbooks that end by handing off to $impeccable polish** — agents_skills_impeccable_reference_adapt, agents_skills_impeccable_reference_adapt_native, agents_skills_impeccable_reference_animate, agents_skills_impeccable_reference_audit, agents_skills_impeccable_reference_audit_native, agents_skills_impeccable_reference_bolder, agents_skills_impeccable_reference_clarify, agents_skills_impeccable_reference_colorize, agents_skills_impeccable_reference_critique_persist_the_snapshot [EXTRACTED 1.00]
- **Commands that hand off to $impeccable polish for the final pass** — agents_skills_impeccable_reference_delight_delight, agents_skills_impeccable_reference_distill_distill, agents_skills_impeccable_reference_harden_harden, agents_skills_impeccable_reference_layout_layout, agents_skills_impeccable_reference_onboard_onboard, agents_skills_impeccable_reference_optimize_optimize, agents_skills_impeccable_reference_polish_polish [EXTRACTED 1.00]
- **Finish flow: review, disposition, verdict, documentation** — agents_skills_impeccable_reference_new_work_new_visual_work, agents_skills_impeccable_reference_degraded_finish_reviewer_impeccable_finish_reviewer, agents_skills_impeccable_reference_degraded_documenter_impeccable_documenter, agents_skills_impeccable_reference_new_work_direction_contract, agents_skills_impeccable_reference_degraded_finish_reviewer_disposition_vocabulary, agents_skills_impeccable_reference_degraded_finish_reviewer_verdict_pass, agents_skills_impeccable_reference_document_design_md, agents_skills_impeccable_reference_new_work_finish_line [EXTRACTED 1.00]
- **Comp-led build state machine and its measurement tools** — agents_skills_impeccable_reference_new_work_comp_led_build, agents_skills_impeccable_reference_new_work_build_phase_state_machine, agents_skills_impeccable_reference_new_work_comp_spec, agents_skills_impeccable_reference_new_work_plates, agents_skills_impeccable_reference_new_work_hero_gate, agents_skills_impeccable_reference_new_work_comp_diff, agents_skills_impeccable_reference_new_work_font_match, agents_skills_impeccable_reference_new_work_asset_producer, agents_skills_impeccable_reference_visualize_visualize [EXTRACTED 1.00]
- **impeccable CLI subcommands used across reference workflows** — agents_skills_impeccable_reference_routing_impeccable_signals, agents_skills_impeccable_reference_routing_impeccable_detect, agents_skills_impeccable_reference_routing_impeccable_context, agents_skills_impeccable_reference_polish_critique_storage, agents_skills_impeccable_reference_visualize_build_phase, agents_skills_impeccable_reference_visualize_comp_spec, agents_skills_impeccable_reference_visualize_generate_image, agents_skills_impeccable_reference_visualize_serve_question [INFERRED 0.85]
- **Plantillas de email transaccional de FilmAI (confirmación + recuperación) y su filtro nombre_completo** — backend_templates_account_email_email_confirmation_message_html_doc, backend_templates_account_email_email_confirmation_message_txt_doc, backend_templates_account_email_email_confirmation_signup_message_html_doc, backend_templates_account_email_email_confirmation_signup_message_txt_doc, backend_templates_account_email_email_confirmation_signup_subject_txt_doc, backend_templates_account_email_email_confirmation_subject_txt_doc, backend_templates_registration_recuperar_contrasena_message_html_doc, backend_templates_registration_recuperar_contrasena_message_txt_doc, backend_usuarios_templatetags_nombres_nombre_completo, backend_templates_account_email_email_confirmation_message_email_design_tokens [EXTRACTED 1.00]
- **Cadena de gates de calidad: hook local, CI y regla de AGENTS.md (lint + format + tests)** — husky_pre_commit, _github_workflows_ci_precommit_hook, _github_workflows_ci_frontend_job, _github_workflows_ci_backend_job, _github_workflows_ci_django_tests, agents_lint_format_gate, agents_tests_rule [INFERRED 0.85]
- **Flujo materialización → embedding pending → worker → ready/failed** — backend_catalogo_services_materialization_materializar, backend_catalogo_services_materialization_encolar_embedding, backend_catalogo_tasks_generar_embedding, backend_catalogo_services_embeddings_generar_vector, backend_catalogo_models_produccionembedding, backend_catalogo_models_estadoembedding, docs_decisiones_embeddings_asincronos_con_celery_e_idempotencia, docs_decisiones_c_04a_adelanta_la_infraestructura_minima_de_embeddings, docs_decisiones_c_04a_completa_materializar_y_politica_de_fallo, docs_05_plan_de_desarrollo_c_04a [INFERRED 0.95]
- **Sync diaria C-04b: refresco por /changes, descubrimiento y backfill** — backend_catalogo_tasks_sync_catalogo_diaria, backend_catalogo_tasks_ids_cambiados, backend_catalogo_client_tmdbclient_get_changes, backend_catalogo_tasks_backfill_embeddings, backend_catalogo_services_materialization_materializar, backend_catalogo_services_materialization_necesita_enriquecimiento, docs_decisiones_c_04b_la_sync_escribe_por_materializar_y_frescura_explicita, docs_decisiones_la_frescura_la_responde_tmdb_no_una_ventana_de_tiempo, docs_decisiones_la_sync_refresca_antes_de_descubrir, docs_decisiones_zona_horaria_de_celery_y_backfill_cierra_c_04b, docs_05_plan_de_desarrollo_c_04b, docs_02_especificaci_n_de_requerimientos_cu_021 [INFERRED 0.95]
- **Catálogo híbrido: TMDB en vivo + PostgreSQL como catálogo materializado global** — docs_decisiones_arquitectura_hibrida_del_catalogo, docs_decisiones_corpus_semantico_global_y_progresivo, backend_catalogo_client_tmdbclient, backend_catalogo_cache_tmdbclientcache, backend_catalogo_models_produccionaudiovisual, docs_03_modelos_de_datos_y_de_dise_o_catalogo_materializado_global_y_progresivo, docs_05_plan_de_desarrollo_contratos_ya_decididos, docs_02_especificaci_n_de_requerimientos_cu_008, docs_02_especificaci_n_de_requerimientos_cu_019, docs_02_especificaci_n_de_requerimientos_cu_021 [INFERRED 0.85]
- **Nightly catalog sync flow: beat enqueues, Redis brokers, worker runs the sync, sync calls materializar per item** — docker_compose_celery_beat, docker_compose_redis, docker_compose_celery_worker, backend_catalogo_tasks_sync_catalogo_diaria, backend_catalogo_services_materialization_materializar, backend_catalogo_client_tmdbclient_get_changes [INFERRED 0.85]
- **Embedding lifecycle pipeline: materializar enqueues, generar_embedding claims and calls the provider, backfill retries pending/failed/stale rows** — backend_catalogo_services_materialization_materializar, backend_catalogo_services_materialization_encolar_embedding, backend_catalogo_tasks_generar_embedding, backend_catalogo_services_embeddings_generar_vector, backend_catalogo_tasks_backfill_embeddings, backend_catalogo_models_produccionembedding, backend_catalogo_models_estadoembedding, backend_catalogo_services_embeddings_calcular_source_hash [INFERRED 0.85]
- **TMDB read path: DRF detail views -> TMDBClientCache -> TMDBClient, with TMDBError mapped by the exception handler** — backend_catalogo_views_moviedetailview, backend_catalogo_views_tvdetailview, backend_catalogo_cache_tmdbclientcache, backend_catalogo_client_tmdbclient, backend_catalogo_exceptions_tmdb_exception_handler, backend_catalogo_exceptions_tmdberror [INFERRED 0.85]

## Communities (165 total, 58 thin omitted)

### Community 0 - "Impeccable live-browser UI (JS)"
Cohesion: 0.03
Nodes (116): applyGlobalBarLabelState(), applyOriginalAttrsToSvelteAnchor(), applyParamValue(), applyPlaceholderSizingStyles(), averageRgb01(), bindEditBadgeProxy(), bufferToBase64(), buildInsertPlaceholderSnapshotFromDom() (+108 more)

### Community 1 - "Impeccable live session (JS)"
Cohesion: 0.06
Nodes (86): abortSvelteComponentInjection(), applyParamDefaults(), applyPlaceholderDimensions(), applySavedSessionMeta(), checkpointPayload(), clampVariantIndex(), clearHandled(), clearSession() (+78 more)

### Community 2 - "modern-screenshot (vendored JS)"
Cohesion: 0.09
Nodes (55): ae(), be(), bt(), Ce(), s(), Ct(), de(), dt() (+47 more)

### Community 3 - "Impeccable configure bar (JS)"
Cohesion: 0.07
Nodes (53): actionLabel(), applyConfigureBarChrome(), bindConfigureCountPillTooltip(), bindConfigureInlineControlHover(), bindConfigureModifierPillHover(), buildConfigureActionControl(), buildConfigureCountControl(), buildConfigureRow() (+45 more)

### Community 4 - "Impeccable live editing (JS)"
Cohesion: 0.12
Nodes (53): applyEditing(), beginNewLiveConfiguration(), cancelEditing(), cancelEditingToPicking(), cancelInsertConfigure(), cleanup(), cleanupAcceptedSession(), clearAnnotations() (+45 more)

### Community 5 - "Impeccable steer chat (JS)"
Cohesion: 0.08
Nodes (53): armPageChatForTyping(), attachSteerFocusDebug(), attachSteerFocusGuard(), buildSteerProcessingDots(), buildSteerQueueHint(), clearSteerAwaitTimer(), clearSteerFocusRecoverTimer(), collapsePageChat() (+45 more)

### Community 6 - "Embedding lifecycle & decisions"
Cohesion: 0.11
Nodes (52): EstadoEmbedding, ProduccionEmbedding, Ciclo de vida del embedding (decisión 08/09/2026). `pending` → `processing` →…, Representación semántica de una producción para búsqueda por similitud. Se crea…, calcular_source_hash(), generar_vector(), Huella del texto embebido (SHA-256 hexadecimal, 64 caracteres). Se guarda junto…, Convierte texto en un vector de 1024 dimensiones. PUNTO DE EXTENSIÓN PARA B-06… (+44 more)

### Community 7 - "TMDB cache & type adapter"
Cohesion: 0.06
Nodes (39): get_redis(), dominio_a_tmdb(), Traducción entre el vocabulario de TMDB y el del dominio (C-04a). TMDB dice…, `"movie"` → `TipoProduccion.PELICULA`, `"tv"` → `TipoProduccion.SERIE`. Lanza…, Inversa de `tmdb_a_dominio`, para construir llamadas a la API de TMDB., tmdb_a_dominio(), EmbeddingProviderError, _lista_normalizada() (+31 more)

### Community 8 - "Catalog models & factories"
Cohesion: 0.07
Nodes (45): CalificacionFactory, Meta, ProduccionAudiovisualFactory, Factories de factory_boy para la app `catalogo`. Se usan únicamente para…, Crea una producción audiovisual simulando un registro de TMDB. Los campos de…, ResenaFactory, Calificacion, Meta (+37 more)

### Community 9 - "User serializers & tests"
Cohesion: 0.06
Nodes (24): Meta, Crea usuarios activos con contraseña hasheada., UsuarioFactory, Serializer para actualizar el perfil del usuario. Solo permite modificar campos…, Valida que la fecha de nacimiento no sea futura y el usuario tenga al menos 13…, UsuarioPerfilSerializer, AvatarValidacionTests, CsrfCookieTests (+16 more)

### Community 10 - "Daily sync task & spec"
Cohesion: 0.07
Nodes (28): Sync nocturna del catálogo (C-04b): refresco + descubrimiento. Dos pasadas con…, sync_catalogo_diaria(), _pagina_de_cambios(), Una página de `/{tipo}/changes` con la forma real (17/09/2026)., La pasada de descubrimiento de la sync nocturna (C-04b, fase 2). `materializar`…, Hace que TMDB reporte estos IDs como modificados hoy., SyncCatalogoTests, changes_por_tipo() (+20 more)

### Community 11 - "TMDB client & exceptions"
Cohesion: 0.12
Nodes (24): TMDBClient, Exception, TMDB rejected the request because its rate limit was exceeded., TMDB could not find the requested resource., TMDB rejected the request as invalid., TMDB returned a server-side error., The request could not reach TMDB or its response could not be read., Base exception for TMDB client failures. (+16 more)

### Community 12 - "Requirements: use cases & vision"
Cohesion: 0.08
Nodes (41): Calificación por estrellas 1-10 enteras, Chatbot LLM de recomendaciones (objetivo), FilmAI (idea-proyecto), Población: usuarios casuales de entretenimiento, Alcance del problema (aplicación web de películas/series con chatbot IA), CU-008: Visualizar Catálogo, CU-009: Consultar Listas, CU-010: Buscar Películas/Series por Nombre (+33 more)

### Community 13 - "Impeccable design panel (JS)"
Cohesion: 0.09
Nodes (38): agentHasWorkInFlight(), agentStatusText(), barPaletteForTheme(), brandMarkSvg(), buildParamsPanel(), designPanelCss(), detectPageTheme(), ensureAgentPollTooltip() (+30 more)

### Community 14 - "Impeccable design models (JS)"
Cohesion: 0.08
Nodes (39): buildCollapsible(), buildColorModels(), buildDesignHeader(), buildListHtml(), buildRadiiModels(), buildTypographyModels(), cssSafe(), designEmptyMessage() (+31 more)

### Community 15 - "allauth integration & user serializers"
Cohesion: 0.06
Nodes (27): allauth_account, allauth_account_adapter, allauth_account_forms, allauth_account_utils, allauth_socialaccount_adapter, allauth_socialaccount_helpers, allauth_socialaccount_models, allauth_socialaccount_providers_oauth2_client (+19 more)

### Community 16 - "Materialization tests"
Cohesion: 0.09
Nodes (14): materializar(), Garantiza que la producción exista en la base con su embedding encolado. Recibe…, MaterializacionBase, MaterializacionCarreraTests, MaterializacionIdempotenteTests, MaterializacionPeliculaTests, MaterializacionSerieTests, TestCase (+6 more)

### Community 17 - "Chat & list models"
Cohesion: 0.10
Nodes (27): ChatFactory, MensajeFactory, Meta, Factories de factory_boy para la app `chatbot`. Se usan únicamente para sembrar…, Chat, Mensaje, Meta, Modelos de la app `chatbot`. Implementa la conversación del chatbot (doc 03):… (+19 more)

### Community 18 - "User model & repair command"
Cohesion: 0.07
Nodes (26): AbstractBaseUser, Command, BaseCommand, Repara listas predeterminadas y chat faltantes de usuarios existentes., Meta, Logueable solo si la cuenta está en estado Activa., Permite que Django/allauth activen la cuenta (`is_active = True`), Cliente de la plataforma y, según sus flags, administrador del panel. (+18 more)

### Community 19 - "README & project rules"
Cohesion: 0.08
Nodes (34): Servicio Postgres pgvector/pgvector:pg16 en CI, Regla 2: docs/ (01 a 06) como fuente de verdad, Prefer APCA over WCAG 2 for contrast, WAI-ARIA Authoring Practices Guide (APG) patterns, watchdog[watchmedo] (auto-reload del worker Celery), Presentación Idea-Proyecto, Especificación de Requerimientos, Modelos de Datos y de Diseño (+26 more)

### Community 20 - "Impeccable manual context (JS)"
Cohesion: 0.07
Nodes (34): addManualContextText(), canRestoreManualEditElement(), collectEditableTextRows(), visit(), collectManualContextPieces(), walk(), contextElementForManualEdit(), copyEditContainerContext() (+26 more)

### Community 21 - "Django migrations"
Cohesion: 0.07
Nodes (21): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+13 more)

### Community 22 - "Impeccable finish reviewer"
Cohesion: 0.15
Nodes (32): Disposition vocabulary (recapture/rebuild/fix/ship), Check 0: Evidence (capture validity), Fidelity element matrix (TYPE / MATERIAL / GROUND rows), Impeccable Finish Reviewer (inline degraded role), Rebuild directive, Verdict Pass (scoring fixes resolved/partial/unresolved), buildPath workflow setting (comp-first vs code-first), Simulator screenshots via xcrun simctl (+24 more)

### Community 23 - "Catalog views & param validation"
Cohesion: 0.13
Nodes (15): get_catalog_service(), ParamValidationTest, CatalogoBaseView, DiscoverView, _float_param(), _int_param(), KeywordsView, _materializar_sin_interrumpir() (+7 more)

### Community 24 - "Global exception handler & Celery app"
Cohesion: 0.09
Nodes (19): filmai_exception_handler(), Manejador global de excepciones de FilmAI., Unifica errores DRF y conserva el mapeo especializado de TMDB., CeleryAppTests, ExceptionHandlerTests, SimpleTestCase, Tests del backend de email sobre Resend (filmai.email_backends). Se instancia…, Wiring de Celery con Django (C-04a). Se verifica configuración, no ejecución:… (+11 more)

### Community 25 - "Impeccable delight & distill"
Cohesion: 0.09
Nodes (31): animate.md (authored motion), $impeccable delight, Delight thesis, Emotional moments (success, waiting, empty, error, repeat, discovery), Antoine de Saint-Exupery (perfection quote), $impeccable distill, Progressive disclosure (distill), Simplicity removes obstacles, not features (+23 more)

### Community 26 - "Impeccable adapt (responsive)"
Cohesion: 0.10
Nodes (26): Adaptation is rethinking the experience for the new context, not scaling pixels, Content-driven breakpoints (640/768/1024 usually suffice; clamp() and container queries for fluid values), Mobile-first: base styles for mobile, layer complexity with min-width queries, Orientation and foldables: landscape restructures, never clips; react to posture and hinge, Phone → tablet: restructure, don't stretch; drive structure from size classes / window size classes, Platform → platform: translate idioms, never transplant (iOS ↔ Android table), Web → native: reconform, don't reflow, Never hide core functionality on mobile; same information architecture across contexts (+18 more)

### Community 27 - "Frontend tooling config"
Cohesion: 0.07
Nodes (27): compat, __dirname, eslintConfig, __filename, nextConfig, name, private, version (+19 more)

### Community 28 - "Password validators & tests"
Cohesion: 0.07
Nodes (15): Contraseñas con menos de 8 caracteres deben ser rechazadas., Contraseñas con más de 20 caracteres deben ser rechazadas., Contraseñas sin mayúsculas deben ser rechazadas., Contraseñas sin minúsculas deben ser rechazadas., Contraseñas sin dígitos deben ser rechazadas., Contraseñas sin caracteres especiales deben ser rechazadas., Cada carácter especial permitido debe ser aceptado individualmente., Una contraseña de exactamente 8 caracteres debe ser aceptada si cumple todas… (+7 more)

### Community 29 - "Chatbot use cases & RNF"
Cohesion: 0.13
Nodes (29): CU-013: Interactuar con el chatbot, CU-014: Cancelar recomendación en curso, CU-018: Entregar respuestas basadas en historial y reseñas, RNF #14: integración con bases de datos externas de películas vía API, RNF #3: anonimizar datos sensibles antes de enviarlos al LLM, RNF #6: chatbot responde <5 s simples / <15 s con agregación, Actor: API LLM de Chatbot, Chatbot como FAB flotante con panel drawer (+21 more)

### Community 30 - "Google OAuth adapter"
Cohesion: 0.13
Nodes (15): Adaptador social (Google OAuth) para `usuarios.Usuario`., Persiste el alta social de forma atómica., Construye un perfil nuevo sin sobrescribir una cuenta vinculada., UsuarioSocialAccountAdapter, EstadoCuenta, Estados del ciclo de vida de una cuenta de usuario (CU-001, CU-002, CU-007)., GoogleOAuthTests, Regresión del 500 en `/api/auth/google/` (RawPostDataException) y del flujo… (+7 more)

### Community 31 - "Impeccable documenter & doctor"
Cohesion: 0.15
Nodes (27): Build wins over direction contract, Impeccable Documenter (inline degraded role), design-md-drift finding, $impeccable doctor, Schema drift, Finding severities (auto / mention / route), Truth drift, Sidecar component translation rules (shadow-DOM snippets) (+19 more)

### Community 32 - "Impeccable Svelte injection (JS)"
Cohesion: 0.11
Nodes (26): abandonForeignSession(), commitAcceptedSvelteComponentToDom(), componentModuleCandidates(), copyToClipboard(), describeMountFailure(), detectDevServerBase(), discardOrphanedSession(), dismissToast() (+18 more)

### Community 33 - "Impeccable manual apply (JS)"
Cohesion: 0.18
Nodes (26): clearStoredManualApplyState(), fetchPendingCount(), handleManualEditActivity(), hidePendingApplyDock(), manualApplyLoadingText(), manualApplyStateKey(), manualEditEventForCurrentPage(), numberOrNull() (+18 more)

### Community 34 - "Auth views & allauth flows"
Cohesion: 0.09
Nodes (22): allauth_account_internal_flows_email_verification, allauth_account_models, allauth_socialaccount_providers_google_views, GoogleLogin, LoginView, Vistas de autenticación. `GoogleLogin` expone el login social de Google (flujo…, Login/registro con Google OAuth 2.0 (Google Identity Services)., Login que usa ``LenientJWTCookieAuthentication``. Evita 401 cuando el browser… (+14 more)

### Community 35 - "Impeccable manual edit applier"
Cohesion: 0.14
Nodes (23): Canonical JSON result (done/partial/error), Entry Atomicity, Impeccable Manual Edit Applier (inline degraded role), Repair mode (post-validation source repair), Spatial thesis, Squint test (reading order), Agent-driven fallback (generated / runtime-injected sources), pbakaus/impeccable live-e2e agent template (agent.mjs) (+15 more)

### Community 37 - "Frontend login & public home"
Cohesion: 0.12
Nodes (15): POSTERS, GoogleButton(), GoogleButtonProps, GoogleCredentialResponse, Window, Button(), buttonVariants, cn() (+7 more)

### Community 38 - "Humanizer skill"
Cohesion: 0.10
Nodes (20): blader/humanizer (upstream repo; Skills CLI + Claude Code plugin install), Humanizer version history 1.0.0 → 2.8.2, Voice Calibration (README usage: paste 2-3 paragraphs of own writing), Wikipedia: Signs of AI writing (WikiProject AI Cleanup), 10. Rule of three overuse, 13. Passive voice and subjectless fragments, 14. Em dashes and en dashes: hard cut in the final rewrite, 1. Undue emphasis on significance, legacy and broader trends (+12 more)

### Community 39 - "Docker Compose services & infra spec"
Cohesion: 0.16
Nodes (22): backend, celery-beat, celery-worker, db, filmai_network, frontend, Named volumes pgdata and redisdata, redis (+14 more)

### Community 40 - "shadcn components.json"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 41 - "Impeccable craft floor & color"
Cohesion: 0.13
Nodes (18): openai.yaml (Codex agent interface: display_name, short_description, default_prompt), Amplify what the system already owns; more effects is the opposite of bold, On colored surfaces derive secondary text from the foreground or surface hue, never washed-out generic gray, WCAG AA minimums: body text 4.5:1, large text 3:1, controls/icons/focus indicators 3:1, `craft` is a deprecated alias for an ordinary new-work request, Browser surfaces carry the design: theme text selection, caret, scrollbars, focus rings, underline offset, tabular numerals, When the design hook is active it enforces the mechanical checks as you edit; act on its findings instead of re-auditing, Declare elevation once (border or shadow); card radii 12–16px; tracking -0.02 to -0.03em reads better than the -0.04em floor (+10 more)

### Community 42 - "TMDB cache layer & spec"
Cohesion: 0.16
Nodes (10): TMDBClientCache, Arquitectura MVC por capas (Controller, Service, Repository), Repositorio Externo (API TMDB), Repositorio Local (base de datos propia), Cache-aside lookup, Cache miss stores and returns, Graceful degradation on Redis failure, JSON serialization round-trip (+2 more)

### Community 43 - "Canonical text & freshness tests"
Cohesion: 0.17
Nodes (8): construir_texto_canonico(), Arma el texto que representa a la producción para la búsqueda semántica. Recibe…, _necesita_enriquecimiento(), Decide si hay que traer el detalle de TMDB para esta fila. Reemplaza el…, MaterializacionFrescuraTests, Cuándo una fila necesita (re)traer el detalle de TMDB (C-04b, fase 1).…, Texto que se embebe y su huella (C-04a). No toca la base:…, TextoCanonicoTests

### Community 44 - "Login tests"
Cohesion: 0.10
Nodes (11): LoginDualTests, Tests de integración para ambos mecanismos de autenticación. Verifica que tanto…, Login con correo electrónico y contraseña debe funcionar., Login con nombre de usuario y contraseña debe funcionar., El login por correo debe ser insensible a mayúsculas., El login por nombre de usuario debe ser insensible a mayúsculas., Login con correo incorrecto debe fallar., Login con nombre de usuario incorrecto debe fallar. (+3 more)

### Community 45 - "Frontend register & confirm email"
Cohesion: 0.15
Nodes (15): ConfirmarCorreoPage(), Estado, maxFechaNacimiento(), RegisterPage(), onBlurCampo(), onSubmit(), validarCampo(), API_URL (+7 more)

### Community 46 - "Impeccable audit & critique"
Cohesion: 0.16
Nodes (18): Audit documents issues; it doesn't fix them (routes to other commands), Implementation Integrity verdict (start here): coherent product-specific system vs. repeated shortcuts and design-system drift, Responsive check: interactive elements < 44x44px, fixed widths, horizontal scroll, text scaling, Allowed recommendation commands (adapt, animate, audit, bolder, clarify, colorize, critique, delight, distill, document, harden, layout, onboard, optimize, overdrive, polish, quieter, shape, typeset); end with polish, Ask the User / final-question gate: 2–4 targeted questions with concrete options, last in the same message, or a literal `Questions skipped: <reason>` line, Assessment A: unanchored design review (design specificity, holistic design, cognitive load, emotional journey, Nielsen heuristics 0–4), Assessment B: `impeccable detect --json` CLI scan + browser overlay via `impeccable live-server` and detect.js, Cognitive Load Assessment: intrinsic / extraneous / germane load, 8-item checklist, 8 common violations (+10 more)

### Community 47 - "Default resources rollback tests"
Cohesion: 0.11
Nodes (14): TransactionTestCase, Tests de usuarios: disponibilidad de username (A-05) y confirmación de cuenta…, RecursosPredeterminadosRollbackTests, RecursosPredeterminadosTests, Validadores de autenticación (CU-001). - `ComplejidadContrasenaValidator`:…, django_core_management, django_test, django_utils_translation (+6 more)

### Community 48 - "Frontend layout & navbar"
Cohesion: 0.12
Nodes (15): frontend_app_globals, inter, metadata, roboto, iniciales(), NAV_LINKS, Navbar(), logout() (+7 more)

### Community 49 - "Frontend password reset"
Cohesion: 0.18
Nodes (15): Campo, Errores, GENEROS, VALIDADORES, decodificarParametro(), EnlaceInvalido, Estado, RestablecerContrasenaPage() (+7 more)

### Community 50 - "Dev seed command"
Cohesion: 0.15
Nodes (9): atomic, Command, BaseCommand, Crea el catálogo repartido entre películas y series., Cada usuario califica un subconjunto aleatorio del catálogo. Se pasan `usuario`…, Crea las 3 listas predeterminadas y algunas personalizadas por usuario., Usa el chat por defecto (creado por la señal) y agrega mensajes., Borra los datos de las apps de negocio (orden de hijos a padres). El borrado en… (+1 more)

### Community 52 - "Materialization concurrency tests"
Cohesion: 0.11
Nodes (10): MaterializacionConcurrenciaTests, materializar_en_paralelo(), _ParchesDeMaterializacion, TransactionTestCase, Doble del `TMDBClientCache`: enriquecimiento (C-04a) y listados (C-04b)., Aísla la materialización de TMDB y del broker de Celery. Es un mixin para poder…, El detalle sigue siendo passthrough de TMDB y además materializa (C-04a). Se…, Dos hilos reales materializando la misma producción (C-04a).… (+2 more)

### Community 53 - "tsconfig"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 54 - "Impeccable session state (JS)"
Cohesion: 0.21
Nodes (15): createLiveBrowserSessionState(), clearHandled(), clearScrollY(), clearSession(), isHandled(), loadSession(), markHandled(), nextCheckpointRevision() (+7 more)

### Community 55 - "Embedding task & backfill integration tests"
Cohesion: 0.18
Nodes (5): BackfillIntegracionTests, GenerarEmbeddingTaskTests, patch, El backfill con `generar_embedding` REAL: que el reencolado sirva. Los tests de…, Idempotencia de la tarea de Celery (C-04a). Celery entrega "al menos una vez":…

### Community 56 - "Catalog settings & service tests"
Cohesion: 0.12
Nodes (7): CatalogoSettingsTest, GetCatalogServiceTest, SimpleTestCase, Reparto y directores (C-04a). Los endpoints de detalle de TMDB NO traen cast ni…, Lista de cambios (C-04b, fase 2). `/{tipo}/changes` devuelve los IDs que TMDB…, TMDBChangesTest, TMDBCreditsTest

### Community 57 - "TMDB client tests"
Cohesion: 0.20
Nodes (3): override_settings, TMDBClientTest, handler()

### Community 58 - "Resend email backend"
Cohesion: 0.24
Nodes (7): Devuelve la parte HTML si el mensaje es multipart/alternative., Envía `EmailMessage` vía `resend.Emails.send` (API REST de Resend). - Requiere…, ResendBackend, override_settings, patch, ResendBackendTests, BaseEmailBackend

### Community 59 - "Email templates"
Cohesion: 0.24
Nodes (17): resend (envío de email), activate_url (contexto de plantilla allauth), Flujo de confirmación de correo por email (allauth), Diseño de email FilmAI (tabla role=presentation, dark #0d0d14/#161625, acento #e67e22, enlace #f5c518), Email confirmación de cuenta (HTML, allauth), Email confirmación de cuenta (texto plano, allauth), Email confirmación al registrarse (HTML, allauth signup), Email confirmación al registrarse (texto plano, allauth signup) (+9 more)

### Community 60 - "Backfill embeddings & tests"
Cohesion: 0.29
Nodes (4): backfill_embeddings(), Recupera el trabajo de embeddings que quedó sin completar (C-04b).…, BackfillEmbeddingsTests, Recuperación del trabajo de embeddings que quedó sin completar (C-04b, fase 3).…

### Community 61 - "Frontend complete Google signup"
Cohesion: 0.20
Nodes (14): Campo, CompletarGooglePage(), onBlurCampo(), onGoogle(), validarCampo(), Errores, GENEROS, maxFechaNacimiento() (+6 more)

### Community 62 - "Impeccable clarify & error states"
Cohesion: 0.12
Nodes (15): Actionable error: what failed, why (when known and useful), how to recover, Empty states distinguish first use, no results, filters, permissions and failure; loading names the real operation and never invents progress, Message hierarchy per state: the one fact now, the next action, supporting context, tone, Forms: persistent labels (placeholders are examples), requirements before submission, validation without blame, Localization: complete translatable messages, structured variables, room for expansion, accessible names aligned with visible labels, Destructive actions: name object and consequence; prefer undo over confirmation when recovery is safe; no Yes/No/OK/Submit buttons, Information conveyed by color also needs text, shape, iconography or position, Heuristic 3: User Control and Freedom (undo, cancel, escape) (+7 more)

### Community 63 - "Impeccable DOM helper (JS)"
Cohesion: 0.17
Nodes (11): createLiveBrowserDomHelpers(), activeElementDeep(), cssId(), liveUiRoot(), makeFrozenAnchor(), own(), pickable(), rectIsUsableAnchor() (+3 more)

### Community 64 - "Django project entry (asgi/wsgi/celery)"
Cohesion: 0.12
Nodes (11): ASGI config for filmai project. It exposes the ASGI callable as a module-level…, App de Celery del proyecto (C-04a). Celery corre en un proceso aparte del…, Paquete del proyecto Django. Importar la app de Celery acá hace que quede…, WSGI config for filmai project. It exposes the WSGI callable as a module-level…, main(), Django's command-line utility for administrative tasks., Run administrative tasks., django_core_asgi (+3 more)

### Community 65 - "Email config validation"
Cohesion: 0.17
Nodes (10): Validación de la configuración de email al arranque. En producción la ausencia…, Levanta ``ImproperlyConfigured`` si la config de email es inválida. Solo aplica…, validar_configuracion_email(), Django settings for filmai project. Generated by 'django-admin startproject'…, ConfiguracionEmailTests, python-decouple (variables de entorno), celery_schedules, decouple (+2 more)

### Community 66 - "Password reset & throttles"
Cohesion: 0.15
Nodes (12): Solicitud de restablecimiento sin revelar si un correo está registrado., RecuperarContrasenaSerializer, EmailRateThrottle, EmailThrottleStatusMixin, Clases de throttling personalizadas para FilmAI. Proporcionan límites de…, Throttle basado en email para recuperación de contraseña. Limita las…, Usa el email del request como clave de throttle. Si el email no está presente o…, Mixin para agregar información de intentos restantes en la respuesta. Los views… (+4 more)

### Community 67 - "Plan: UI tasks & accessibility"
Cohesion: 0.13
Nodes (16): Accesibilidad WCAG 2.1 AA, Pantallas de error (404, 500/timeout), A-04: Pantalla de Login (UI), F-01: Docker + docker-compose, F-02: Scaffold Django + DRF, F-03: Scaffold Next.js + Tailwind + Shadcn, F-05: Seeds de desarrollo, Módulo 0 — Fundación (+8 more)

### Community 68 - "Frontend login form & Google auth"
Cohesion: 0.18
Nodes (12): LoginForm(), cerrarModalRecuperar(), onGoogle(), onSubmitRecuperar(), GoogleLinkButton(), CAMPOS_FALTANTES, CompletarGoogleResult, esFaltaDeCamposGoogle() (+4 more)

### Community 69 - "Impeccable iOS/Android platforms"
Cohesion: 0.18
Nodes (15): android.md (Android platform reference), Platform (web / ios / android / adaptive), Dynamic Type and San Francisco, HIG conformance (system navigation, safe area, modality), iOS platform reference, iOS slop test, SF Symbols iconography, 44x44 pt touch targets (+7 more)

### Community 70 - "Impeccable annotation pins (JS)"
Cohesion: 0.24
Nodes (15): beginEditPin(), buildAnnotationsForCapture(), buildPinElement(), cancelEditingPin(), finalizeEditingPin(), initAnnotOverlay(), localCoords(), onAnnotDown() (+7 more)

### Community 71 - "Python requirements"
Cohesion: 0.14
Nodes (15): bcrypt (hash de contraseñas), celery >=5.3,<5.5, django-cors-headers, dj-rest-auth >=7.0,<8.0, Django >=5.0,<5.2, Dependencias Python del backend (requirements.txt), djangorestframework >=3.15,<3.16, drf-spectacular (OpenAPI schema) (+7 more)

### Community 72 - "Impeccable hooks & craft floor"
Cohesion: 0.23
Nodes (14): craft-floor.md (Refuse list and craft floors), Not-canonized defects line, Check 6: Floor (craft-floor Refuse list), impeccable context (session boot), Tool version drift, Design detector hook (post-tool-use), Ignore scoping (ignore-value < file-scoped value < ignore-file < ignore-rule), .impeccable/config.json (unified project config) (+6 more)

### Community 73 - "Django app configs"
Cohesion: 0.14
Nodes (9): CatalogoConfig, AppConfig, ChatbotConfig, AppConfig, ListasConfig, AppConfig, AppConfig, UsuariosConfig (+1 more)

### Community 74 - "allauth account adapter"
Cohesion: 0.14
Nodes (10): django-allauth[socialaccount]==65.19.1 (pin exacto), Adaptador de cuenta para el registro tradicional (dj-rest-auth)., Mapea los campos de allauth a los de ``Usuario``., Activa la cuenta al confirmar su correo de forma atómica., Envía la confirmación a la pantalla correspondiente de la SPA., UsuarioAccountAdapter, ConfirmarCorreoView, Confirma la cuenta a partir del enlace del email (CU-002). Reemplaza al… (+2 more)

### Community 75 - "Profile use cases & shell layout"
Cohesion: 0.24
Nodes (14): CU-005: Acceder a la sección de perfil de usuario, CU-006: Modificar perfil, CU-007: Dar de baja la cuenta, Layout base (Shell): navbar Inicio/Buscar/Listas + avatar, Perfil con edición inline, Preferencias (tema, privacidad, notificaciones, baja), Módulo 4 — Perfil y Preferencias (Gonza), P-01: Endpoint de perfil (+6 more)

### Community 76 - "CI workflow & pre-commit"
Cohesion: 0.21
Nodes (12): Job backend: Ruff + tests Django, CI workflow (GitHub Actions), ESLint (sin warnings permitidos), Job frontend: ESLint + Prettier, Pre-commit hook local (.husky/pre-commit), Prettier --check, Ruff check + format --check, Trigger en PRs hacia main y feat/** (PRs apilados) (+4 more)

### Community 77 - "AGENTS.md rules"
Cohesion: 0.18
Nodes (13): python manage.py test --verbosity=2 en CI, Regla 3: ante ambigüedad, preguntar al usuario, Regla 1: registrar decisiones en docs/decisiones.md, AGENTS.md — Reglas para agentes en FilmAI, Regla 9: estructura docs/ · openspec/specs · openspec/changes · graphify-out, Regla 7: consultar y actualizar el grafo graphify, Regla 8: sin herramientas de review automático en PRs, Structured question / user-input tool (+5 more)

### Community 78 - "Conventional commits skill"
Cohesion: 0.19
Nodes (11): Commit Type Examples table (one example message per type), Commit subject format `type(scope): description`, Eleven allowed commit types (feat, fix, chore, docs, style, refactor, perf, test, build, ci, revert), Pick exactly one type; most specific wins, state the alternative, No AI attribution in commits (no Co-Authored-By), Design brief (shape output), Regla 6: .agents/skills/ es la única fuente de skills, vercel-quality README (+3 more)

### Community 79 - "TMDB changes list (get_changes)"
Cohesion: 0.26
Nodes (8): _ids_cambiados(), IDs que TMDB reporta como modificados en las últimas 24 h., IdsCambiadosTests, El paginador de la lista de cambios de TMDB (C-04b, fase 2). `_ids_cambiados`…, Endpoints /movie/changes y /tv/changes, 18/09/2026 — actualizadas pasa a ya_existentes; C-04b cerrada, 15/09/2026 — La frescura la responde TMDB, no una ventana de tiempo, 17/09/2026 — La sync refresca antes de descubrir

### Community 80 - "Catalog detail views & C-03"
Cohesion: 0.32
Nodes (13): MovieDetailView, TVDetailView, C-03: Endpoints de catálogo, 13/09/2026 — Corrección de sintaxis en las rutas del catálogo, 12/09/2026 — C-03: endpoints de catálogo públicos con AllowAny explícito, 14/09/2026 — Rutas de detalle sin conversor int: 400 en vez de 404 ante id_tmdb no entero, Failure isolation, Detail views materialize as a side effect (+5 more)

### Community 81 - "Frontend devDependencies"
Cohesion: 0.15
Nodes (13): devDependencies, eslint, eslint-config-next, eslint-config-prettier, @eslint/eslintrc, husky, prettier, tailwindcss (+5 more)

### Community 82 - "Avatars registry"
Cohesion: 0.18
Nodes (9): es_avatar_valido(), obtener_avatar(), Registro centralizado de avatares disponibles., Indica si ``avatar_id`` pertenece al registro y es un entero., Obtiene el recurso asociado o ``None``., Lanza ``ValidationError`` si el avatar no es válido., validar_avatar_id(), Valida que avatar_id sea uno de los avatares disponibles. (+1 more)

### Community 83 - "Account confirmation & recovery decisions"
Cohesion: 0.30
Nodes (12): CU-002: Confirmar cuenta por correo electrónico, CU-020: Recuperar contraseña, A-02: Confirmación de cuenta, A-05: Pantalla de Registro (UI), A-07: Recuperar contraseña, 24/08/2026 — A-04/A-05: link de recuperación solo visual, error genérico de login y endpoint de disponibilidad de username, 24/08/2026 — A-07: Recuperación de contraseña (CU-020) conectada de punta a punta, 24/08/2026 — Confirmación de correo: validez 24h, templates propios en español y errores diferenciados (CU-002) (+4 more)

### Community 84 - "Frontend dependencies"
Cohesion: 0.17
Nodes (12): dependencies, @base-ui/react, class-variance-authority, clsx, lucide-react, next, react, react-dom (+4 more)

### Community 85 - "explicar-al-implementar skill"
Cohesion: 0.18
Nodes (10): Regla 4: Breve, pero sin perder claridad (apuntar a la versión corta y expandir donde el concepto lo pida), Regla 2: Diagrama de cajas y flechas al tocar arquitectura o comunicación entre servicios, Regla 3: Explicar cada test al escribirlo, Regla 1: No dar por sabido ningún concepto de framework, Regla 7: Ofrecer opciones solo cuando son reales, Ejemplo de diagrama: celery-beat → Redis DB 1 → celery-worker → TMDB (HTTP) / Postgres (SQL), Qué NO hace la skill: no es tutorial, no narra línea por línea, no reemplaza docs/decisiones.md, Regla 5: Avanzar en unidades chicas (paso, explicación, verificación) (+2 more)

### Community 86 - "Impeccable colorize"
Cohesion: 0.20
Nodes (10): Material color roles + Dynamic Color (Material You) with static fallback; tonal elevation, Visitor mode for motion: Persuade/Experience may let motion carry the voice; Operate/Read keep transitions fast, Theming check: hard-coded colors, broken dark mode, inconsistent tokens, Live-mode signature param `color-amount` (var(--p-color-amount, 0.5)), Build color roles (canvas/elevated surfaces, text, action/focus/selection, borders, semantic, data), not a bag of swatches, Dark mode: design surface elevation and contrast explicitly; do not invert the light theme mechanically, Prefer OKLCH for a new web palette, Visitor mode for color: Persuade/Experience may own large regions; Operate/Read encode action, selection, status, wayfinding (rarity gives an accent force) (+2 more)

### Community 87 - "Impeccable bolder & polish"
Cohesion: 0.22
Nodes (10): 'Bolder' during an open direction round means the Bolder hand-register steer (new-work), not this command, The skeleton test: strip the copy and see if hierarchy alone still says what the section is, Polish (impeccable reference), Polish is refinement, not concealed redesign, Quieter (impeccable reference), Quiet is not generic (luxury, not laziness), Routing / command guidance (impeccable reference), Shape (impeccable reference) (+2 more)

### Community 88 - "Impeccable DOM recovery (JS)"
Cohesion: 0.31
Nodes (11): acceptedDomAlreadyClean(), clearHandledWrapperReloadStamp(), deferredRecoverySuperseded(), ensureAcceptedDomClean(), findAcceptedRuntimeWrappers(), handledWrapperReloadKey(), reloadAfterMissingAcceptedDom(), restoreAcceptedDomFromSnapshot() (+3 more)

### Community 89 - "Catalog admin"
Cohesion: 0.18
Nodes (9): ProduccionEmbeddingAdmin, register, Configuración del admin de Django para el catálogo. Por ahora solo se registra…, register, Admin para el modelo personalizado de usuario. Adapta `UserAdmin` de Django a…, UsuarioAdmin, BaseUserAdmin, django_contrib (+1 more)

### Community 90 - "Auth screens & use cases"
Cohesion: 0.29
Nodes (11): CU-003: Iniciar sesión, CU-004: Cerrar sesión, Pantallas de autenticación (Login, Registro, Confirmación), A-01: Registro tradicional, A-03: Login con credenciales, A-08: Cerrar sesión, A-09: Middleware de rutas protegidas, Módulo 1 — Autenticación (Marcos) (+3 more)

### Community 91 - "Impeccable animate"
Cohesion: 0.24
Nodes (9): Avoid animating width/height/top/left/margins; use FLIP, transforms or grid; bound blur/filter/shadow; will-change only during known animation, Choose animated properties by what the transition communicates (continuity, focus/depth, reveal, material, state), Motion thesis: focal moment, continuity, feedback, budget, Every web animation needs a prefers-reduced-motion path with an intentional alternative, Timing bands 100–150 / 150–300 / 300–500 / 500–800 ms; exit faster than entrance; cubic-bezier(0.16, 1, 0.3, 1), Audit Health Score: 5 dimensions × 0–4 = /20 (A11y, Performance, Theming, Responsive, Implementation Integrity) with rating bands, A11y check: prefers-reduced-motion needs an intentional alternative; flag a global 0.01ms kill, Performance check: will-change is a targeted hint for known expensive animations, not a baseline (+1 more)

### Community 92 - "Impeccable asset producer"
Cohesion: 0.27
Nodes (9): Scope is sovereign: touch only the named target; no new colors, fonts, radii, shadows or primitives, Decision comp: one decision card → one north-star comp file at the card's declared `comp` path, Core rule: production cleanup, not new art direction, Output contract: one line per region `<id> <plate path> <WxH> <score%|unscored> <accepted|needs_parent_review|blocked> <note>` plus blockers and assumptions, Plate: a raster region regenerated at ≥1.5x the comp region size from the comp crop, with UI text and page chrome removed, Measured spec `.impeccable/build/spec.json` (from `impeccable comp-spec`) is the inventory, Background decision: isolated figure/object/line drawing → transparent PNG cutout with native alpha; photo/full-frame/texture → opaque, Two misses on one region: keep the better plate, mark `needs_parent_review`, name the drift (+1 more)

### Community 93 - "Account creation & bcrypt"
Cohesion: 0.29
Nodes (10): CU-001: Crear cuenta de usuario, RNF #12: hashear con bcrypt y cifrar datos sensibles (correos), RNF #2: contraseñas bcrypt y datos sensibles cifrados en reposo, Usuario (entidad unificada, AUTH_USER_MODEL), 22/08/2026 — Adopción de dj-rest-auth + django-allauth para autenticación, 22/08/2026 — Carácter ! permitido en la contraseña, 13/08/2026 — contraseña VARCHAR(50) → VARCHAR(128), 22/08/2026 — Datepicker de fecha de nacimiento: máximo hoy −13 años (+2 more)

### Community 94 - "Impeccable live setup"
Cohesion: 0.42
Nodes (9): Live config drift (configDrift.orphans), CSP detection (impeccable detect-csp), CSP patch shapes (null / append-arrays / append-string / middleware / meta-tag), Live inject framework adapters (SvelteKit / Nuxt / TanStack Start), pbakaus/impeccable framework fixtures (expected-after-patch), __impeccableLiveDev dev-only CSP allowance, .impeccable/live/inject-journal.json, .impeccable/live/config.json (+1 more)

### Community 96 - "Reset link validation"
Cohesion: 0.25
Nodes (7): EnlaceRestablecimientoInvalido, Exception, Señala un ``uid`` o token de restablecimiento inválido o vencido., Valida el enlace y persiste la nueva contraseña., RestablecerContrasenaSerializer, POST `/api/auth/password/reset/confirm/` — nueva contraseña. Valida el enlace…, RestablecerContrasenaView

### Community 98 - "CSRF token view"
Cohesion: 0.22
Nodes (6): CSRFTokenView, APIView, Entrega la cookie `csrftoken` para el frontend (SPA). Con…, Chequeo de disponibilidad de nombre de usuario en tiempo real (A-05). Devuelve…, UsernameDisponibleView, method_decorator

### Community 99 - "Lint & CI decisions"
Cohesion: 0.29
Nodes (8): F-06: ESLint + Prettier + Django linting, Q-06: CI (GitHub Actions) para lint/format, 15/09/2026 — El CI corre también en PRs apilados sobre ramas feat/**, 25/08/2026 — El lint solo corre en local; pendiente agregar CI, 18/09/2026 — Herramientas de review automáticas desactivadas y simplificación de openspec, 18/08/2026 — Prettier + ESLint + Husky en frontend (F-06), 18/08/2026 — Ruff como linter + formatter único (F-06), 10/09/2026 — Tests en CI, AGENTS.md con reglas de testing y skills, limpieza de archivos raíz

### Community 100 - "npm scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, format, format:check, lint, prepare, start

### Community 101 - "Impeccable ignore rules (JS)"
Cohesion: 0.52
Nodes (6): globToRegex(), matchesScope(), normalizeIgnoreRule(), normalizeIgnoreValue(), pageCandidates(), resolveDetectIgnores()

### Community 102 - "send_test_email command"
Cohesion: 0.29
Nodes (4): Command, BaseCommand, Comando de desarrollo: verifica la integración con Resend. Uso: python…, django_core_mail

### Community 103 - "Google OAuth decisions"
Cohesion: 0.33
Nodes (7): A-06: Google OAuth, 12/09/2026 — Contrato API centralizado y perfiles sociales inmutables al login, 11/09/2026 — El perfil de FilmAI prevalece sobre el perfil de Google, 26/08/2026 — Fix del 500 en Google OAuth: no releer request.body en populate_user, 26/08/2026 — Fix del id_token de un solo uso en el flujo Google de 2 pasos, 26/08/2026 — Google OAuth: login abre el selector y registro completa datos (flujos distintos), 22/08/2026 — Validación de campos Google antes de complete_social_login

### Community 104 - "Impeccable CLI script"
Cohesion: 0.60
Nodes (5): impeccable script, check_download(), fetch_url(), probe_ok(), setup_help()

### Community 105 - "UsuarioManager"
Cohesion: 0.47
Nodes (3): Manager que usa `correo` como identificador de autenticación.…, UsuarioManager, BaseUserManager

### Community 106 - "LoginSerializer"
Cohesion: 0.33
Nodes (3): LoginSerializer, Login por credenciales con errores específicos para cuentas inactivas., La activación por ``estado`` reemplaza el chequeo de allauth.

### Community 107 - "visualize.md (small group)"
Cohesion: 0.50
Nodes (5): DESIGN.md (project design system source), impeccable context (setup / capability report), Typeset (impeccable reference), Visualize: direction comps & asset production (impeccable reference), PRODUCT.md (captured product context)

### Community 108 - "middleware.ts (small group)"
Cohesion: 0.40
Nodes (3): config, PROTECTED_PREFIXES, ref_next_server

### Community 109 - "views.py (small group)"
Cohesion: 0.50
Nodes (3): LenientJWTCookieAuthentication, Variante que no revienta si la cookie JWT es inválida o está vencida.…, JWTCookieAuthentication

### Community 110 - "decisiones.md (small group)"
Cohesion: 0.50
Nodes (4): 26/08/2026 — CSRF para el access token en cookie httpOnly (JWT_AUTH_COOKIE_USE_CSRF), 26/08/2026 — Fix login Google vs registro + access token solo en cookie httpOnly, 25/08/2026 — Limpieza de storeTokens (quitar parámetro refresh), 22/08/2026 — Refresh token fuera de localStorage

## Ambiguous Edges - Review These
- `Diseño de email FilmAI (tabla role=presentation, dark #0d0d14/#161625, acento #e67e22, enlace #f5c518)` → `Lineamientos de UI`  [AMBIGUOUS]
  backend/templates/account/email/email_confirmation_message.html · relation: conceptually_related_to

## Knowledge Gaps
- **228 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+223 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 716 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **58 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Diseño de email FilmAI (tabla role=presentation, dark #0d0d14/#161625, acento #e67e22, enlace #f5c518)` and `Lineamientos de UI`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Usuario` connect `User model & repair command` to `Reset link validation`, `Confirm email tests`, `Password reset & throttles`, `Auth views & allauth flows`, `CSRF token view`, `User serializers & tests`, `LoginSerializer`, `AGENTS.md rules`, `allauth integration & user serializers`, `Default resources rollback tests`, `Chat & list models`, `Dev seed command`, `Catalog admin`, `Google OAuth adapter`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `Regla 6: .agents/skills/ es la única fuente de skills` connect `Conventional commits skill` to `Impeccable craft floor & color`, `explicar-al-implementar skill`, `AGENTS.md rules`, `Humanizer skill`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `AGENTS.md — Reglas para agentes en FilmAI` connect `AGENTS.md rules` to `README & project rules`, `CI workflow & pre-commit`, `Conventional commits skill`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `materializar()` (e.g. with `TMDBClientCache` and `tmdb_a_dominio()`) actually correct?**
  _`materializar()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `TMDBClient` (e.g. with `TMDBBadRequest` and `TMDBError`) actually correct?**
  _`TMDBClient` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `sync_catalogo_diaria()` (e.g. with `Ejemplo de diagrama: celery-beat → Redis DB 1 → celery-worker → TMDB (HTTP) / Postgres (SQL)` and `ProduccionAudiovisual`) actually correct?**
  _`sync_catalogo_diaria()` has 16 INFERRED edges - model-reasoned connections that need verification._