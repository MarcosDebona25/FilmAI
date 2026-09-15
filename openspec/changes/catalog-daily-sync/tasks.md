# Tasks: Daily Catalog Sync + Embedding Backfill (C-04b)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~520-620 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR1 → PR2 → PR3 |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked on `feat/c-04b-sync-diaria` |

Decision needed before apply: No — the four open decisions were resolved with
the repo owner on 15/09/2026 (see `design.md` → Architecture Decisions).

> Lesson carried from C-04a: the review budget was ignored until the branch had
> already grown to 2.4× it, forcing a mid-flight split into stacked PRs. Here
> the split is planned up front. The CI now runs on PRs targeting `feat/**`
> (PR #16), so a stacked PR is properly gated.

### Suggested Work Units

| Unit | Goal | Likely PR | Est. lines | Focused test command | Rollback boundary |
|------|------|-----------|-----------:|----------------------|-------------------|
| 1 | `on_commit` + `fecha_enriquecimiento` + `forzar` (changes to existing C-04a code) | PR 1 | ~180 | `docker compose exec -T backend python manage.py test catalogo.tests.MaterializacionIdempotenteTests catalogo.tests.MaterializacionFrescuraTests` | `migrate catalogo <prev>`, then revert model + materialization |
| 2 | `celery-beat` service + schedule + `sync_catalogo_diaria` | PR 2 | ~230 | `docker compose exec -T backend python manage.py test catalogo.tests.SyncCatalogoTests` | Revert the compose service and the task; unit 1 stays useful on its own |
| 3 | `backfill_embeddings` + docs + spec sync | PR 3 | ~180 | `docker compose exec -T backend python manage.py test catalogo` | Revert the task; the schedule keeps running the sync |

## Phase 1: Changes to existing C-04a code

> Goes first and alone: it touches tests that already pass, so any regression is
> unambiguous. Nothing here depends on the sync existing.

- [ ] 1.1 RED: move the two enqueue assertions (`MaterializacionPeliculaTests.test_crea_el_embedding_pendiente_y_lo_encola_una_sola_vez`, `MaterializacionIdempotenteTests.test_no_reencola_si_el_embedding_ya_existia`) to `captureOnCommitCallbacks(execute=True)` — they must fail first, proving the callback is what now carries the enqueue
- [ ] 1.2 GREEN: wrap the enqueue in `transaction.on_commit()` in `_encolar_embedding`; update its docstring, which currently explains why the direct `.delay()` was correct
- [ ] 1.3 RED: add `MaterializacionFrescuraTests` — `fecha_enriquecimiento is None` ⇒ needs enrichment; set to now ⇒ does not; set beyond `_DIAS_FRESCURA` ⇒ does
- [ ] 1.4 GREEN: add `fecha_enriquecimiento` to `ProduccionAudiovisual`; `makemigrations catalogo`; confirm the migration is additive and nullable
- [ ] 1.5 GREEN: rewrite `_necesita_enriquecimiento()` against `fecha_enriquecimiento`; set the timestamp inside `_enriquecer()`, in the same `save()`
- [ ] 1.6 RED: add a case asserting `materializar(..., forzar=True)` re-enriches a row the criterion would have skipped, and that `forzar=False` still skips it
- [ ] 1.7 GREEN: add the `forzar` parameter to `materializar()`
- [ ] 1.8 Update `openspec/specs/catalog-materialization/spec.md`: the "Incompleteness criterion" requirement now describes `fecha_enriquecimiento` and the refresh window, and the known limitation about `titulo` is removed — it no longer applies
- [ ] 1.9 `docker compose exec -T backend python manage.py test catalogo` — all green; `ruff format . && ruff check .`

## Phase 2: Scheduler and daily sync

- [ ] 2.1 Add the `celery-beat` service to `docker-compose.yml` (`RUN_MIGRATIONS: "false"`, single replica); add `CELERY_BEAT_SCHEDULE` and an explicit `CELERY_TIMEZONE` to settings
- [ ] 2.2 Verify the scheduler actually fires: temporarily shorten the interval, `docker compose logs -f celery-beat`, confirm the worker receives the task, then restore 03:00
- [ ] 2.3 RED: add `SyncCatalogoTests` with listing fixtures for trending (mixed `movie`/`tv`/`person`), now_playing and discover → asserts `materializar` is called once per supported item
- [ ] 2.4 RED: add a case asserting `person` entries (and any unsupported `media_type`) are skipped without raising
- [ ] 2.5 RED: add a case asserting one failing item does not abort the run — the rest are still processed and the failure is counted
- [ ] 2.6 RED: add a case asserting the returned statistics (`nuevas`, `actualizadas`, `omitidas`, `errores`) reflect what happened
- [ ] 2.7 GREEN: implement `sync_catalogo_diaria()` in `backend/catalogo/tasks.py`
- [ ] 2.8 RED: **acceptance criterion, tested directly** — rate and review a production, run the sync, assert the rating and review survive untouched
- [ ] 2.9 `docker compose exec -T backend python manage.py test catalogo` — all green; `ruff format . && ruff check .`

## Phase 3: Backfill, documentation and verification

- [ ] 3.1 RED: add `BackfillEmbeddingsTests` — `pending` and `failed` rows are re-enqueued
- [ ] 3.2 RED: add a case where `ready` with a matching `source_hash` and `model_version` is left alone, and one where a changed hash causes re-enqueue
- [ ] 3.3 RED: add a case asserting `limite` caps how many rows are processed in one run
- [ ] 3.4 GREEN: implement `backfill_embeddings(limite=...)`
- [ ] 3.5 Add the beat entry for the backfill; `.env.example` and `README.md` updated to the 6-service topology
- [ ] 3.6 Create the canonical spec `openspec/specs/catalog-daily-sync/spec.md` (Given/When/Then, RFC 2119)
- [ ] 3.7 Record the declared timezone in `docs/decisiones.md` (the four design decisions of 15/09/2026 are already recorded); update `docs/05_Plan_de_Desarrollo.md` (mark C-04b done)
- [ ] 3.8 **Contrast the listing fixtures against the real API** — the shapes assumed in the tests must match what TMDB actually returns. In C-04a a fabricated `job: "Director"` kept 172 tests green while no series had a director in production
- [ ] 3.9 End-to-end verification: force a beat run, confirm rows and statistics; run it twice and confirm no duplicates; `docker compose exec -T backend python manage.py test` full suite; `ruff format --check . && ruff check .`
