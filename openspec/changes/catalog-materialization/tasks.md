# Tasks: Catalog On-Demand Materialization + Embedding Enqueue (C-04a)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1050-1250 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 → PR2 → PR3 → PR4 → PR5 |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Est. lines | Focused test command | Rollback boundary |
|------|------|-----------|-----------:|----------------------|-------------------|
| 1 | Celery app wiring + docker-compose (`pgvector` image + `celery-worker`) + `requirements.txt` + `.env.example` + docs | PR 1 | ~150 | `docker compose exec -T backend python manage.py shell -c "from filmai.celery import app; print(app)"` | revert `celery.py`, `__init__.py`, settings, compose, requirements, env |
| 2 | `ProduccionEmbedding` model + migration (`VectorExtension`) + admin | PR 2 | ~210 | `docker compose exec -T backend python manage.py test catalogo.tests.ProduccionEmbeddingModelTest` | `migrate catalogo <prev>` then revert model/admin/migration file |
| 3 | `adapter.py` + `embeddings.py` (canonical text, hash, provider stub) | PR 3 | ~200 | `docker compose exec -T backend python manage.py test catalogo.tests.AdapterTest catalogo.tests.EmbeddingTextTest` | revert both service files + tests |
| 4 | `client.py`/`cache.py` credits methods + `tasks.py` (`generar_embedding`) | PR 4 | ~260 | `docker compose exec -T backend python manage.py test catalogo.tests.TMDBCreditsTest catalogo.tests.GenerarEmbeddingTaskTest` | revert `tasks.py`; credits methods are additive and can stay even if task is reverted |
| 5 | `materialization.py` + view wiring + concurrency tests | PR 5 | ~280 | `docker compose exec -T backend python manage.py test catalogo` | revert `materialization.py` + view changes; model/task from PR2-4 stay inert without a caller |

## Phase 1: Celery infrastructure

- [ ] 1.1 RED: add `CeleryAppTest` asserting `filmai.celery.app` is a `Celery` instance named `"filmai"` and that `filmai.celery_app` is importable from `filmai`
- [ ] 1.2 GREEN: create `backend/filmai/celery.py`, update `backend/filmai/__init__.py` to import `celery_app`
- [ ] 1.3 Add `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`/serializer settings to `backend/filmai/settings.py`, reading from `.env` via `decouple.config`
- [x] 1.4 Update `docker-compose.yml`: swap `db` image to `pgvector/pgvector:pg16-alpine`; add `celery-worker` service (`command: celery -A filmai worker -l info`)
- [ ] 1.5 Add `pgvector>=0.3,<0.4` to `backend/requirements.txt`
- [ ] 1.6 Add `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` to `.env.example`; update `README.md` (5-service topology)
- [ ] 1.7 Record the "adelantar infraestructura mínima de embeddings" decision + `pgvector` vs `django-pgvector` correction in `docs/decisiones.md`
- [ ] 1.8 `docker compose up --build -d db redis backend celery-worker` — confirm all healthy, `docker compose exec db psql -c "\dx"` (extension not yet created, just confirms image works)

## Phase 2: `ProduccionEmbedding` model

- [ ] 2.1 RED: add `ProduccionEmbeddingModelTest` — default `estado="pending"`, `OneToOneField` rejects a second embedding for the same `produccion`, `ck_embedding_ready_requiere_vector` rejects `estado="ready"` with `vector=None`
- [ ] 2.2 GREEN: add `EstadoEmbedding` + `ProduccionEmbedding` to `backend/catalogo/models.py` (`VectorField(1024)`, `HnswIndex`, check constraint)
- [ ] 2.3 `python manage.py makemigrations catalogo`; edit the generated migration to prepend `VectorExtension()` from `pgvector.django`
- [ ] 2.4 `docker compose exec backend python manage.py migrate catalogo` — confirm `CREATE EXTENSION vector` succeeds against `pgvector/pgvector:pg16-alpine`
- [ ] 2.5 (optional, skip if PR nears budget) register `ProduccionEmbedding` in `backend/catalogo/admin.py` (`list_display`: producción, estado, model_version, fecha_actualizacion)
- [ ] 2.6 `python manage.py test catalogo` — all green; `ruff format . && ruff check .`

## Phase 3: Adapter + embedding text

