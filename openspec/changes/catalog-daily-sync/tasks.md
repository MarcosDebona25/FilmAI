# Tasks: Daily Catalog Sync + Embedding Backfill (C-04b)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~660-780 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR1 → PR2 → PR3 → PR4 |
| Delivery strategy | ask-on-risk |
| Chain strategy | independent PRs off `main` — the SDD merged first (#18, 16/09/2026), so each unit lands on its own without stacking |

Decision needed before apply: No — the five open decisions were resolved with
the repo owner on 15/09/2026 (see `design.md` → Architecture Decisions).

> Lesson carried from C-04a: the review budget was ignored until the branch had
> already grown to 2.4× it, forcing a mid-flight split into stacked PRs. Here
> the split is planned up front. The CI now runs on PRs targeting `feat/**`
> (PR #16), so a stacked PR is properly gated.

### Suggested Work Units

| Unit | Goal | Likely PR | Est. lines | Focused test command | Rollback boundary |
|------|------|-----------|-----------:|----------------------|-------------------|
| 1 | `on_commit` + `fecha_enriquecimiento` + `forzar` (changes to existing C-04a code) | PR 1 | ~180 | `docker compose exec -T backend python manage.py test catalogo.tests.MaterializacionIdempotenteTests catalogo.tests.MaterializacionFrescuraTests` | `migrate catalogo <prev>`, then revert model + materialization |
| 2 | `celery-beat` service + schedule + the discovery pass of `sync_catalogo_diaria` (tasks 2.1-2.7) | PR 2 | ~230 | `docker compose exec -T backend python manage.py test catalogo.tests.SyncCatalogoTests` | Revert the compose service and the task; unit 1 stays useful on its own |
| 3 | `get_changes` on client/cache + the refresh pass (tasks 2.8-2.14) | PR 3 | ~140 | `docker compose exec -T backend python manage.py test catalogo.tests.TMDBChangesTest catalogo.tests.IdsCambiadosTests` | Revert the refresh pass; discovery keeps working and the safety-net window still catches stale rows eventually |
| 4 | `backfill_embeddings` + docs + spec sync | PR 4 | ~180 | `docker compose exec -T backend python manage.py test catalogo` | Revert the task; the schedule keeps running the sync |

> Units 2 and 3 are both inside Phase 2 but ship separately: adding the changes
> API pushed the phase to ~370 lines, close enough to the 400-line budget that
> one more discovery brings it over. Splitting at the seam between "grow the
> corpus" and "keep it fresh" also keeps each PR reviewable as one idea.

## Phase 1: Changes to existing C-04a code

> Goes first and alone: it touches tests that already pass, so any regression is
> unambiguous. Nothing here depends on the sync existing.

- [x] 1.1 RED: add `test_el_encolado_espera_a_que_la_transaccion_se_confirme` — inside `captureOnCommitCallbacks(execute=False)`, `delay` must NOT have been called yet and exactly one callback must be registered. *Corrected at apply time:* the original wording ("wrap the two existing assertions, they must fail first") was not a RED — a direct `.delay()` still fires inside the capture block, so those tests passed both before and after. The existing enqueue assertions (**four**, not two: the two in the materialization tests and the two in `VistasDeDetalleMaterializanTests`) get `execute=True` so they keep asserting what they always did once the callback carries the enqueue
- [x] 1.2 GREEN: wrap the enqueue in `transaction.on_commit()` in `_encolar_embedding`; docstring rewritten — it used to explain why the direct `.delay()` was correct
- [x] 1.3 RED: add `MaterializacionFrescuraTests` — `fecha_enriquecimiento is None` ⇒ needs enrichment; set to now ⇒ does not; set beyond `_DIAS_FRESCURA` ⇒ does
- [x] 1.4 GREEN: add `fecha_enriquecimiento` to `ProduccionAudiovisual`; `makemigrations catalogo`; confirm the migration is additive and nullable
- [x] 1.5 GREEN: rewrite `_necesita_enriquecimiento()` against `fecha_enriquecimiento`; set the timestamp inside `_enriquecer()`, in the same `save()`
- [x] 1.6 RED: add a case asserting `materializar(..., forzar=True)` re-enriches a row the criterion would have skipped, and that `forzar=False` still skips it
- [x] 1.7 GREEN: add the `forzar` parameter to `materializar()`
- [x] 1.8 Update `openspec/specs/catalog-materialization/spec.md`: the "Incompleteness criterion" requirement now describes `fecha_enriquecimiento` and the refresh window, and the known limitation about `titulo` is removed — it no longer applies
- [x] 1.9 `docker compose exec -T backend python manage.py test catalogo` — all green; `ruff format . && ruff check .`

## Phase 2: Scheduler and daily sync

- [x] 2.1 Add the `celery-beat` service to `docker-compose.yml` (`RUN_MIGRATIONS: "false"`, single replica); add `CELERY_BEAT_SCHEDULE` and an explicit `CELERY_TIMEZONE` to settings
- [x] 2.2 Verify the scheduler actually fires: temporarily shorten the interval, `docker compose logs -f celery-beat`, confirm the worker receives the task, then restore 03:00
- [x] 2.3 RED: add `SyncCatalogoTests` with listing fixtures for trending (mixed `movie`/`tv`/`person`), now_playing and discover → asserts `materializar` is called once per supported item
- [x] 2.4 RED: add a case asserting `person` entries (and any unsupported `media_type`) are skipped without raising
- [x] 2.5 RED: add a case asserting one failing item does not abort the run — the rest are still processed and the failure is counted
- [x] 2.6 RED: add a case asserting the returned statistics (`nuevas`, `actualizadas`, `omitidas`, `errores`) reflect what happened
- [x] 2.7 GREEN: implement the discovery pass of `sync_catalogo_diaria()` in `backend/catalogo/tasks.py`
- [x] 2.8 RED: add `TMDBChangesTest` (`httpx.MockTransport`) — `get_changes(tipo, page)` hits `/{tipo}/changes` and reuses the existing retry/error-mapping path; add the cache-layer case for the new `"changes"` TTL
- [x] 2.9 GREEN: add `get_changes` to `backend/catalogo/client.py` and `backend/catalogo/cache.py`
- [x] 2.10 RED: add `IdsCambiadosTests` — paginates until `total_pages`, stops at `_MAX_PAGINAS_CAMBIOS`, tolerates entries without `id`. *Adjusted at apply time:* the cap is **200**, not 100 — `/movie/changes` had 98 pages on 17/09/2026 (74 on 15/09), so 100 was one busy day away from truncating
- [x] 2.11 RED: add the refresh-pass case — a complete row whose id TMDB reports as changed is re-enriched; a complete row it does not report is left untouched. Also: a changed id we do **not** hold is never materialized (otherwise the sync would crawl the ~10k daily changes), and a failing `/changes` skips that type's refresh while discovery still runs
- [x] 2.12 GREEN: implement `_ids_cambiados()` and the refresh pass, intersecting in Python (not via a huge `id_tmdb__in`). *Adjusted at apply time:* refresh runs **before** discovery (see design.md → Sync Task) and the statistics gain `refrescadas`
- [x] 2.13 RED: **acceptance criterion, tested directly** — rate and review a production, run the sync, assert the rating and review survive untouched. Passes on first run by design (phase 1 already `save()`s the same instance); verified it fails under a delete-and-reinsert mutation before keeping it
- [x] 2.14 `docker compose exec -T backend python manage.py test catalogo` — all green (197); `ruff format . && ruff check .`. Live: 60 rows → `refrescadas: 39` in 26 s; second run 0.47 s from cache, same 60 rows

## Phase 3: Backfill, documentation and verification

- [x] 3.1 RED: add `BackfillEmbeddingsTests` — `pending` and `failed` rows are re-enqueued. Also: `processing` rows are left alone
- [x] 3.2 RED: add a case where `ready` with a matching `source_hash` and `model_version` is left alone, and one where a changed hash causes re-enqueue. Also a changed `model_version` (the B-06 case)
- [x] 3.3 RED: add a case asserting `limite` caps how many rows are processed in one run, and one asserting the cap is shared by both populations
- [x] 3.4 GREEN: implement `backfill_embeddings(limite=...)`. **Bug found at apply time:** re-enqueueing a stale `ready` row did nothing — `generar_embedding` claims with `estado__in=(pending, failed)`, so the task returned without work and the old vector would have survived forever. The backfill now returns the row to `pending` *before* enqueueing. The seven unit tests missed it (they patch `generar_embedding` wholesale); `BackfillIntegracionTests`, with the real task, caught it
- [x] 3.5 Add the beat entry for the backfill (04:00, an hour after the sync, so it picks up what that night's sync just failed to embed); `README.md` updated. `.env.example` needed no change: the schedule lives in `settings.py`, not in env vars
- [x] 3.6 Create the canonical spec `openspec/specs/catalog-daily-sync/spec.md` (Given/When/Then, RFC 2119) — 10 requirements, every one with at least one scenario, plus a Known limitations section
- [x] 3.7 Record the declared timezone in `docs/decisiones.md`; update `docs/05_Plan_de_Desarrollo.md` (C-04b marked complete)
- [x] 3.8 **Contrast the listing fixtures against the real API** — the shapes assumed in the tests must match what TMDB actually returns. In C-04a a fabricated `job: "Director"` kept 172 tests green while no series had a director in production
- [x] 3.9 End-to-end verification: force a beat run, confirm rows and statistics; run it twice and confirm no duplicates; `docker compose exec -T backend python manage.py test` full suite; `ruff format --check . && ruff check .`
