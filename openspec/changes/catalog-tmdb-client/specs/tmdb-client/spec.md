# tmdb-client Specification

## Purpose

Defines `TMDBClient`, a thin `httpx`-based wrapper over TMDB API v3 for live
catalog discovery. It returns raw parsed JSON — no Django model mapping (that is
C-04a). Auth is via the `api_key` query parameter. Covers C-01 only; Redis cache
(C-02), catalog endpoints (C-03), materialization + embedding (C-04a), Celery
sync (C-04b), and all UI work are out of scope.

## Requirements

### Requirement: Configuration

The client MUST read settings via `decouple.config()`: `TMDB_API_KEY`,
`TMDB_API_BASE_URL` (base `https://api.themoviedb.org/3`), and `TMDB_TIMEOUT`
(default `5` seconds). Requests MUST authenticate by appending `api_key` as a
query parameter. `TMDB_TIMEOUT` MUST be added to `.env.example`.

#### Scenario: Default timeout when unset

- GIVEN `TMDB_TIMEOUT` is absent from the environment
- WHEN `TMDBClient` is instantiated
- THEN the request timeout is 5 seconds

#### Scenario: Explicit timeout

- GIVEN `TMDB_TIMEOUT=10`
- WHEN `TMDBClient` is instantiated
- THEN the request timeout is 10 seconds

#### Scenario: Auth query param

- GIVEN `TMDB_API_KEY=abc123`
- WHEN any client method builds a request
- THEN the URL includes `api_key=abc123`

### Requirement: Error Mapping

The client MUST raise a domain exception on HTTP errors or transport failures.
All exceptions MUST inherit from `TMDBError` (base). The mapping MUST be:

| Status | Exception |
|--------|-----------|
| 429 | `TMDBRateLimited` |
| 404 | `TMDBNotFound` |
| other 4xx | `TMDBBadRequest` |
| 5xx | `TMDBServerError` |
| network/transport | `TMDBTransportError` |

#### Scenario: Not found

- GIVEN TMDB returns a 404 response
- WHEN a detail method is called
- THEN `TMDBNotFound` is raised

#### Scenario: Server error

- GIVEN TMDB returns a 503 response
- WHEN any method is called
- THEN `TMDBServerError` is raised

### Requirement: Retry Policy

The client MUST retry only transitory errors — `429`, `5xx`, and
network/transport failures — with backoff honoring the `Retry-After` header. It
MUST NOT retry on other `4xx` responses. The number of retries MUST be bounded to
avoid infinite loops.

#### Scenario: Retry then success

- GIVEN the first request returns 429 with `Retry-After: 1`
- WHEN a method is called
- THEN it retries after the backoff delay and returns the parsed response

#### Scenario: No retry on 4xx

- GIVEN the request returns 400
- WHEN a method is called
- THEN `TMDBBadRequest` is raised without retrying

### Requirement: Discovery Methods

The client MUST provide `get_trending(media_type="all", time_window="week",
page=1)`, `get_now_playing(page=1)`, and `discover(tipo, genero, anio,
min_rating, page)`. Each MUST return parsed JSON.

| Method | Endpoint |
|--------|----------|
| `get_trending` | `/trending/{media_type}/{time_window}` |
| `get_now_playing` | `/movie/now_playing` |
| `discover` | `/discover/{tipo}` |

#### Scenario: Trending defaults

- GIVEN no arguments
- WHEN `get_trending()` is called
- THEN it requests `/trending/all/week` with `page=1`

#### Scenario: Discover filters

- GIVEN `tipo="movie"`, `genero=28`, `anio=2024`, `min_rating=7.5`, `page=1`
- WHEN `discover(...)` is called
- THEN it requests `/discover/movie` with query params for genre, year, min rating, and page

### Requirement: Search

The client MUST provide `search(query, tipo, page)` returning parsed JSON from
`/search/{tipo}`.

#### Scenario: Search movie

- GIVEN `query="Inception"`, `tipo="movie"`
- WHEN `search(...)` is called
- THEN it requests `/search/movie` with `query=Inception`

### Requirement: Detail Methods

The client MUST provide `get_movie_detail(id_tmdb)`, `get_tv_detail(id_tmdb)`,
and `get_keywords(id_tmdb, tipo)` returning parsed JSON.

| Method | Endpoint |
|--------|----------|
| `get_movie_detail` | `/movie/{id_tmdb}` |
| `get_tv_detail` | `/tv/{id_tmdb}` |
| `get_keywords` | `/{tipo}/{id_tmdb}/keywords` |

#### Scenario: Movie detail

- GIVEN `id_tmdb=550`
- WHEN `get_movie_detail(550)` is called
- THEN it requests `/movie/550`

### Requirement: Thin Client

The client MUST return raw parsed JSON and MUST NOT map responses to Django
models. Tests MUST use `httpx.MockTransport` (no real network calls).

#### Scenario: Raw JSON returned

- GIVEN a mocked TMDB response body
- WHEN any method is called
- THEN the parsed JSON body is returned unchanged
