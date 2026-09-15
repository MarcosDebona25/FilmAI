# catalog-materialization Specification

## Purpose

On-demand, concurrency-safe persistence of `ProduccionAudiovisual` (CU-021). Any production opened through a catalog detail endpoint is stored globally in the local database and enriched from TMDB, so it can later be rated, added to lists (Módulo 3), and retrieved semantically (B-06). Covers C-04a only; scheduled bulk sync and embedding backfill are C-04b, and the real embedding provider is B-06.

## Requirements

### Requirement: Single materialization entry point

The system MUST expose exactly one write path into `ProduccionAudiovisual`: `catalogo.services.materialization.materializar(id_tmdb, tipo_tmdb)`. Callers MUST NOT insert catalog rows directly, and MUST NOT call TMDB themselves to build them.

The helper MUST accept TMDB vocabulary (`"movie"` / `"tv"`) and translate it to the domain (`TipoProduccion.PELICULA` / `SERIE`) through `catalogo.services.adapter`. It MUST return the `ProduccionAudiovisual` instance.

#### Scenario: Unsupported type is rejected before any write

- GIVEN `materializar(550, "all")`
- WHEN the helper runs
- THEN it raises `ValueError`
- AND no `ProduccionAudiovisual` row is created

### Requirement: Uniqueness by natural key

The system MUST keep at most one `ProduccionAudiovisual` per `(id_tmdb, tipo)` pair, enforced at the database level by the `uq_produccion_tmdb_tipo` constraint. TMDB IDs are not unique across movies and series, so `id_tmdb` alone MUST NOT be treated as unique.

#### Scenario: Repeated materialization is idempotent

- GIVEN a production already materialized for `(550, pelicula)`
- WHEN `materializar(550, "movie")` is called again
- THEN the existing row is returned
- AND no second row is created
- AND no TMDB request is issued

### Requirement: Concurrency safety

Two simultaneous materializations of the same production MUST both succeed and MUST converge on the same row. The losing insert MUST recover by reading the winner's row rather than propagating the error.

The insert MUST be wrapped in `transaction.atomic()` so the constraint violation rolls back to a savepoint: in PostgreSQL an error aborts the whole transaction, and without the savepoint the recovery query would fail too.

An `IntegrityError` that does not come from this race — the row still not being found afterwards — MUST be propagated rather than disguised as "already existed".

#### Scenario: Losing insert recovers the winner's row

- GIVEN two requests materializing `(550, pelicula)` at the same time
- WHEN one insert violates `uq_produccion_tmdb_tipo`
- THEN that caller returns the row created by the other
- AND exactly one row exists

#### Scenario: Unrelated integrity error is not swallowed

- GIVEN an `IntegrityError` unrelated to the race
- WHEN the row is still absent after the failure
- THEN the error propagates to the caller

### Requirement: TMDB enrichment

When a row is new or incomplete, the system MUST populate it from TMDB using the detail, credits and keywords endpoints via `TMDBClientCache`. These calls MUST happen outside any open write transaction, because they are network calls that may take seconds and must not hold a database connection.

Field mapping MUST follow the type-specific shapes of the TMDB API:

| Field | Movie source | TV source |
|---|---|---|
| `titulo` | `title` | `name` |
| `fecha_lanzamiento` | `release_date` (empty ⇒ NULL) | `first_air_date` (empty ⇒ NULL) |
| `reparto` | first 10 of `credits.cast` | same |
| `directores` | `credits.crew` filtered by `job == "Director"` | same |
| `generos` | `genres[].name` | same |
| `keywords` | `keywords` key | `results` key |
| `duracion` | `runtime` | `episode_run_time[0]`, else NULL |
| `cantidad_temporadas` / `cantidad_episodios` | NULL | `number_of_seasons` / `number_of_episodes` |
| `poster` | raw `poster_path` (CDN URL built by the frontend) | same |

#### Scenario: Keywords key differs by type

- GIVEN the keywords payload of a movie and of a series
- WHEN the system extracts them
- THEN the movie list is read from `keywords` and the series list from `results`

#### Scenario: Empty release date becomes NULL

- GIVEN TMDB returns `release_date: ""` for an unreleased title
- WHEN the row is enriched
- THEN `fecha_lanzamiento` is NULL rather than an invalid date

### Requirement: Embedding enqueue

After persisting the production, the system MUST ensure a `ProduccionEmbedding` exists in state `pending` and MUST enqueue `generar_embedding(produccion_id)` for asynchronous processing. It MUST NOT wait for the result.

The task MUST be enqueued only when the embedding row is newly created. Re-enqueuing on every visit would fill the queue with duplicated work; refreshing `failed` or stale embeddings is the responsibility of the C-04b backfill.

#### Scenario: Enqueued once across repeated visits

- GIVEN a production opened twice in detail
- WHEN both requests are handled
- THEN exactly one `ProduccionEmbedding` exists
- AND the task was enqueued exactly once

### Requirement: Failure isolation

`materializar()` MUST propagate its errors so that each caller can choose its own failure policy. Detail views MUST NOT let a materialization failure alter their response: the body stays the raw TMDB passthrough defined by C-03, and the failure is logged.

#### Scenario: Materialization failure leaves the response intact

- GIVEN materialization raises for any reason
- WHEN `GET /api/catalogo/movie/{id}/` is handled
- THEN the response is still 200 with the unchanged TMDB body
- AND the failure is recorded in the logs

### Requirement: Incompleteness criterion

The system MUST re-enrich a row it considers incomplete. The current criterion is the absence of `titulo`.

This is a KNOWN LIMITATION: a row holding a title but missing genres or synopsis is treated as complete. It cannot occur while `materializar()` is the only write path, and `_necesita_enriquecimiento()` is the single place to harden when C-04b starts creating partial rows from listing summaries.

#### Scenario: Incomplete row is repaired on next open

- GIVEN a row that exists with an empty `titulo`
- WHEN `materializar()` is called for it
- THEN TMDB is queried and the row is completed in place
- AND no duplicate row is created