- [ ] 3.1 RED: add `AdapterTest` — `tmdb_a_dominio("movie") == TipoProduccion.PELICULA`, `"tv" == SERIE`, unknown value raises `ValueError`; `dominio_a_tmdb` round-trips
- [ ] 3.2 GREEN: create `backend/catalogo/services/adapter.py`
- [ ] 3.3 RED: add `EmbeddingTextTest` — `construir_texto_canonico` sorts `generos`/`directores`/`reparto`/`keywords` alphabetically, tolerates empty/whitespace entries, produces the `Title/Genres/Directors/Cast/Keywords/Synopsis` label order; `calcular_source_hash` is deterministic and content-sensitive
- [ ] 3.4 RED: add a case asserting `generar_vector(...)` raises `NotImplementedError` (documents the stub contract)
- [ ] 3.5 GREEN: create `backend/catalogo/services/embeddings.py` (`construir_texto_canonico`, `calcular_source_hash`, `EmbeddingProviderError`, `generar_vector` stub, `MODEL_VERSION`)
- [ ] 3.6 `python manage.py test catalogo` — all green; `ruff format . && ruff check .`

## Phase 4: TMDB credits + Celery task

- [ ] 4.1 RED: add `TMDBCreditsTest` (`httpx.MockTransport`) — `TMDBClient.get_movie_credits`/`get_tv_credits` hit `/movie/{id}/credits`/`/tv/{id}/credits` and reuse the existing retry/error-mapping path
- [ ] 4.2 GREEN: add `get_movie_credits`/`get_tv_credits` to `backend/catalogo/client.py`
- [ ] 4.3 RED: add cache-layer test asserting `TMDBClientCache.get_movie_credits`/`get_tv_credits` are cached under new `ENDPOINT_TTLS` keys
- [ ] 4.4 GREEN: add wrapper methods + TTL entries to `backend/catalogo/cache.py`
- [ ] 4.5 RED: add `GenerarEmbeddingTaskTest` — missing `ProduccionEmbedding` row → no-op; `estado="ready"` + matching hash/version → provider not called; `estado="pending"` → claimed, provider mocked to return a vector → `ready` + `source_hash`/`model_version` persisted
- [ ] 4.6 RED: add failure case — provider mocked to raise (and separately, the real stub's `NotImplementedError`) → `estado="failed"`, no exception propagates out of the task
- [ ] 4.7 RED: add concurrent-claim case — pre-set `estado="processing"` → task call is a no-op (`claimed == 0`, provider not called)
- [ ] 4.8 GREEN: create `backend/catalogo/tasks.py` with `generar_embedding`
- [ ] 4.9 `python manage.py test catalogo` — all green; `ruff format . && ruff check .`

## Phase 5: Materialization + view wiring

- [ ] 5.1 RED: add `MaterializationRaceTest` — mock `ProduccionAudiovisual.objects.create` to raise `IntegrityError`; assert `materializar()` falls back to `.get()` and returns the existing row without raising
- [ ] 5.2 RED: add `MaterializationEnrichmentTest` — mock `get_catalog_service()` (detail+credits+keywords fixtures for both `movie` and `tv`) → assert every mapped field (see design.md table), `ProduccionEmbedding(estado=pending)` created, `generar_embedding.delay` called once with the new `produccion.id`
- [ ] 5.3 RED: add a case where the row already exists and is complete (`titulo` set) → no TMDB calls made, no duplicate `ProduccionEmbedding`, no re-enqueue
- [ ] 5.4 GREEN: create `backend/catalogo/services/materialization.py` (`materializar`, `_obtener_o_crear`, `_enriquecer`, `_encolar_embedding`)
- [ ] 5.5 RED: add `MovieDetailViewMaterializationTest`/`TVDetailViewMaterializationTest` (`APIClient`, mocked `get_catalog_service`) — GET response body is unchanged TMDB passthrough, and a `ProduccionAudiovisual` row now exists for that `(id_tmdb, tipo)`
- [ ] 5.6 GREEN: wire `materializar(id_tmdb, tipo_tmdb)` into `MovieDetailView.get`/`TVDetailView.get` in `backend/catalogo/views.py`
- [ ] 5.7 Best-effort (not a merge gate): add `MaterializationConcurrencyTransactionTest(TransactionTestCase)` with `threading.Barrier` — two threads materializing the same `(id_tmdb, tipo)` end with exactly one row
- [ ] 5.8 Update `docs/decisiones.md` with the final acceptance-criteria confirmation (unicidad, concurrencia, idempotencia, fallo→failed)
- [ ] 5.9 `docker compose exec -T backend python manage.py test catalogo` — all green; `ruff format . && ruff check .`; manual smoke: `docker compose up -d`, `curl localhost:8000/api/catalogo/movie/550/` twice, confirm one row + one `pending`/`failed` embedding via `python manage.py shell`
