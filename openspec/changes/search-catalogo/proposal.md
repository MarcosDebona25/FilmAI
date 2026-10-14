# Proposal: Buscar (C-06)

## Intent

The navbar and the mobile tab bar link to `/search`, and it answers 404 (Not
Found). Search is the second way into the catalog after the Home: the user
types a title or browses with filters (type, genre, year, TMDB rating), and
every card leads to the title page (C-07), whose breadcrumb already accepts
`?from=search`.

C-06 builds the page following the canvas artboards «Search · desktop» and
«Search · mobile» (section 5).

## The TMDB constraint that shapes it

Verified against TMDB on 14/10/2026:

- `search/movie` and `search/tv` take text and a year, but **ignore genre and
  rating**: «dune» with `with_genres=878&vote_average.gte=9` still answers its
  1,115 results.
- `discover` takes every filter but **no text**.
- `search/multi` mixes movies and shows but also people (9 of 20 on page 1 of
  «dune»), and its total counts them.
- The search year filter must be `primary_release_year` (movies) or
  `first_air_date_year` (shows): `year` is loose («dune», 2021 → the 1984 one).
- Movie and show genres share only 8 ids; Action, Adventure, Science Fiction,
  Fantasy and War have show counterparts under other ids.

So a new endpoint composes the right TMDB calls for each combination, instead
of the frontend juggling them.

## Scope

### In Scope

Backend:

- `GET /api/catalogo/browse/?q=&tipo=all|movie|tv&genero=&anio=&nota=&page=`
  - **No text**: `discover`, sorted by popularity, with every filter.
  - **Text, no genre or rating**: `search/movie` and/or `search/tv`, with the
    year sent to TMDB. One call per type.
  - **Text with genre or rating** (decided with the user on 14/10/2026): the
    first 100 TMDB matches per type (up to 5 pages, page 1 first and the rest in
    parallel, all cached 1 h), filtered here, paginated 20 per type.
  - **«All»**: page N of movies and page N of shows, alternated like the Home
    (up to 40 per page). Totals add up.
  - Genre in «All» maps movie genres to their show counterparts.
  - Rating: «N or higher» and «Below 5», always with at least 50 votes.
- `GET /api/catalogo/genres/?tipo=all`: movie genres plus the show-only ones
  with no movie counterpart (Kids, News, Reality, Soap, Talk).
- `q` accepts any text, trimmed, up to 50 characters (decided with the user on
  14/10/2026; doc 02 said alphanumeric only).

Frontend:

- `/search` as a page (the canvas draws it with the navbar and «Search» as the
  current item; doc 04 described an overlay): big search field, «Close Esc»,
  type selector, Genre/Year/Rating, results count, responsive grid of
  MediaCards, Previous / Page X of Y / Next.
- States: popular titles (no text, no filters), results, empty («Nothing for
  “q”» + «Clear filters»), error + Retry, loading skeleton.
- State in the URL (`q`, `type`, `genre`, `year`, `rating`, `page`): reload,
  share and Back keep the search. Typing waits 350 ms before asking.
- Mobile: «Search» heading, field, type selector and a «Filters» button with a
  badge of active filters that opens a bottom sheet (Genre, Year, TMDB rating,
  Clear, Show results).
- Cards go to the title page with `?from=search`; its breadcrumb «Search»
  returns to the last search, not to an empty one.

### Out of Scope

- Materializing the productions that the search exposes (C-04a's pending item
  for listings).
- Semantic search (chatbot, B-06).
- A «Where to watch» block on the title page: proposed on 14/10/2026, to be
  decided after C-06.

## Risks

| Risk                                                              | Mitigation                                                                                          |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| First uncached text+filter search fans out to up to 10 TMDB calls | Page 1 first, then the rest in parallel; each page cached 1 h; most queries have fewer than 5 pages |
| «100 results» understates a broad query («love» has 10,000)       | Only when genre or rating are on; documented; the count says what it filtered                       |
| Genre lists differ by type                                        | Backend owns the mapping; the frontend asks `genres/?tipo=all`                                      |
