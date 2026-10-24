# catalog-materialization Specification

## Purpose

On-demand, concurrency-safe persistence of `ProduccionAudiovisual` (CU-021). Any production opened through a catalog detail endpoint is stored globally in the local database and enriched from TMDB, so it can later be rated, added to lists (Módulo 3), and retrieved semantically (B-06). Covers C-04a only; scheduled bulk sync and embedding backfill are C-04b, and the real embedding provider is B-06.

## Requirements

### Requirement: Single materialization entry point

The system MUST expose exactly one write path into `ProduccionAudiovisual`: `catalogo.services.materialization.materializar(id_tmdb, tipo_tmdb, forzar=False)`. Callers MUST NOT insert catalog rows directly, and MUST NOT call TMDB themselves to build them. This includes bulk processes such as the daily sync: they iterate and call the helper per item.

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
- WHEN the row is still absent after the failure, and again after one retry
- THEN the error propagates to the caller

#### Scenario: The winner's row was discarded before the loser found it

- GIVEN the insert collides with a row that another request then deletes (TMDB answered 404, security audit F7)
- WHEN the loser looks for the winner's row and finds none
- THEN the insert is retried once instead of answering 500 (Internal Server Error)

### Requirement: TMDB enrichment

When a row is new or incomplete, the system MUST populate it from TMDB using the detail, credits and keywords endpoints via `TMDBClientCache`. These calls MUST happen outside any open write transaction, because they are network calls that may take seconds and must not hold a database connection.

Field mapping MUST follow the type-specific shapes of the TMDB API:

| Field | Movie source | TV source |
|---|---|---|
| `titulo` | `title` | `name` |
| `fecha_lanzamiento` | `release_date` (empty ⇒ NULL) | `first_air_date` (empty ⇒ NULL) |
| `reparto` | first 10 of `credits.cast` | same |
| `directores` | `credits.crew` filtered by `job == "Director"` | `created_by` from the detail payload, falling back to crew directors |
| `generos` | `genres[].name` | same |
| `keywords` | `keywords` key | `results` key |
| `duracion` | `runtime` | `episode_run_time[0]`, else NULL |
| `cantidad_temporadas` / `cantidad_episodios` | NULL | `number_of_seasons` / `number_of_episodes` |
| `poster` | raw `poster_path` (CDN URL built by the frontend) | same |

Two type asymmetries were confirmed against the live API on 2026-09-15 and are load-bearing:

- A series carries no `job == "Director"` in its crew, because TV directors are per-episode. Its authorship MUST come from `created_by`, or the canonical text of every series would ship an empty `Directors:` line and no series could be retrieved by its author.
- TMDB frequently returns an empty `episode_run_time`, so `duracion` is legitimately NULL for many series. ACCEPTED as-is: duration is not part of the embedded text, and `last_episode_to_air.runtime` is not a representative substitute.

#### Scenario: A series is credited to its creators

- GIVEN a series whose crew contains no `job == "Director"`
- WHEN the row is enriched
- THEN `directores` is taken from the detail payload's `created_by`
- AND a series with neither creators nor crew directors is left empty

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

The enqueue MUST be deferred to `transaction.on_commit()`. The worker runs in another process with its own connection: a message sent before the row is committed would point at a row the worker cannot yet see. With no open transaction the callback runs immediately, so the behavior is unchanged in that case; inside an `atomic()` block it waits for the commit, and a rollback enqueues nothing.

#### Scenario: Enqueued once across repeated visits

- GIVEN a production opened twice in detail
- WHEN both requests are handled
- THEN exactly one `ProduccionEmbedding` exists
- AND the task was enqueued exactly once

#### Scenario: Enqueue waits for the commit

- GIVEN materialization runs inside an open transaction
- WHEN `materializar()` returns
- THEN the task has not been sent yet
- AND exactly one on-commit callback is registered to send it

### Requirement: Detail views materialize in the background

Detail views MUST NOT enrich inside the request (14/10/2026: it added up to a second to the first visit). They MUST call `materializar_en_segundo_plano(id_tmdb, tipo_tmdb)`, which enqueues the Celery task `catalogo.materializar_produccion` only when the row does not exist or still needs enrichment, and enqueues nothing for a complete row. The task MUST call `materializar()` and MUST NOT raise: a failure is logged and the next visit enqueues it again, since the row is still missing or unenriched. Writes that need the row (rating, adding to a list) MUST keep materializing synchronously before writing.

#### Scenario: First visit

- GIVEN a production that is not in the database
- WHEN `GET /api/catalogo/movie/{id}/` is handled
- THEN the response is the TMDB body, no row is written during the request
- AND `materializar_produccion` is enqueued once with `(id, "movie")`

#### Scenario: Complete row

- GIVEN an enriched row inside the staleness window
- WHEN its detail is opened again
- THEN nothing is enqueued

### Requirement: Listings materialize what they show

