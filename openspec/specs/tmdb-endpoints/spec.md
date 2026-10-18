# tmdb-endpoints Specification

## Purpose

Read-only DRF REST layer exposing the catalog to the frontend via `/api/catalogo/*`. Each endpoint wraps one `TMDBClientCache` method and returns raw TMDB JSON unchanged (passthrough serialization). Public (no auth). Covers C-03 only; DTO mapping (C-04a) and mutations (C-08) are out of scope.

## Requirements

### Requirement: Endpoint surface

The system MUST expose read-only `GET` endpoints, each delegating to a `TMDBClientCache` method.

| Endpoint | Cache method |
|---|---|
| `GET /api/catalogo/trending/` | `get_trending` |
| `GET /api/catalogo/now-playing/` | `get_now_playing` |
| `GET /api/catalogo/discover/` | `discover` |
| `GET /api/catalogo/search/` | `search` |
| `GET /api/catalogo/movie/{id_tmdb}/` | `get_movie_detail` |
| `GET /api/catalogo/tv/{id_tmdb}/` | `get_tv_detail` |
| `GET /api/catalogo/keywords/` | `get_keywords` |
| `GET /api/catalogo/{movie,tv}/{id_tmdb}/credits/` | `get_credits` (and `get_tv_detail` for shows) |
| `GET /api/catalogo/{movie,tv}/{id_tmdb}/providers/?pais=XX` | `get_watch_providers` |

The credits endpoint (C-07) is the only one that reshapes TMDB's JSON: `{"directores": [...], "reparto": [{"nombre", "personaje"}]}`, at most 50 cast members in TMDB's order. For movies the directors are the crew with `job == "Director"`; for shows, the detail's `created_by`, because TMDB has no series-level director.

The providers endpoint is public and reshapes TMDB's `watch/providers` into `{"pais", "enlace", "suscripcion", "gratis", "alquiler", "compra"}`. Each group is a list of `{"id", "nombre", "logo"}` (`logo` is TMDB's `logo_path`), sorted by `display_priority` and without repeats; `gratis` joins TMDB's `free` and `ads`. `enlace` is TMDB's `link` for the country, or `null` when the country has no providers. `pais` MUST be an ISO 3166-1 alpha-2 code from `contracts/enums.json` (`paisCodes`); if it is missing or not in the list the endpoint MUST answer 400 (Bad Request) with the code `country_invalid` and not call TMDB. The country is sent by the client (not read from the session) so the endpoint stays public and cacheable.

#### Scenario: Providers for a country

- GIVEN TMDB lists Netflix as `flatrate` and Tubi as `free` and `ads` for AR
- WHEN `GET /api/catalogo/movie/157336/providers/?pais=AR` is called
- THEN `suscripcion` has Netflix and `gratis` has Tubi once

#### Scenario: Country without data

- GIVEN TMDB has no entry for the requested country
- WHEN the providers endpoint is called with it
- THEN the four groups are empty and `enlace` is `null`

#### Scenario: Missing or invalid country

- WHEN `pais` is absent or not in `paisCodes`
- THEN the response is 400 (Bad Request) with `country_invalid` on `pais`

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

#### Scenario: Discover with a minimum of votes (C-05)

- GIVEN `/api/catalogo/discover/` with `tipo=tv&min_votes=50`
- WHEN the endpoint handles it
- THEN `discover` is invoked with `min_votos=50`, sent to TMDB as `vote_count.gte=50`
- AND the cache key includes it, so the same query without the minimum is a different entry
- AND `min_votes=0` or a non-integer answers 400 without calling the service

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

### Requirement: Detail views materialize as a side effect

Added by C-04a (2026-09-15). The detail endpoints MUST materialize the production they serve, by calling `catalogo.services.materialization.materializar(id_tmdb, tipo_tmdb)` after resolving the response.

This MUST NOT alter the response contract defined above: the body stays the raw TMDB passthrough. A materialization failure MUST be logged and swallowed, never surfaced to the client — the catalog remains readable even when local persistence is degraded.

#### Scenario: Row exists after a detail request

- GIVEN `GET /api/catalogo/movie/550/` or `GET /api/catalogo/tv/1396/`
- WHEN the request succeeds
- THEN the response body is unchanged TMDB JSON
- AND a `ProduccionAudiovisual` row exists for that `(id_tmdb, tipo)`
- AND a `ProduccionEmbedding` exists for it in state `pending`

#### Scenario: Materialization failure is invisible to the client

- GIVEN materialization raises
- WHEN the detail endpoint handles the request
- THEN the client still receives 200 with the unchanged TMDB body

