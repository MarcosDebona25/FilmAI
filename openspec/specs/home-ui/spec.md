# home-ui Specification

## Purpose

The discovery Home at `/home` (C-05, doc 04 §5): a Hero, «Recommended for you», «Trending this week» and «New releases», with an `All · Movies · TV shows` selector. Public: a visitor without a session sees everything but the recommendations. Consumes the public catalog endpoints of `tmdb-endpoints` and, with a session, `recommendations-api`. Visual source of truth: the canvas artboards «Home · desktop» and «Home · mobile».

## Requirements

### Requirement: The selector lives in the URL

The selected type MUST be read from `?type=movie|tv`; any other value or none means All. Choosing an option MUST update the URL with the browser History API, without asking the server for the page again, so coming back from a title page keeps the selection.

#### Scenario: Choosing TV shows

- GIVEN the Home with All selected
- WHEN the user chooses TV shows
- THEN the URL becomes `/home?type=tv`
- AND the Hero and every row switch to TV shows

### Requirement: Hero rule

With All, the Hero MUST be the first trending title with a backdrop, labeled «#N trending» with its real position. With Movies or TV shows, it MUST be the first trending title of that type with a backdrop that is not the All Hero, labeled «Featured this week». Titles compare by type and id. The synopsis MUST be clamped to 3 lines on desktop; the only action is «View details», linking to `/movie/{id}` or `/tv/{id}`.

#### Scenario: Three different Heroes

- GIVEN a movie that is first in both trending/all and trending/movie
- WHEN the user switches from All to Movies
- THEN the Movies Hero is the next movie with a backdrop

### Requirement: The Hero comes in the server HTML (24/10/2026)

The page (`app/home/page.tsx`, a Server Component) MUST request what the Hero needs (trending of All and, with Movies or TV shows, of that type, plus both genre lists) from the backend before sending the HTML, in the page language, and hand it to `HomeView`. The HTML then carries the Hero title and the preload of its backdrop (the LCP), instead of waiting for the browser to request trending. The server reaches the backend through `API_URL_INTERNA` (`http://backend:8000` in Docker); without it nothing is requested on the server. The answers stay 5 minutes in Next's data cache. Any failure or a wait longer than 500 ms falls back to the browser requesting them, as before (the whole HTML waits for this request, but only when Next has no copy at all: a stale copy is served while it is renewed in the background). Data in another language than the one being viewed is ignored.

#### Scenario: Hero without a client request

- GIVEN the server got trending and genres
- WHEN `HomeView` renders for the first time
- THEN the Hero is there and the browser does not request trending or genres again
- AND the other rows are still requested by the browser

#### Scenario: Backend unavailable from the server

- GIVEN the server request fails or times out
- WHEN the page is sent
- THEN `HomeView` requests the Hero data from the browser, as before

### Requirement: Rows and their sources

| Row                        | All                                                                       | Movies                      | TV shows                                    |
| -------------------------- | ------------------------------------------------------------------------- | --------------------------- | ------------------------------------------- |
| Recommended (session only) | `recommended?tipo=all`                                                    | `recommended?tipo=movie`    | `recommended?tipo=tv`                       |
| Trending this week         | `trending?media_type=all`                                                 | `trending?media_type=movie` | `trending?media_type=tv`                    |
| New releases               | `now-playing` and `discover?tipo=tv&anio=<year>&min_votes=50`, alternated | `now-playing`               | `discover?tipo=tv&anio=<year>&min_votes=50` |

Trending and New releases MUST show at most one TMDB page (20); Recommended up to 15. Cards MUST show the type only with All. A row without titles MUST NOT render. The Recommended subtitle MUST name the genres the API returned, joined with `Intl.ListFormat` in the interface language.

#### Scenario: Visitor without a session

- GIVEN no session
- WHEN the Home loads
- THEN it shows the Hero, Trending, New releases and the «What have you watched lately?» callout with Sign up and Log in
- AND it never asks for `recommended`
- AND there is no «Ask FilmAI» button in the page body

#### Scenario: User with a session

- GIVEN a session
- THEN the Recommended row comes first when the API returns titles
- AND an «Ask FilmAI» floating button links to `/chat` (404 (Not Found) until B-04)

### Requirement: Failures

Each row MUST fetch its own data. A failed row MUST hide and the page MUST show a single toast with the translated error code. If every requested row fails, the page MUST show the translated error and a «Try again» button that asks again only for what failed.

#### Scenario: One row fails

- GIVEN `recommended` answers with an error and the other rows load
- WHEN the Home renders
- THEN Recommended is not shown and one toast says «The catalog couldn’t respond. Try again later.»

### Requirement: Layout

On desktop the site navbar MUST be drawn over the Hero backdrop, and the selector sits inside the Hero. On mobile the selector sits between the navbar and the Hero, and the Hero meta puts year and rating on one line and the genres on the next. Rows scroll horizontally inside themselves and MUST NOT widen the page at any width.

The Hero title size MUST depend on its length in characters: up to 16 keeps the canvas size (152 px desktop, 72 px mobile), 17 to 28 uses 112/56 px and longer titles 88/44 px, always with a 0.9 line height and balanced lines.

#### Scenario: A long title on desktop

- GIVEN a 33-character Hero title («Law & Order: Special Victims Unit»)
- THEN it takes at most two lines
- AND its label stays at least 40 px below the selector

#### Scenario: Twenty cards on a phone

- GIVEN a row with 20 titles at 390 px
- THEN the document is not wider than the viewport