Since 16/10/2026 (docs 02 and 03), `trending`, `now-playing`, `discover`, `search` and `browse` MUST call `materializar_listado_en_segundo_plano(results, tipo_tmdb)` after building their response. It takes the type from each item's `media_type` when present (mixed listings) or from the listing, ignores people and malformed items, filters the fresh rows with a single query, and enqueues `materializar_produccion` for the rest. The same title MUST be enqueued at most once per 10 minutes (an atomic `cache.add` marker), so repeated visits to the same listing do not flood the queue while TMDB is slow or down. If enqueuing fails, the marker MUST be removed so the next listing retries. A failure while enqueuing MUST NOT alter the listing response.

#### Scenario: Home trending

- GIVEN `trending/all` returns a movie, a TV show and a person
- WHEN the view is handled
- THEN the movie and the TV show are enqueued with their own type and the person is ignored

#### Scenario: Repeated visits

- GIVEN the same listing is requested five times within 10 minutes
- THEN each title not yet fresh is enqueued once

### Requirement: Failure isolation

`materializar()` MUST propagate its errors so that each caller can choose its own failure policy. Detail views MUST NOT let a materialization failure (including a broker that cannot enqueue) alter their response: the body stays the raw TMDB passthrough defined by C-03, and the failure is logged.

#### Scenario: Materialization failure leaves the response intact

- GIVEN enqueuing the materialization raises for any reason
- WHEN `GET /api/catalogo/movie/{id}/` is handled
- THEN the response is still 200 with the unchanged TMDB body
- AND the failure is recorded in the logs

#### Scenario: An id TMDB does not know leaves no row

- GIVEN no row exists for the id and TMDB answers 404 (Not Found) for its detail
- WHEN `materializar()` runs
- THEN it raises `TMDBNotFound`
- AND the empty row it created is deleted (security audit F7, 24/10/2026)
- AND an empty, never-enriched row left by an earlier transient failure is deleted too
- AND a row with data is never deleted, since ratings and lists may hang from it
- AND a transient failure (TMDB down) keeps the new row, to be enriched on a later visit

### Requirement: Enrichment is recorded, not inferred

The system MUST record on each row when it last pulled the full TMDB detail, in `ProduccionAudiovisual.fecha_enriquecimiento`. A row whose value is `NULL` MUST be treated as never enriched and MUST be enriched on the next materialization, regardless of which other fields it holds.

Completeness MUST NOT be inferred from the presence of any content field. Revised 16/09/2026 (C-04b): the previous criterion — "the row has no `titulo`" — only held while a single writer filled every column at once. A row built from a TMDB listing item carries a title but no genres, cast, crew or keywords, and under that criterion would have counted as complete forever.

The timestamp MUST be written in the same `save()` as the enriched fields, so a failed write never leaves a row marked as enriched.

#### Scenario: A listing-shaped row is repaired on next open

- GIVEN a row that exists with a `titulo` but `fecha_enriquecimiento` is `NULL`
- WHEN `materializar()` is called for it
- THEN TMDB is queried and cast, crew, genres and keywords are filled in place
- AND `fecha_enriquecimiento` is set
- AND no duplicate row is created

#### Scenario: A recently enriched row is left alone

- GIVEN a row whose `fecha_enriquecimiento` is recent
- WHEN `materializar()` is called for it without `forzar`
- THEN no TMDB request is issued

### Requirement: Staleness safety net

The system MUST re-enrich a row whose `fecha_enriquecimiento` is older than a long safety window (`_DIAS_RED_DE_SEGURIDAD`, 90 days at the time of writing).

This window is NOT the primary refresh mechanism. Actual change detection belongs to the daily sync (`catalog-daily-sync`), which asks TMDB's own changes list and forces a refresh through `forzar`. The window only guarantees that a row can never go unrefreshed forever if that list is missed.

#### Scenario: Window boundary

- GIVEN a row enriched 91 days ago and another enriched 89 days ago
- WHEN `_necesita_enriquecimiento()` evaluates each
- THEN the first needs enrichment and the second does not

### Requirement: Forced refresh

`materializar()` MUST accept `forzar=True`, which re-enriches the row even when the completeness and staleness checks would skip it. This is the only sanctioned way to refresh a complete row: callers MUST NOT blank `fecha_enriquecimiento` to provoke the path, and MUST NOT write the row themselves.

#### Scenario: Forced refresh re-queries TMDB

- GIVEN a row enriched one hour ago
- WHEN `materializar(id_tmdb, tipo_tmdb, forzar=True)` is called
- THEN TMDB is queried again
- AND the row's fields and `fecha_enriquecimiento` are updated in place

### Requirement: Traducciones persistidas (OT-62, OT-63)

`ProduccionAudiovisual` MUST seguir siendo canónica en inglés; el texto de
embeddings y su `source_hash` no cambian. El enriquecimiento MUST guardar
`generos_ids` y, por cada idioma no canónico, una fila `ProduccionTraduccion`
(título, sinopsis, póster) con `update_or_create`. Un fallo al traer la
traducción MUST registrarse sin invalidar el enriquecimiento canónico.
`rellenar_traducciones` MUST completar de forma idempotente y por lotes las
filas enriquecidas pendientes; la sincronización nocturna ejecuta ese relleno
acotado por `CELERY_BACKFILL_LIMIT` y lo informa en `traducciones`.
Los serializers de ítems de lista, previews y «mis reseñas» MUST elegir título
y póster por idioma efectivo con respaldo al canónico, sin consultas por fila.
