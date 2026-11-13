# Delta for tmdb-endpoints

## ADDED Requirements

### Requirement: Suggestions (13/11/2026)

`GET /api/catalogo/suggest/` MUST be public, take `q` (trimmed, 2 to 50 characters; otherwise 400 (Bad Request) with `min_length` or `max_length`) and `tipo` (`all` by default, or `person`; otherwise 400 `invalid_choice`), and answer `{results}` with at most 5 items, each with `media_type`. It MUST make one TMDB call, `search/multi` page 1 without adult content, cached for 1 hour like `search`, and MUST keep TMDB's order:

- movies and shows that pass the relevance rule of Buscar (5 votes or more, popularity 5 or more, or a title equal to the text); if none of them passes, the titles as received;
- at most 2 people whose `known_for_department` is `Acting` or `Directing` and whose popularity is 1 or more, each with `rol` (`actor` or `director`), `gender` and `profile_path`.

With `tipo=person` it MUST return only people, up to 5. In Spanish it MUST fill only empty titles and names from English. It MUST NOT enqueue the materialization of its results. It MUST use its own throttle scope `sugerencias` (120 requests per minute per IP) and count its TMDB calls in the existing caps.

#### Scenario: A person query

- GIVEN TMDB's `search/multi` for «nolan» puts Christopher Nolan (Directing, popularity 9.2) first and «Nolan Yee» (Crew, 0.1) later
- WHEN `suggest/?q=nolan` is requested
- THEN the first result is Christopher Nolan with `rol: "director"`
- AND «Nolan Yee» is not in the results

#### Scenario: Too short

- GIVEN `suggest/?q=a`
- THEN the answer is 400 with `min_length`

#### Scenario: Cached

- GIVEN `suggest/?q=dune` was answered a minute ago
- WHEN it is requested again
- THEN no call reaches TMDB

### Requirement: Person filter in Buscar (13/11/2026)

`GET /api/catalogo/browse/` MUST accept `persona` (a positive TMDB person id; otherwise 400 `invalid`) and `rol` (`director` or `actor`; absent means both; otherwise 400 `invalid_choice`). With `persona` it MUST read the person's `combined_credits` (cached 24 h) and keep, for `actor`, the cast without shows in News or Talk (10763, 10767), and for `director`, the crew with `job` «Director» in movies and «Creator» in shows. It MUST drop duplicates by type and id, apply type, genre, year, `a_estrenar`, `decada` and rating in memory as with text, keep only titles whose `title`, `name`, `original_title` or `original_name` contains `q` (normalized: lowercase, without accents, spaces collapsed) when there is text, and sort and paginate like a text search. The answer MUST add `persona: {id, name, rol, gender, profile_path}` read from TMDB's `person/{id}` (cached 24 h). An id TMDB does not know MUST answer 404 (Not Found) with `person_not_found`. TMDB's `discover` with `with_people` MUST NOT be used (TMDB ignores it for shows).

#### Scenario: Directed by Vince Gilligan

- GIVEN Gilligan's credits list Breaking Bad as `Creator` and «The X-Files» only as an episode `Director`
- WHEN `browse/?persona=66633&rol=director&tipo=tv` is requested
- THEN Breaking Bad is in the results and «The X-Files» is not

#### Scenario: Cheap after the first time

- GIVEN `browse/?persona=525` was requested once
- WHEN `browse/?persona=525&genero=878&page=2` is requested
- THEN no call reaches TMDB

## MODIFIED Requirements

### Requirement: Buscar combina discover y search (C-06)

`GET /api/catalogo/browse/` MUST accept `q` (any text, trimmed; empty means no text; longer than 50 → 400 `max_length`), `tipo` (`all` by default, `movie`, `tv`), `genero`, `anio`, `nota` (`9+`, `8+`, `7+`, `6+`, `5+`, `m5`), `a_estrenar` (`true`: only what premieres after today, replacing `anio`), `decada` (1900, 1910… up to the current decade: from January 1st of its first year to December 31st of its last, replacing `anio`; anything else → 400 `invalid_choice`), `persona` and `rol` («Person filter in Buscar») and `page` (1–500). It MUST answer `{page, total_pages, total_results, results}` with `media_type` on every item, and `total_pages` capped at 500.

- Without text it MUST use `discover` sorted by popularity, with at least 50 votes, except for a future year or `a_estrenar` without a rating filter (announced titles have no votes); `a_estrenar` sends `primary_release_date.gte` / `first_air_date.gte` with tomorrow's date; shows MUST exclude News and Talk unless a genre is chosen.
- With text it MUST read up to the first 5 TMDB `search` pages per type (sending the year as `primary_release_year` or `first_air_date_year`), keep the items that pass the filters, and sort all of them — movies and shows together in `all` — by `max(vote_count, popularity × 100)`, descending, keeping TMDB's order on ties; pages hold 20 per type (40 in `all`). TMDB's relevance order puts titles with no votes first, and an upcoming title with high popularity must not sink (decided 14/10/2026).
- Genre, rating, `a_estrenar` and `decada` MUST be filtered on those items (by release date for `a_estrenar` and `decada`, without a date out; rating with at least 50 votes). A TMDB error in any page MUST fail the request, never return a partial count.
- **Relevance cut (13/11/2026)**: with text or `persona`, after the filters and before paginating, it MUST leave out the items with fewer than 5 votes and popularity under 5, unless their `title`, `name`, `original_title` or `original_name`, normalized (lowercase, without accents, spaces collapsed), equals the normalized text. If no item passes, all of them MUST be kept. `total_results` and `total_pages` MUST count only what is kept; there is no way to ask for what was left out. `video`, the synopsis and `adult` MUST NOT be used as signals. It makes no extra TMDB call.
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

#### Scenario: Irrelevant titles are left out

- GIVEN «chihiro» matches 13 titles and only 3 have 5 votes or popularity 5
- WHEN `browse/?q=chihiro` is requested
- THEN `total_results` is 3
- AND «La arquitectura de El Viaje de Chihiro» (1 vote, popularity 0.2) is not in any page

#### Scenario: The exact title is kept

- GIVEN a film titled «Sato no Chihiro» with 1 vote and popularity 0.1
- WHEN `browse/?q=sato no chihiro` is requested
- THEN it is in the results

#### Scenario: Nothing passes the cut

- GIVEN every match of a text has fewer than 5 votes and popularity under 5 and none is named as the text
- WHEN it is searched
- THEN all matches are returned
