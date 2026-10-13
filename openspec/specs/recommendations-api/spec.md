# recommendations-api Specification

## Purpose

«Recommended for you», the row of the Home (C-05) built from what the user rated highly. Algorithmic, through TMDB `discover`, with no LLM involved (doc 04 §3.3). Reads `Calificacion` (from `reviews-api`) and the `Vistas` list (from `list-endpoints`), and calls TMDB through the cache of `tmdb-cache`. Design in `openspec/changes/home-catalogo/design.md` §2.

## Requirements

### Requirement: Only for an authenticated user

`GET /api/catalogo/recommended/` MUST require a session. Without one it MUST answer 401 (Unauthorized) with `code: "not_authenticated"`. It shares the `catalogo` throttle (60/min) with the public catalog endpoints.

#### Scenario: Anonymous visitor

- GIVEN a request without a session
- WHEN it asks for `/api/catalogo/recommended/`
- THEN the response is 401 with `code: "not_authenticated"`

### Requirement: Genres come from ratings of 7 or more, per type

For each type, the endpoint MUST count the `generos_ids` of the productions of that type the user rated with 7 or more in an active rating, and keep the 3 most frequent. A tie MUST go to the genre of the most recent rating. Movies only use movie ratings and shows only show ratings: TMDB names genres differently per type.

#### Scenario: The three most repeated genres

- GIVEN a user whose movie ratings of 7+ have Drama 3 times, Thriller 2, Crime 2 and Comedy 1
- WHEN they ask for `tipo=movie`
- THEN TMDB `discover` is asked for movies with `with_genres` Drama, Thriller and Crime joined with `|` (OR)
- AND sorted by `popularity.desc` with `vote_count.gte=100`

#### Scenario: Nothing rated highly

- GIVEN a user whose only ratings are below 7, or inactive
- WHEN they ask for recommendations
- THEN the response is 200 with `{"generos": [], "results": []}`
- AND TMDB is not called

### Requirement: Titles already watched are left out

Results MUST exclude the `(id_tmdb, tipo)` pairs of the user's `Vistas` list. With "a rated production is in `Vistas`" this also excludes everything rated. `Pendientes` MUST NOT be excluded. The comparison MUST use the pair, because TMDB numbers movies and shows separately.

#### Scenario: Watched versus watchlist

- GIVEN a recommended movie in `Vistas` and another in `Pendientes`
- WHEN the user asks for recommendations
- THEN the first is not returned and the second is

### Requirement: Shape, size and mixing

The response MUST be `{"generos": [...], "results": [...]}`. Each result keeps TMDB's shape plus `media_type` (`movie` or `tv`), like `trending/all`, and the `campos_en_ingles` mark of the localized catalog. At most 15 results come from TMDB's first page. `tipo` is `all` (default), `movie` or `tv`; anything else answers 400 (Bad Request) with `invalid_choice` on `tipo`. With `all`, results MUST alternate movie and show, and when one type runs out the other fills in.

`generos` MUST hold the names, in the request's language, of the genres used, ordered by count and capped at 3. With `all`, the counts of both types add up.

#### Scenario: Mixed row

- GIVEN a user with high ratings of both types
- WHEN they ask for `tipo=all`
- THEN results go movie, show, movie, show… and the longer list fills the end

#### Scenario: Genre names in Spanish

- GIVEN a request with `Accept-Language: es` and high ratings of Thriller and Crime
- WHEN the user asks for `tipo=movie`
- THEN `generos` is `["Suspense", "Crimen"]`, the names TMDB uses in `es-MX`
