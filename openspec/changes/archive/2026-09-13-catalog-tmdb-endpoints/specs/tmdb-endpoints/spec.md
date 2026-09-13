# tmdb-endpoints Specification

## Purpose

Read-only DRF REST layer exposing the catalog to the frontend via `/api/catalogo/*`. Each endpoint wraps one `TMDBClientCache` method and returns raw TMDB JSON unchanged (passthrough serialization). Public (no auth). Covers C-03 only; DTO mapping (C-04a) and mutations (C-08) are out of scope.

## Requirements

### Requirement: Endpoint surface

The system MUST expose seven read-only `GET` endpoints, each delegating to exactly one `TMDBClientCache` method.

| Endpoint | Cache method |
|---|---|
| `GET /api/catalogo/trending/` | `get_trending` |
| `GET /api/catalogo/now-playing/` | `get_now_playing` |
| `GET /api/catalogo/discover/` | `discover` |
| `GET /api/catalogo/search/` | `search` |
| `GET /api/catalogo/movie/{id_tmdb}/` | `get_movie_detail` |
| `GET /api/catalogo/tv/{id_tmdb}/` | `get_tv_detail` |
| `GET /api/catalogo/keywords/` | `get_keywords` |

#### Scenario: Raw JSON passthrough

- GIVEN a cache method returns TMDB JSON
- WHEN its endpoint is called
- THEN the response body is that JSON unchanged
- AND only `GET` is accepted on these routes

### Requirement: Parameter pass-through

The system MUST forward each query/path parameter to the matching cache-method argument, coercing `id_tmdb` to an integer and validating `tipo` (if present) is 'movie' or 'tv'.

#### Scenario: Discover filters

- GIVEN `/api/catalogo/discover/` with `tipo=movie&genero=28&anio=2024&min_rating=7.5`
- WHEN the endpoint handles it
- THEN `discover("movie", genero=28, anio=2024, min_rating=7.5, page=...)` is invoked

#### Scenario: Search params

- GIVEN `/api/catalogo/search/` with `query=Inception&tipo=movie`
- WHEN the endpoint handles it
- THEN `search("Inception", "movie", page=...)` is invoked

#### Scenario: Trending params

- GIVEN `/api/catalogo/trending/` with `media_type=tv&time_window=day`
- WHEN the endpoint handles it
- THEN `get_trending("tv", "day", page=...)` is invoked

#### Scenario: Detail path params

- GIVEN `/api/catalogo/movie/550/`, `/api/catalogo/tv/550/`, or `/api/catalogo/keywords/` with `id_tmdb=550&tipo=movie`
- WHEN the endpoint handles it
- THEN the matching detail/keywords method is invoked with `id_tmdb=550`
- THEN the matching detail/keywords method is invoked with the provided path and query parameters
#### Scenario: Invalid params rejected

- GIVEN a non-integer `id_tmdb` or an unsupported `tipo`
- WHEN the endpoint handles it
- THEN HTTP 400 is returned without calling TMDB

### Requirement: Error mapping

The system MUST map `TMDBError` subclasses to HTTP statuses via a DRF exception handler.

| Exception | HTTP |
|---|---|
| `TMDBNotFound` | 404 |
| `TMDBBadRequest` | 400 |
| `TMDBRateLimited` | 429 |
| `TMDBServerError` | 502 or 503 |
| `TMDBTransportError` | 502 or 503 |

#### Scenario: Not found

- GIVEN the cache method raises `TMDBNotFound`
- WHEN the endpoint handles it
- THEN the status is 404

#### Scenario: Rate limited

- GIVEN the cache method raises `TMDBRateLimited`
- WHEN the endpoint handles it
- THEN the status is 429

#### Scenario: Bad request

- GIVEN the cache method raises `TMDBBadRequest`
- WHEN the endpoint handles it
- THEN the status is 400

#### Scenario: Server or transport error

- GIVEN the cache method raises `TMDBServerError` or `TMDBTransportError`
- WHEN the endpoint handles it
- THEN the status is 502 or 503 (exact split resolved in design)

### Requirement: Public access

The system MUST allow unauthenticated access to all catalog endpoints; no permission beyond `AllowAny` SHALL be required.

#### Scenario: Anonymous request

- GIVEN an unauthenticated client
- WHEN any catalog endpoint is called
- THEN the request is processed without an auth challenge

### Requirement: Pagination passthrough

The system MUST forward the `page` query parameter to the cache method and return TMDB's own pagination shape without applying DRF pagination.

#### Scenario: Page forwarded

- GIVEN a list request with `page=3`
- WHEN the endpoint handles it
- THEN `page=3` is passed to the cache method
- AND TMDB's own `page`, `total_pages`, `results` fields are returned unchanged
