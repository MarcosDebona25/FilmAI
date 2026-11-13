# similar-titles Specification

## Purpose

One engine that finds titles similar to a set of seeds — one title on its page,
or the items of a list — with the B-06 vectors in pgvector and TMDB
`/recommendations` as a fill. Two endpoints use it: the title page row and the
list suggestions. Builds on `embedding-infrastructure`, `semantic-search`
(`ef_search`, model preload), `tmdb-cache`, `catalog-materialization` and
`list-endpoints`. Design in `openspec/changes/recomendaciones-similares/design.md`.

## ADDED Requirements

### Requirement: Seed vector

The engine MUST average the `ready` vectors of the seeds and normalize the
result. Seeds without a `ready` vector MUST be skipped. When a list name is
given, the engine MUST mix it as `normalize((1 − w) · centroid + w · name)`
with `w = max(0.15, 1 / (n + 1))`, `n` being the seeds with a vector.

#### Scenario: One title and a meaningful name

- GIVEN a list «Pelis para llorar» with one title that has a vector
- WHEN its suggestions are computed with the model loaded
- THEN the vector is half the title and half the name

#### Scenario: No seed has a vector

- GIVEN a list whose only item has its embedding `pending`
- WHEN its suggestions are computed
- THEN there is no local search and the results come from TMDB only

### Requirement: The name only when it says something

A name MUST be used only for custom lists, and only when, after lowercasing,
removing accents and digits and dropping the filler words listed in the
design, a word of 3 or more letters remains. Favorites MUST NOT use its name.

#### Scenario: Generic name

- GIVEN a list named «Lista 3»
- THEN the name is not embedded and `nombre_usado` is `false`

### Requirement: Ollama is never waited for

The name vector MUST be read from a cache keyed by model and normalized name
first. If it is missing and the model is not loaded or Ollama fails, the name
MUST be skipped without waiting, the model load MUST be requested, and the
pool MUST be cached for 5 minutes instead of 24 hours. A failure to reach
Ollama MUST be remembered for 60 seconds so later requests do not wait for it.

#### Scenario: Model not loaded

- GIVEN `bge-m3` is not loaded and the name is not cached
- WHEN a list asks for suggestions
- THEN the answer arrives without the name, `nombre_usado` is `false`
- AND `calentar_modelo` is enqueued

### Requirement: Local candidates

Candidates MUST come from `produccion_embedding` ordered by cosine distance,
with the seeds excluded in SQL and `hnsw.iterative_scan = relaxed_order`, so
excluding many seeds never shortens the result. They MUST have a poster and a
TMDB rating. A list with a single type MUST only get that type; a mixed list
and a title page MUST get both.

#### Scenario: A list of 1 000 close titles

- GIVEN a list made of the 1 000 nearest neighbours of a title
- WHEN 100 candidates are asked for
- THEN 100 are returned, none of them in the list

### Requirement: TMDB fill

When fewer than 20 local candidates are within the distance threshold, the
engine MUST ask TMDB `/recommendations` for up to 3 seeds (the most recently
added items, or the title of the page), through the TMDB cache, and append the
results after the close local ones, interleaved by seed. It MUST drop `adult`
results, results with fewer than 10 votes or no poster, the seeds and anything
already among the candidates. It MUST NOT make more than 6 TMDB calls per
request. A TMDB failure MUST leave the local results and MUST NOT be an error.
Shown TMDB results MUST be enqueued for materialization.

#### Scenario: Niche title

- GIVEN a title with 4 local neighbours under the threshold
- WHEN its similar titles are asked for
- THEN the 4 come first and TMDB recommendations follow

#### Scenario: TMDB down

- GIVEN TMDB fails
- WHEN a fill is needed
- THEN the answer is 200 (OK) with the local candidates only

### Requirement: Pool, shuffle and pages

The engine MUST build a pool of at most 60 titles, shuffled with weights that
favour the closest, using a seed derived from the cache key, so the same key
always gives the same order. Pages MUST be slices of 10 of the pool after
removing the per-user exclusions.

#### Scenario: Refresh

- GIVEN a pool of 60 and a user with none of them in «Vistas»
- WHEN pages 1 and 2 are asked for
- THEN they hold 10 different titles each, without recomputing the pool

### Requirement: Title page endpoint

`GET /api/catalogo/{movie|tv}/{id_tmdb}/similar/` MUST answer with and without
a session, with the `catalogo` throttle, and return up to 20 results. The pool
MUST be cached per title, language and model, and MUST NOT depend on the user.
With a session, the user's «Vistas» MUST be removed after the cache and the
answer MUST be `Cache-Control: private`; without one, nothing is removed and
the answer is `public, max-age=300` with `Vary: Accept-Language`. A title that
is not in the local catalog or has no vector MUST get TMDB results only, with
a 10-minute cache.

#### Scenario: Anonymous visitor

- GIVEN no session
- WHEN `/api/catalogo/movie/157336/similar/` is asked for
- THEN up to 20 movies and shows are returned, nothing excluded

#### Scenario: Watched titles

- GIVEN a user with one of the similar titles in «Vistas»
- WHEN they open the same title page
- THEN that title is not returned, and another user still gets it

### Requirement: List suggestions endpoint

`GET /api/lists/{id}/suggestions/?pagina=N` MUST require a session and MUST
answer 404 (Not Found) `not_found` for a list of another user, an inactive
list, Pendientes and Vistas. `pagina` MUST be an integer ≥ 1 (default 1);
anything else MUST answer 400 (Bad Request). The answer MUST be `{results,
pagina, paginas, nombre_usado}`, each result with `id_tmdb`, `tipo`, `titulo`,
`poster`, `anio`, `calificacion_promedio`, `campos_en_ingles` and `origen`.
The pool MUST be cached under a signature of the model, the language, the
normalized name and the list's productions; «Vistas» MUST be removed after the
cache. An empty list MUST answer 200 (OK) with no results and no TMDB call.

#### Scenario: Adding an item

- GIVEN a cached pool for list 4
- WHEN an item is added to list 4
- THEN the next request computes a new pool

#### Scenario: Rating a title

- GIVEN a cached pool for list 4
- WHEN the user rates a title, which adds it to «Vistas»
- THEN the pool is reused and that title is no longer in the pages

#### Scenario: Someone else's list

- GIVEN list 9 belongs to another user
- WHEN `/api/lists/9/suggestions/` is asked for
- THEN the answer is 404 (Not Found)
