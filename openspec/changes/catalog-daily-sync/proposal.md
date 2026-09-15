# Proposal: Daily Catalog Sync + Embedding Backfill (C-04b, CU-021)

## Intent

C-04a made the catalog **reactive**: a production is persisted the moment
someone opens it in detail. Nothing keeps that catalog fresh, and nothing
rescues an embedding that failed — which today is *every* embedding, since the
provider is still a stub. C-04b adds the **proactive** half: a nightly job that
refreshes what TMDB changed and a backfill that retries the embeddings that did
not make it.

The catalog is hybrid by design: discovery (Home, Search) is served live from
TMDB, so this sync is **maintenance, not a prerequisite**. If it misses a night,
the application keeps working.

## Scope

### In Scope
- `celery-beat` service in `docker-compose.yml`, scheduled at 03:00 with an
  explicitly declared timezone
- `CELERY_BEAT_SCHEDULE` in settings
- `catalogo/tasks.py::sync_catalogo_diaria()`: walks trending, now_playing and
  popular discover, materializing each item; logs per-run statistics (new,
  updated, errors)
- `catalogo/tasks.py::backfill_embeddings()`: picks up `pending` and `failed`
  rows in bounded batches, and regenerates `ready` rows whose `source_hash` or
  `model_version` no longer match
- `get_changes(tipo, page)` on `TMDBClient` and `TMDBClientCache` (additive, same shape as the existing methods) + a `"changes"` TTL
- New `ProduccionAudiovisual.fecha_enriquecimiento` field + migration: records
  when full detail was last pulled: it answers the completeness question and
  backs the safety net. Staleness itself comes from TMDB's own changes list
- `materializar(id_tmdb, tipo_tmdb, forzar=False)`: an explicit refresh flag, so
  the sync can re-enrich without opening a second write path
- `_necesita_enriquecimiento()` hardened to use `fecha_enriquecimiento`
- Refresh pass in the sync: intersect our ids with the ids TMDB reports as
  changed in the last 24 h, and re-materialize that set with `forzar=True`
- `generar_embedding.delay(...)` wrapped in `transaction.on_commit()`
- `.env.example`, `README.md`, `docs/decisiones.md` updates

### Out of Scope
- **Initial seed of ~10k productions** — split into its own task (C-04c). It
  needs pagination, rate pacing and resumability, and it should only run once
  the mapping proven here is known to be correct. The development plan already
  allowed for this: "con C-04b **o** comando de management".
- The real embedding provider (Ollama client, `bge-m3`) — B-06 (Marcos)
- `buscar_semantico` retrieval — B-06
- Any change to the response contract of the C-03 endpoints
- Genre-name resolution from `genre_ids` — unnecessary, because every row goes
  through the detail endpoint, which returns genre names directly

## Capabilities

### New Capabilities
- `catalog-daily-sync`: scheduled, idempotent refresh of the persisted catalog
  from TMDB, and recovery of embeddings that never completed

### Modified Capabilities
- `catalog-materialization` (C-04a): `materializar()` gains the `forzar` flag;
  the incompleteness criterion moves from "no title" to
  `fecha_enriquecimiento`; the enqueue moves inside `transaction.on_commit()`.
  The single-write-path guarantee is **preserved** — that is the point of the
  flag.

## Approach

**The sync calls `materializar()` per item.** It does not write rows itself.
This was the central decision (15/09/2026) and it resolves three problems at
once: the canonical spec's "exactly one write path" holds; no partial rows are
ever created; and `genre_ids` never need translating, because the detail
endpoint returns genre names. The cost is three TMDB calls per item, all
Redis-cached for 24 h.

**Freshness is explicit, not inferred.** `fecha_enriquecimiento` records when a
row last saw the detail endpoint. `NULL` means never; older than the refresh
window means stale. The sync passes `forzar=True` for rows it decides to
refresh, which is the only way to re-enrich without a second write path.

**The backfill works in bounded batches.** Enqueuing thousands of tasks at once
would flood the broker; it processes a capped number of rows per run and lets
the next run continue.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/catalogo/tasks.py` | Modified | `sync_catalogo_diaria`, `backfill_embeddings` |
| `backend/catalogo/client.py` | Modified | `get_changes(tipo, page)` (additive) |
| `backend/catalogo/cache.py` | Modified | cached `get_changes` + `"changes"` TTL |
| `backend/catalogo/services/materialization.py` | Modified | `forzar` flag, `fecha_enriquecimiento`, `on_commit` |
| `backend/catalogo/models.py` | Modified | `fecha_enriquecimiento` field |
| `backend/catalogo/migrations/` | New | `AddField` |
| `backend/filmai/settings.py` | Modified | `CELERY_BEAT_SCHEDULE`, `CELERY_TIMEZONE` |
| `docker-compose.yml` | Modified | `celery-beat` service |
| `openspec/specs/catalog-materialization/spec.md` | Modified | criterion + write path |
| `.env.example`, `README.md`, `docs/decisiones.md` | Modified | 6-service topology, decisions |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| The sync overwrites user data (ratings, reviews) | Med | It writes only through `materializar()`, which touches TMDB-sourced fields exclusively. Covered by a test that rates and reviews a production, runs the sync, and asserts both survive |
| Two `celery-beat` containers fire the task twice | Med | A single beat container, as a single container migrates today via `RUN_MIGRATIONS`. The task is idempotent regardless |
| "3 AM" ambiguous between UTC and Argentina | Med | `CELERY_TIMEZONE` declared explicitly and recorded in `docs/decisiones.md`. The classic bug discovered three months later |
| The backfill floods the broker | Low–Med | Bounded batches per run, not one enqueue per row |
| TMDB rate limits during a sync run | Low | ~60 items per run × 3 calls, all cached. The client already retries on 429 honoring `Retry-After`. The real exposure is the seed, which is out of scope here |
| `on_commit` silently disables the enqueue in tests | Med | Known Django behavior: callbacks do not run inside `TestCase`. The two affected tests move to `captureOnCommitCallbacks(execute=True)` |

## Rollback Plan

Each work unit has an isolated boundary. Reverting the beat service stops the
schedule without touching any task code. Reverting the tasks leaves
`materializar()` intact and the catalog reactive, exactly as C-04a shipped. The
`fecha_enriquecimiento` migration is additive and nullable: rolling it back
requires `migrate catalogo <prev>` before reverting the model, and no data is
lost because the column is derived, not authored.

## Dependencies

- C-04a on `main`: `materializar()`, `generar_embedding`, `ProduccionEmbedding`
- Celery worker and broker already wired (C-04a)
- **B-06 is required only for the backfill to be *useful*, not to build it.**
  Until `generar_vector()` is real, the backfill correctly moves rows to
  `failed`. It can be written and tested now by mocking the provider, exactly
  as `generar_embedding` was.

## Success Criteria

- [ ] `celery -A filmai beat` fires `sync_catalogo_diaria` on schedule, in the declared timezone
- [ ] A sync run materializes every item it walks, with no partial rows
- [ ] A row TMDB reports as changed is refreshed; a complete row it does not report is left untouched
- [ ] Two consecutive runs produce no duplicates and no redundant TMDB calls
- [ ] A rated and reviewed production keeps its rating and review after a sync
- [ ] `fecha_enriquecimiento` is set on enrichment and answers the completeness check
- [ ] The backfill picks up `pending` and `failed` rows in bounded batches
- [ ] The backfill regenerates a `ready` row whose `source_hash` changed
- [ ] No change to the C-03 endpoint response contract
- [ ] Tests pass via `python manage.py test` with no real network