### Requirement: Idioma en vistas públicas (OT-60)

Tendencias, estrenos, descubrimiento, búsqueda y detalles MUST resolver
`Accept-Language` con el núcleo de idioma y seleccionar `en-US`/`es-MX`.
Estas vistas públicas mantienen autenticación deshabilitada y por tanto usan
encabezado/default, sin consultar una cuenta. Keywords MUST conservar su
contrato global. La materialización MUST seguir usando el servicio canónico
inglés. El fallback de campos vacíos se entrega en OT-61.

#### Scenario: Caché separada desde HTTP

- GIVEN la misma URL de detalle consultada en EN y ES
- WHEN cada consulta se repite
- THEN cada respuesta respeta su idioma y reutiliza su propia entrada Redis
- AND la materialización recibe solamente identificador y tipo

### Requirement: Respaldo en inglés y géneros por idioma (OT-61, OT-63)

Fuera del inglés, los detalles y cada ítem de tendencias, estrenos,
descubrimiento y búsqueda MUST incluir `campos_en_ingles`: la lista de campos
(`title`, `name`, `overview`) que llegaron vacíos y se completaron con la
versión inglesa. El respaldo MUST pedirse solo si falta algún campo, pasar por
la misma caché y no pisar valores no vacíos; en listados se pide la misma
página en inglés y se combina por (`media_type`, `id`). En inglés el cuerpo de
TMDB MUST quedar sin esa clave. `GET /api/catalogo/genres/?tipo=movie|tv` MUST
devolver `{"genres": [{id, name}]}` en el idioma efectivo, completando con
inglés los nombres vacíos.

#### Scenario: Sinopsis ausente en español

- GIVEN TMDB devuelve `overview` vacío con `es-MX` y no vacío con `en-US`
- WHEN se pide el detalle con `Accept-Language: es`
- THEN `overview` trae el texto inglés y `campos_en_ingles` es `["overview"]`
- AND una segunda solicitud no vuelve a llamar a TMDB

### Requirement: Buscar combina discover y search (C-06)

`GET /api/catalogo/browse/` MUST accept `q` (any text, trimmed; empty means no text; longer than 50 → 400 `max_length`), `tipo` (`all` by default, `movie`, `tv`), `genero`, `anio`, `nota` (`9+`, `8+`, `7+`, `6+`, `5+`, `m5`), `a_estrenar` (`true`: only what premieres after today, replacing `anio`), `decada` (1900, 1910… up to the current decade: from January 1st of its first year to December 31st of its last, replacing `anio`; anything else → 400 `invalid_choice`) and `page` (1–500). It MUST answer `{page, total_pages, total_results, results}` with `media_type` on every item, and `total_pages` capped at 500.

- Without text it MUST use `discover` sorted by popularity, with at least 50 votes, except for a future year or `a_estrenar` without a rating filter (announced titles have no votes); `a_estrenar` sends `primary_release_date.gte` / `first_air_date.gte` with tomorrow's date; shows MUST exclude News and Talk unless a genre is chosen.
- With text it MUST read up to the first 5 TMDB `search` pages per type (sending the year as `primary_release_year` or `first_air_date_year`), keep the items that pass the filters, and sort all of them — movies and shows together in `all` — by `max(vote_count, popularity × 100)`, descending, keeping TMDB's order on ties; pages hold 20 per type (40 in `all`). TMDB's relevance order puts titles with no votes first, and an upcoming title with high popularity must not sink (decided 14/10/2026).
- Genre, rating, `a_estrenar` and `decada` MUST be filtered on those items (by release date for `a_estrenar` and `decada`, without a date out; rating with at least 50 votes). A TMDB error in any page MUST fail the request, never return a partial count.
- Without text, `all` MUST alternate movies and shows and add their totals. A genre MUST be mapped to its show id when TMDB uses another one (28 and 12 → 10759, 878 and 14 → 10765, 10752 → 10768); a genre with no counterpart MUST leave that side empty without calling TMDB for it.

`GET /api/catalogo/genres/?tipo=all` MUST return the movie genres followed by the show-only ones with no movie counterpart (10762, 10763, 10764, 10766, 10767).

#### Scenario: Text and genre on «All»

- GIVEN «dune» with genre 878
- WHEN `browse/?q=dune&genero=878` is requested
- THEN movies are filtered by 878 and shows by 10765 within the first 5 pages of each
- AND the results alternate movie and show

#### Scenario: Default grid

- GIVEN no text and no filters
- WHEN `browse/?tipo=tv` is requested
- THEN `discover/tv` is called with `vote_count.gte=50` and `without_genres=10763,10767`
