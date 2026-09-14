# Proposal: Catalog On-Demand Materialization + Embedding Enqueue (C-04a, CU-021)

## Intent

Every production served by catalog discovery (C-03, live TMDB) or opened in
detail must be persisted globally in `ProduccionAudiovisual` so it can be
rated, listed (Módulo 3), and made semantically searchable (B-06). Today
nothing persists: `catalogo/services/` does not exist, there is no
`ProduccionEmbedding`, and no Celery app is wired despite `celery` already
being a dependency. This change adds the materialization helper (CU-021) and
advances the **minimum** embedding infrastructure needed to enqueue work
without blocking the request — the actual embedding provider (Ollama/bge-m3)
stays a documented stub for B-06 (Marcos) to implement later.

## Scope

### In Scope
- `catalogo/services/adapter.py`: single `movie ↔ pelicula`, `tv ↔ serie` type adapter
- `catalogo/services/materialization.py`: `materializar(id_tmdb, tipo_tmdb)` —
  get-or-create by `(id_tmdb, tipo)`, concurrency-safe, TMDB enrichment
  (detail + credits + keywords), embedding row creation + enqueue
- New `ProduccionEmbedding` model (`pending|processing|ready|failed`) +
  migration enabling the `vector` Postgres extension
- Two additive TMDB client/cache methods: `get_movie_credits`/`get_tv_credits`
  (cast/crew are absent from the existing detail endpoints)
- `catalogo/services/embeddings.py`: canonical-text builder, `source_hash`,
  and a documented `generar_vector()` stub (raises `NotImplementedError`)
- `catalogo/tasks.py`: `generar_embedding` Celery task with real
  claim/lease idempotency (`pending`/`failed` → `processing`), hash/version
  short-circuit, and failure handling — only the provider call is stubbed
- Minimal Celery app wiring (`filmai/celery.py`, `filmai/__init__.py`,
  `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` settings) and a `celery-worker`
  docker-compose service
- `db` image swapped to `pgvector/pgvector:pg16-alpine` (same Postgres 16
  binary, adds the `vector` extension files)
- Wiring `materializar()` as a side effect of `MovieDetailView`/`TVDetailView`
  (C-03), without changing their existing passthrough response contract
- `.env.example`, `README.md`, `docs/decisiones.md` updates

### Out of Scope
- The real embedding provider (Ollama client, `bge-m3` model, `ollama`
  docker-compose service, `OLLAMA_BASE_URL`/`EMBEDDING_MODEL` env vars) — 100%
  B-06 (Marcos)
- `celery-beat` / scheduled sync (`sync_catalogo_diaria`, backfill) — C-04b
- `buscar_semantico` retrieval query — B-06
- Listas (`Tiene`) calling the materialization helper — Módulo 3 (Marcos),
  already documented as a hard dependency on this change
