# Apply Progress: Catalog On-Demand Materialization + Embedding Enqueue (C-04a)

## Status

- **Change**: `catalog-materialization`
- **Mode**: Strict TDD
- **Work units**: 5 of 5 complete
- **Progress**: 39/39 tasks complete
- **Delivery**: two stacked PRs — #12 (work units 1–4) and #13 (work unit 5)

> Consolidated at archive time from `tasks.md`, the branch history and the
> recorded test runs; this change was implemented in a single continuous
> effort across 13–15/09/2026 rather than resumed from a running progress file.

## Completed Tasks

### Work unit 1 — Celery infrastructure (1.1–1.8)

- [x] `filmai/celery.py` + `filmai/__init__.py` exporting `celery_app`, driven by `CeleryAppTests` (4 tests).
- [x] Broker/result/serializer settings read from `.env` via `decouple.config`.
- [x] `docker-compose.yml`: `db` → `pgvector/pgvector:pg16`, new `celery-worker` service.
- [x] `pgvector>=0.3,<0.5` added to `requirements.txt`; `.env.example` and `README.md` updated to the 5-service topology.
- [x] `entrypoint.sh` moved to the standard `exec "$@"` pattern with a `RUN_MIGRATIONS` flag, so each service's `command:` is honoured and only one container migrates.

### Work unit 2 — `ProduccionEmbedding` model (2.1–2.6)

- [x] `EstadoEmbedding` + `ProduccionEmbedding` with `VectorField(1024)`, `HnswIndex(vector_cosine_ops)` and the `ck_embedding_ready_requiere_vector` check constraint.
- [x] Migration `0004` hand-edited to prepend `VectorExtension()`; `makemigrations` cannot infer it.
- [x] Registered in the admin with `vector` excluded.

### Work unit 3 — Adapter + embedding text (3.1–3.6)

- [x] `services/adapter.py`: the single `movie ↔ pelicula`, `tv ↔ serie` conversion; `"all"` raises `ValueError`.
- [x] `services/embeddings.py`: canonical text, `calcular_source_hash`, `MODEL_VERSION`, and the documented `generar_vector()` stub.
- [x] `catalogo/service.py` moved to `catalogo/services/tmdb.py` so `service.py` and `services/` do not coexist.

### Work unit 4 — TMDB credits + Celery task (4.1–4.10)

- [x] `get_credits(id_tmdb, tipo)` on client and cache (single method mirroring `get_keywords`), with a 24 h TTL.
- [x] `catalogo/tasks.py::generar_embedding` with three defenses: hash/version short-circuit, atomic claim, provider call outside any transaction with failure → `failed`.
- [x] Worker auto-reload via `watchdog[watchmedo]`: Celery does not reload code, and editing an existing task body runs the stale version silently.

### Work unit 5 — Materialization + view wiring (5.1–5.9)

- [x] `services/materialization.py`: `materializar`, `_buscar_produccion`, `_obtener_o_crear`, `_necesita_enriquecimiento`, `_enriquecer`, `_mapear`, `_extraer_keywords`, `_duracion_de_episodio`, `_encolar_embedding`.
- [x] `MovieDetailView`/`TVDetailView` call `_materializar_sin_interrumpir()` after resolving the response.
- [x] `EndpointIntegrationTest` neutralizes materialization in `setUp`: it covers the C-03 HTTP contract and runs without a database.
- [x] Best-effort real-concurrency test with `TransactionTestCase` + `threading.Barrier`.

## TDD Cycle Evidence

| Unit | Test file | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|-----|-------|-------------|----------|
| 1 | `backend/filmai/tests.py` | Unit | ✅ Import failure before `celery.py` | ✅ 4 tests passed | ✅ App name, config source, autodiscovery, re-export | ✅ Ruff clean |
| 2 | `backend/catalogo/tests.py` | Integration (DB) | ✅ Import failure before the model; migration failed with `type "vector" does not exist` until `VectorExtension()` was prepended | ✅ 6 tests passed | ✅ Defaults, OneToOne uniqueness, check constraint both ways, cascade | ✅ Ruff clean |
| 3 | `backend/catalogo/tests.py` | Unit | ✅ Import failure before both service modules | ✅ 12 tests passed | ✅ Both directions of the adapter, `"all"` rejected, array normalization, hash determinism, stub contract | ✅ Ruff clean |
| 4 | `backend/catalogo/tests.py` | Unit + Integration | ✅ Missing `get_credits`; task import failure | ✅ 10 tests passed | ✅ Missing row, ready+same hash, pending→ready, provider failure, already-claimed | ✅ Ruff clean |
| 5 | `backend/catalogo/tests.py` | Integration (DB) | ✅ `ModuleNotFoundError: catalogo.services.materialization`; then 4 view tests failing on a missing row and a missing `materializar` attribute | ✅ 23 tests passed | ✅ Movie vs TV mapping, keywords key difference, empty date, cast truncation, idempotency, race both ways, view wiring, swallowed failure | ✅ Ruff clean; shared patches extracted to `_ParchesDeMaterializacion` |

## Work Unit Evidence

| Evidence | Result |
|----------|--------|
| Focused test command and exact result | `docker compose exec -T backend python manage.py test catalogo` — exit 0, **94 tests passed** |
| Full suite | `docker compose exec -T backend python manage.py test` — exit 0, **172 tests passed** (149 before this change) |
| Real-concurrency stability | `MaterializacionConcurrenciaTests` run 5 consecutive times — 5/5 OK |
| Runtime harness scenario | Two materializations of `(155, pelicula)` through the real broker: one row, one embedding, task enqueued once; worker consumed it and the B-06 stub left it `failed` without crashing |
| Rollback boundary | Revert `services/materialization.py` and the view wiring; the model and task from units 2–4 stay inert without a caller |

## Verification

- Full suite: **172/172 passed**
- `ruff check .`: **All checks passed!**
- `ruff format --check .`: **64 files already formatted**
- CI on both PRs and on `main` after each merge: **green**

## Remaining Tasks

None. All five work units merged to `main`.
