# catalog-seed Specification

## Purpose

One-off bulk population of the local catalog (CU-021). `catalog-daily-sync` keeps the corpus fresh but reads one page of four listings a night, so it captures novelty rather than volume. This capability walks TMDB along genre, decade and type and materializes what it finds, so the semantic search space (B-06) holds more than this month's popular titles. Covers C-04c. Builds on `catalog-materialization`, which owns the single write path this capability drives, and on the `get_genres` and year-range `discover` support of `tmdb-client` and `tmdb-cache`.

## Requirements

### Requirement: Management command, not a scheduled task

The seed MUST be exposed as `python manage.py seed_catalogo`. It MUST NOT be a Celery task: it runs for tens of minutes under supervision, and a blocking process with a progress counter is easier to watch, interrupt and resume than a task whose only output is a log line an hour later.

#### Scenario: The command reports where it is

- GIVEN the command is running
- WHEN it reads a page of a combination
- THEN it prints the current count, the target and which combination and page it is reading

### Requirement: The seed writes only through materialization

`seed_catalogo` MUST NOT write `ProduccionAudiovisual` rows itself. Every item it materializes MUST go through `materializar()`, as required by `catalog-materialization`, so rows land with genres, cast, directors, keywords and a non-null `fecha_enriquecimiento`.

#### Scenario: A seeded row is complete

- GIVEN a production is reached by the seed and is not in the database
- WHEN the seed processes it
- THEN `materializar()` is called with its id and TMDB type
- AND the stored row has a non-null `fecha_enriquecimiento`

### Requirement: Sampling across genre, decade and type

The seed MUST sample the product of genre × decade × type rather than a single popularity-sorted listing. Genres MUST be read from `/genre/{tipo}/list` for each type, never from a list in the source: the two catalogues differ (movies have `Action` and `Adventure`, series have `Action & Adventure`) and the ids are TMDB's.

Decades MUST run from a declared initial decade (1970) to the decade containing the current year, inclusive. `--desde-anio` MAY move the start and MUST be rounded down to the start of its decade. `--tipos` MAY restrict the types.

Within each combination, results MUST be requested sorted by `vote_count.desc`, so the corpus holds the titles people know rather than what trended this week.

#### Scenario: The combinations cover the whole space

- GIVEN 19 movie genres and 16 TV genres from TMDB
- AND decades from 1970 to the current one
- WHEN the seed builds its combinations
- THEN there are 19 × 6 + 16 × 6 = 210 of them
- AND each carries the year range of its decade and the genre id of its own type

### Requirement: Round-robin over a deterministically shuffled order

The seed MUST traverse combinations in rounds — page 1 of every combination before page 2 of any — so an interrupted run is a smaller version of the same diverse corpus rather than every title of one genre and none of another.

The combination order MUST be shuffled with a fixed seed: cutting mid-round in declaration order would bias toward whichever genre is listed first, and a fixed seed keeps two runs on the same path so resuming covers the same ground.

#### Scenario: Page 1 of every combination precedes page 2 of any

- GIVEN two combinations, one with two pages and one with a single page
- WHEN the seed traverses them
- THEN the pages are requested in the order (A, 1), (B, 1), (A, 2)
- AND B is not requested again

#### Scenario: The order is reproducible

- GIVEN the same genre lists and decades
- WHEN the combinations are built twice
- THEN the two orders are identical
- AND differ from the declaration order

### Requirement: Pagination stops at the 500-page wall

Pagination of `/discover` MUST stop at `min(total_pages, 500)`. TMDB reports `total_pages` above 500 and answers HTTP 400 for page 501 (verified 18/09/2026); `total_pages` is input, not truth.

#### Scenario: A combination that reports 1001 pages

- GIVEN `/discover` reports `total_pages: 1001` for a combination
- WHEN the seed traverses it
- THEN pages 1 to 500 are requested
- AND page 501 is never requested

### Requirement: The limit counts this run's materializations

`--limite` (default 2 000) MUST cap how many productions are materialized in the current run and MUST stop the traversal as soon as it is reached, even mid-page. Rows skipped because they were already fresh MUST NOT count toward it.

#### Scenario: The limit stops mid-round

- GIVEN six candidate productions across three combinations
- WHEN the seed runs with `--limite 4`
- THEN exactly four are materialized

#### Scenario: Fresh rows do not consume the limit

