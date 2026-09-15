# Archive Report: Catalog On-Demand Materialization + Embedding Enqueue (C-04a)

## Result

- **Change**: `catalog-materialization`
- **Status**: success
- **Artifact mode**: hybrid (OpenSpec + SDD)
- **Archived on**: 2026-09-15
- **Branches**: `feat/c-04a-materializacion` (work units 1–4), `feat/c-04a-fase5` (work unit 5)
- **Merged commits**:
  - `920f296` — `Merge pull request #12 from MarcosDebona25/feat/c-04a-materializacion`
  - `bb6739a` — `Merge pull request #13 from MarcosDebona25/feat/c-04a-fase5`

## Final State

C-04a is implemented, tested, reviewed and merged into `main`. `materializar(id_tmdb, tipo_tmdb)` is the single write path into `ProduccionAudiovisual`: it resolves the row by `(id_tmdb, tipo)` with savepoint-isolated race recovery, enriches it from TMDB (detail + credits + keywords, all Redis-cached) when new or incomplete, creates a `pending` `ProduccionEmbedding` and enqueues `generar_embedding`. `MovieDetailView` and `TVDetailView` call it as a side effect without altering the C-03 passthrough contract.

The change also advanced the minimum embedding infrastructure originally scoped to B-06: Celery app wiring, the `celery-worker` service, the `pgvector/pgvector:pg16` image, the `ProduccionEmbedding` model with its HNSW index, the canonical-text builder and the idempotent `generar_embedding` task. Only `generar_vector()` remains a stub, so every embedding currently ends in `failed` by design — without affecting catalog visibility.

**This unblocks Módulo 3 (Listas, Marcos)**, which depends on the materialization helper to reference catalog rows.

## Verification

- **Verdict**: PASS
- **Tasks**: 39/39 complete (all five work units)
- **Tests**: 172 passed (full backend suite; 94 in the `catalogo` app)
- **Ruff check**: clean
- **Ruff format**: clean
- **CI**: green on both PRs and on `main` after each merge
- **Success criteria**: all eight from `proposal.md` verified, including the two that needed a live runtime check (one row under real concurrency; production visible with a failed embedding)
- **Open issues**: two non-blocking items raised in review and accepted as-is, both recovered by the C-04b backfill — a broker outage during `.delay()` can leave an embedding permanently `pending`, and the incompleteness criterion only inspects `titulo` (documented in the spec as a known limitation)

## Deviations from the Proposal

- The review budget (400 lines) forced a two-PR chain instead of the five originally suggested in `tasks.md`; work units 1–4 shipped together once they proved inseparable in practice.
- `catalogo/service.py` was moved to `catalogo/services/tmdb.py`, which the proposal did not anticipate: creating the `services/` package would otherwise have left both coexisting.
- `entrypoint.sh` had to be corrected to the standard `exec "$@"` pattern before the worker could run its own `command`.
- `pgvector/pgvector:pg16-alpine` does not exist; the Debian image was used, which required recreating the `pgdata` volume because of the musl → glibc collation change.

## Spec Sync and Archive

- Created canonical capability spec at `openspec/specs/catalog-materialization/spec.md`.
- Created canonical capability spec at `openspec/specs/embedding-infrastructure/spec.md`.
- Extended `openspec/specs/tmdb-endpoints/spec.md` with the detail-view materialization side effect (modified capability; the existing passthrough requirements are unchanged).
- Moved change directory to `openspec/changes/archive/2026-09-15-catalog-materialization/`.

## Follow-ups

- **C-04b** — scheduled sync + embedding backfill; recovers `pending`/`failed` rows and regenerates on `source_hash` / `model_version` change.
- **B-06** — replace `generar_vector()` with the real Ollama/`bge-m3` client and add `buscar_semantico`.
- **Módulo 3** — now unblocked: `from catalogo.services.materialization import materializar`.
