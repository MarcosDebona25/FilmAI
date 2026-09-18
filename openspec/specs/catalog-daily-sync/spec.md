# catalog-daily-sync Specification

## Purpose

Scheduled maintenance of the local catalog (CU-021). A nightly Celery task grows the corpus without waiting for a user to open anything, refreshes the rows TMDB reports as changed, and a second task recovers embedding work that never completed. Covers C-04b. The initial ~10k seed is C-04c; the real embedding provider is B-06. Builds on `catalog-materialization`, which owns the single write path this capability drives.

## Requirements

### Requirement: Scheduled execution

The system MUST run `catalogo.sync_catalogo_diaria` once per day at 03:00 and `catalogo.backfill_embeddings` once per day at 04:00, through a dedicated `celery-beat` service declared in `docker-compose.yml`.

`CELERY_TIMEZONE` MUST be declared explicitly so the schedule is interpreted in the project's timezone rather than UTC.

Exactly one beat instance MUST run. Beat MUST NOT write its schedule state file into the source bind mount.

#### Scenario: The scheduler enqueues rather than executes

- GIVEN the scheduled hour is reached
- WHEN beat fires the entry
- THEN the task is published to the broker
- AND a `celery-worker` process executes it

### Requirement: The sync writes only through materialization

`sync_catalogo_diaria` MUST NOT write `ProduccionAudiovisual` rows itself. Every item it processes MUST go through `materializar()`, as required by `catalog-materialization`.

A TMDB listing item MUST NOT be treated as sufficient to fill a row: listing payloads carry `genre_ids` rather than genre names, and carry no status, runtime, credits or keywords — four of the six sections of the canonical embedding text.

#### Scenario: A discovered item is persisted from its detail, not its listing entry

- GIVEN a production appears in a TMDB listing and is not in the database
- WHEN the sync processes it
- THEN `materializar()` is called with its id and TMDB type
- AND the stored row has genres, cast, directors and keywords

### Requirement: Discovery pass

The sync MUST walk a declared set of TMDB listing sources and materialize each supported item, so the corpus grows without a user opening anything.

Each source MUST declare how the item's TMDB type is resolved: from `media_type` where the endpoint mixes types, otherwise from the type the endpoint implies. Items whose type is not `movie` or `tv` (TMDB trending includes `person`) MUST be skipped and counted, not treated as an error.

#### Scenario: A person entry in trending is skipped

- GIVEN a trending payload containing an entry with `media_type: "person"`
- WHEN the sync processes it
- THEN no materialization is attempted for it
- AND it is counted as `omitidas`

### Requirement: Refresh pass driven by TMDB's change list

The sync MUST refresh the rows TMDB reports as modified, rather than inferring staleness from elapsed time. It MUST read `/movie/changes` and `/tv/changes`, intersect those ids with the ids already stored, and re-materialize the intersection with `forzar=True`.

The intersection MUST be computed in Python over two sets, not by passing thousands of ids into a SQL `IN` clause.

Changed ids that are not in the local database MUST NOT be materialized: the change list covers all of TMDB, and following it would turn the sync into a crawl.

Pagination of the change list MUST stop at a declared maximum. Ids beyond that cap are covered by the staleness safety net of `catalog-materialization`.

#### Scenario: Only the intersection is refreshed

- GIVEN the database holds productions A and B
- AND TMDB reports A and C as changed today
- WHEN the sync runs
- THEN A is re-materialized with `forzar=True`
- AND B is not re-materialized
- AND C is never requested

### Requirement: Refresh precedes discovery

The refresh pass MUST run before the discovery pass. A title currently in theatres is both actively edited on TMDB and present in the listing sources; discovery-first would enrich it as new and the refresh would enrich it again moments later.

#### Scenario: A row enriched by discovery is not enriched twice

- GIVEN a production is both in today's change list and in a listing source
- WHEN the sync runs
- THEN it is enriched once

### Requirement: Failures are per item

A failure while processing one item MUST NOT abort the run. It MUST be logged, counted in `errores`, and the run MUST continue.

If the change list itself fails for one TMDB type, the refresh of that type MUST be skipped and the run MUST continue, including the discovery pass.

#### Scenario: One unavailable title does not lose the night

- GIVEN five items to process and one raising an exception
- WHEN the sync runs
- THEN the other four are still processed
- AND the failure is counted once

### Requirement: User data survives synchronization

The sync MUST update only fields sourced from TMDB. Ratings, reviews and list membership MUST be left untouched.

Refreshing MUST update the existing row in place. Delete-and-reinsert MUST NOT be used: `Calificacion` and list entries cascade from `ProduccionAudiovisual`, so recreating a row would silently destroy user data.

#### Scenario: A rated and reviewed production is refreshed

- GIVEN a user has rated and reviewed a production
- AND TMDB reports it as changed
- WHEN the sync runs
- THEN the production's TMDB fields are updated
- AND the rating and the review still exist, unchanged, attached to the same row

### Requirement: Run statistics

Each run MUST return and log a statistics dictionary reporting `nuevas`, `actualizadas`, `refrescadas`, `omitidas` and `errores`.

`nuevas` MUST count each production once even when it appears in several sources.

#### Scenario: A production present in two sources counts once

- GIVEN a production appears in both trending and now playing
- AND it is not in the database
- WHEN the sync runs
- THEN it is counted once in `nuevas`

### Requirement: Embedding backfill

The system MUST provide `catalogo.backfill_embeddings(limite=...)` to recover embedding work that never completed. `materializar()` enqueues an embedding only when it creates the row, so rows left in `pending` (broker unavailable) or `failed` (provider error) would otherwise never be retried.

It MUST cover two populations, sharing one limit: rows in `pending` or `failed`, and `ready` rows whose recomputed `source_hash` or stored `model_version` no longer matches.

Rows in `processing` MUST NOT be touched.

The task MUST re-enqueue `generar_embedding` rather than compute vectors itself, so the claim logic of `embedding-infrastructure` remains the single source of truth for idempotency.

A `ready` row selected for regeneration MUST be returned to `pending` before being enqueued, because the claim in `generar_embedding` only accepts `pending` and `failed`.

#### Scenario: A stale ready row is regenerated

- GIVEN a `ready` embedding whose production text has since changed
- WHEN the backfill runs and the worker processes the enqueued task
- THEN the stored `source_hash` matches the current canonical text
- AND the row is `ready` again

#### Scenario: The limit caps the whole run

- GIVEN one `pending` row and one stale `ready` row
- WHEN the backfill runs with `limite=1`
- THEN exactly one task is enqueued

### Requirement: Rows are processed oldest first

Both backfill populations MUST be traversed by ascending `fecha_actualizacion`, so that rows beyond the limit in one run are reached in a later one rather than starved indefinitely.

#### Scenario: Work rotates across runs

- GIVEN more outstanding rows than the limit
- WHEN the backfill runs on consecutive nights
- THEN rows not reached on the first night are reached later

## Known limitations

- A row stranded in `processing` (worker killed mid-task) is recovered by nobody. A lease with an expiry is the fix, and is best added once the real provider (B-06) makes tasks long enough for this to occur in practice.
- If the provider fails while regenerating a stale `ready` row, the row ends in `failed` holding its previous vector: it stops being used by search for one night and the next run retries it, since `failed` is claimable.
- The discovery pass reads page 1 of each source, so it captures novelty rather than growing the corpus in volume. Bulk population is C-04c.