- DTO/serializer mapping for catalog responses (still raw TMDB passthrough,
  per C-03's own out-of-scope decision)

## Capabilities

### New Capabilities
- `catalog-materialization`: on-demand, concurrency-safe persistence of
  `ProduccionAudiovisual` + embedding enqueue
- `embedding-infrastructure`: minimal Celery + pgvector plumbing with a
  stubbed provider, ready for B-06 to plug in without refactoring

### Modified Capabilities
- `tmdb-endpoints` (C-03): `MovieDetailView`/`TVDetailView` now trigger
  materialization as a side effect; response body unchanged

## Approach

`materializar()` never calls TMDB or the embedding provider inside an open
write transaction (decision 25/08/2026). It: (1) tries `create()` inside
`atomic()`, falls back to `get()` on `IntegrityError` (race-safe); (2) if the
row is new or still incomplete, enriches it synchronously from
`TMDBClientCache` (detail + credits + keywords — all Redis-cached, so repeat
calls are cheap); (3) `get_or_create`s a `pending` `ProduccionEmbedding` and
calls `generar_embedding.delay(produccion_id)`. The Celery task claims the
row atomically (`update()` conditioned on current `estado`), builds the
canonical text, computes `source_hash`, short-circuits if `ready` with the
same hash/version, calls the stub provider, and marks `failed` on any
exception — never leaving the row stuck or blocking the caller.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/catalogo/services/adapter.py` | New | TMDB ↔ dominio type mapping |
| `backend/catalogo/services/materialization.py` | New | `materializar()` helper |
| `backend/catalogo/services/embeddings.py` | New | canonical text, hash, provider stub |
| `backend/catalogo/models.py` | Modified | `ProduccionEmbedding` + `EstadoEmbedding` |
| `backend/catalogo/migrations/` | New | `VectorExtension()` + `CreateModel` |
| `backend/catalogo/tasks.py` | New | `generar_embedding` Celery task |
| `backend/catalogo/client.py` | Modified | `get_movie_credits`/`get_tv_credits` (additive) |
| `backend/catalogo/cache.py` | Modified | cached wrappers for credits (additive) |
| `backend/catalogo/views.py` | Modified | detail views call `materializar()` |
| `backend/catalogo/admin.py` | Modified | register `ProduccionEmbedding` (dev visibility) |
| `backend/filmai/celery.py` | New | Celery app |
| `backend/filmai/__init__.py` | Modified | import `celery_app` |
| `backend/filmai/settings.py` | Modified | `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` |
| `docker-compose.yml` | Modified | `pgvector/pgvector:pg16-alpine`, `celery-worker` service |
| `backend/requirements.txt` | Modified | `pgvector` |
| `.env.example` | Modified | Celery broker/result vars |
| `README.md` | Modified | 5-service topology, `ProduccionEmbedding` no longer "planned" |
| `docs/decisiones.md` | Modified | record decisions listed under Risks |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| TMDB detail endpoints lack cast/crew | High (confirmed) | Additive `get_movie_credits`/`get_tv_credits`, no change to existing C-01/C-02 contracts |
| `pgvector/pgvector:pg16-alpine` vs `postgres:16-alpine` volume compatibility | Low–Med | Same upstream Postgres 16 binary/data format, only extra extension files; verify in dev before merging, documented rollback |
| `pgvector` vs `django-pgvector` package naming in existing docs | Med | Use `pgvector` (pgvector-python), which ships `pgvector.django`; correct the docs in this change (see design) |
| Real DB-race concurrency test flakiness (`TransactionTestCase` + threads) | Med | Required test is a deterministic mocked-`IntegrityError` unit test; real-thread test is best-effort, not a merge gate (confirmed with repo owner 14/09/2026) |
| Wiring `materializar()` into detail views adds sync DB+TMDB latency per request | Med | Bounded by `TMDBClientCache` TTLs (24h); acceptable for a detail-page open |
| Stub provider always fails, so "ready" success path is untestable end-to-end | Low | Unit-test success branch by mocking `generar_vector`; document as expected until B-06 |
| Celery worker misconfiguration (wrong broker DB) collides with TMDB Redis cache | Low | Separate Redis logical DBs: cache `/0`, broker `/1`, results `/2` |

## Rollback Plan

Each PR in the chain (see `tasks.md`) has an isolated rollback boundary:
revert `catalogo/services/`, `tasks.py`, and the view wiring without touching
the model; if the model/migration must be rolled back, `migrate catalogo
000<N-1>` before reverting — no data has been written to `vector` columns
until B-06 lands, so this is non-destructive. Reverting the `db` image swap
requires no volume changes since the underlying Postgres 16 data format is
unchanged (see design). Celery wiring can be reverted independently; `.delay()`
calls simply won't be queued if the app import is removed (no crash, since
`generar_embedding` becomes unreachable code, not a broken import, as long as
the view/service call is reverted in the same rollback).

## Dependencies

- C-01 `TMDBClient`, C-02 `TMDBClientCache` (on `main`)
- C-03 `MovieDetailView`/`TVDetailView`, `get_catalog_service()` (on `main`)
- `uq_produccion_tmdb_tipo` constraint (already on `main`)

## Success Criteria

- [ ] `materializar()` is atomic and never creates duplicate rows for the same `(id_tmdb, tipo)`
- [ ] The production persists even when the embedding task fails
- [ ] Two concurrent materialization attempts return the same row
- [ ] `ProduccionEmbedding.produccion_id` is enforced UNIQUE at the DB level
- [ ] `generar_embedding` is idempotent: same hash + `model_version` + `ready` ⇒ no-op, no extra provider calls
- [ ] Provider stub failure ⇒ `estado="failed"`, production remains visible via catalog/detail endpoints
- [ ] `docker compose up` brings up 5 healthy services with no manual steps
- [ ] Tests pass via `python manage.py test` (no real network, no real Ollama)