- GIVEN six candidates of which one is already stored and fresh
- WHEN the seed runs with `--limite 5`
- THEN five are materialized
- AND the fresh one is counted in `ya_estaban`

### Requirement: Resumable without state of its own

The seed MUST keep no progress file or state table. It MUST load the keys `(id_tmdb, tipo)` of every row `materializar()` would not re-enrich — those with `fecha_enriquecimiento` inside the freshness window of `catalog-materialization` — once at startup, and skip them without calling `materializar()`. Rows that exist but were never enriched MUST be sent to `materializar()` so they are completed.

The freshness definition MUST be the one owned by `catalog-materialization` (`claves_frescas()`), so the seed and the materialization cannot disagree on what is fresh.

#### Scenario: Re-running after an interruption costs no detail request

- GIVEN a previous run materialized N productions
- WHEN the seed runs again on the same path
- THEN those N are counted in `ya_estaban`
- AND no detail, credits or keywords request is issued for them
- AND no duplicate row is created

### Requirement: One production, one materialization per run

A title carrying several genres appears in several combinations. Within a run the seed MUST materialize it once and count later sightings in `omitidas`. The key MUST be `(id_tmdb, tipo)`: a TMDB id is unique only within a type.

#### Scenario: A film that is both Action and Drama

- GIVEN a production listed under two genres of the same type
- WHEN the seed reaches both combinations
- THEN `materializar()` is called once for it
- AND the second sighting is counted in `omitidas`

### Requirement: Failures are per item and per page

A failure in `materializar()` for one item MUST be logged, counted in `errores` and skipped; the run MUST continue. A failure reading one page of one combination MUST be logged, counted in `errores`, and that combination MUST leave the round; the run MUST continue with the others.

#### Scenario: One unavailable title does not end a four-hour run

- GIVEN six candidates of which one raises in `materializar()`
- WHEN the seed runs
- THEN the other five are materialized
- AND `errores` is 1

### Requirement: Interruption leaves a consistent, resumable catalog

Each `materializar()` call MUST be its own transaction, so Ctrl-C between items loses nothing. On `KeyboardInterrupt` the command MUST print the summary and exit without a traceback.

#### Scenario: Ctrl-C mid-run

- GIVEN the seed has materialized two productions
- WHEN the process receives a `KeyboardInterrupt` during the third
- THEN the two are persisted
- AND the summary reports `materializadas=2`

### Requirement: Run statistics

The command MUST print and log a final summary with `materializadas`, `ya_estaban`, `omitidas` and `errores`. `materializadas` counts productions sent through `materializar()` in this run; `ya_estaban` counts rows skipped as already fresh; `omitidas` counts repeated sightings within the run; `errores` counts failed items and failed pages.

`--dry-run` MUST traverse `discover` and compute the same counters without calling `materializar()`, and MUST say so in its output.

#### Scenario: Dry run

- GIVEN `--dry-run`
- WHEN the seed runs
- THEN `discover` is requested
- AND `materializar()` is never called
- AND the output states that nothing was written

### Requirement: The development reset refuses to wipe a seeded catalog

`python manage.py seed` MUST refuse to run when the catalog holds more productions than a declared threshold (100, twice what the reset itself creates), unless `--borrar-catalogo` is passed. The refusal MUST name that flag. Below the threshold the reset MUST behave as before.

#### Scenario: A populated catalog is protected

- GIVEN 101 productions in the catalog
- WHEN `seed` runs without the flag
- THEN it aborts with a `CommandError` naming `--borrar-catalogo`
- AND no row is deleted

## Known limitations

- The seed does not pace itself: TMDB publishes no rate-limit headers and drew no `429` under rapid calls (verified 18/09/2026); the client retries `429` and `5xx` with backoff. `--pausa` is a manual brake for a long run that starts drawing them.
- The first full round is 210 × 20 = 4 200 items, so `--limite 2000` does not finish round one; diversity comes from the shuffled order, not from depth. A `--limite 50` reaches only three combinations and says nothing about spread; the spread was verified with a dry run over 600 (37 combinations: 26 movie / 11 TV, all six decades).
- TMDB's TV genre list includes `Talk`, `Soap`, `News` and `Reality`. They enter the corpus with everything else. If B-06 surfaces them where they do not belong, a genre exclusion option is the fix.
- Embeddings enqueued by the seed end in `failed` until the real provider (B-06) exists; the backfill of `catalog-daily-sync` recovers them afterwards. That is by design.
