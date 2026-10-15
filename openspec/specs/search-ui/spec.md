# search-ui Specification

## Purpose

The Search page (C-06, CU-008 and CU-010): typing a title or browsing the catalog with filters, following the canvas artboards «Search · desktop» and «Search · mobile». It builds on `GET /api/catalogo/browse/` (`tmdb-endpoints`, «Buscar combina discover y search») and links every card to the title page (`title-page-ui`).

## Requirements

### Requirement: Page and state

`/search` MUST render the Search page, public like the Home and the title page. The search MUST live in the URL (`q`, `type`, `genre`, `year`, `rating` as `9`…`5` or `lt5`, `page`) and change through `history.replaceState`, so reload and share keep it and Back leaves Search. Any change except the page itself MUST go back to page 1.

#### Scenario: Reload keeps the search

- GIVEN `/search?q=dune&genre=878&page=2`
- WHEN the page loads
- THEN it asks `browse/?q=dune&tipo=all&genero=878&page=2`

### Requirement: Field and closing

The field MUST accept any text up to 50 characters and search 350 ms after the last keystroke, or at once on Enter. On desktop it MUST take the focus; on mobile it MUST NOT. «Close» and Escape MUST go back when the user arrived from inside the app and to Home when `/search` was opened directly; with a dialog open, Escape belongs to the dialog.

#### Scenario: Typing waits

- GIVEN the user types «dun» and then «dune» within 350 ms
- THEN only `?q=dune` reaches the URL, once

### Requirement: Filters

The page MUST offer the type selector (All · Movies · TV shows), Genre (from `genres/?tipo=` of the current type), Year (Any, «Upcoming» — what premieres after today —, single years from the current one down to 1990, then decades «1980s» … «1900s») and TMDB rating (Any, 9 or higher … 5 or higher, Below 5). Changing the type MUST keep the genre only when it has the same id for movies and shows. The five show-only genres TMDB does not translate (Kids, News, Reality, Soap, Talk) MUST use the app's copy. On mobile the filters MUST live in a «Filters» sheet opened by a button that announces how many are active; each change applies at once and «Show results» closes it.

#### Scenario: Mobile sheet

- GIVEN a mobile viewport with genre and year chosen
- THEN the button reads «Filters, 2 active»
- AND choosing «Below 5» in the sheet adds `rating=lt5` to the URL

### Requirement: Results

The page MUST show a responsive grid of MediaCards (two columns on mobile) leading to `/{type}/{id}?from=search`, with «No ratings» for titles without votes, and a count «N results for “text”» (or «N results» without text) whenever there is text or a filter. More results MUST load as the user scrolls (decided 14/10/2026, replacing the canvas' Previous / Next): when the end of the grid is within 600 px, the next page is appended, up to 25 pages; repeated titles are dropped; a failed page keeps what was loaded and offers «Try again». `page` in the URL MUST mean how many pages are loaded, and coming back from the title page (Back or the crumb) MUST restore those pages from the cache and the scroll position. Without text or filters it shows the popular titles with no count.

States: loading skeleton; empty «Nothing for “text”» (or «Nothing with these filters») with «Clear filters», or «Clear search» when no filter is on; API error with «Try again».

#### Scenario: Empty with filters

- GIVEN `?q=dnue&genre=18` returns nothing
- WHEN the user presses «Clear filters»
- THEN the URL becomes `?q=dnue`

### Requirement: Return from the title page

Search MUST keep its last URL in `sessionStorage` for the tab; the title page's «Search» crumb (`?from=search`) MUST link to it, read after mounting. Without storage, or with a stored value that is not a Search URL, the crumb MUST link to `/search`.

#### Scenario: Back to the results

- GIVEN the user searched «interstellar» and opened a card
- THEN the title page's «Search» crumb links to `/search?q=interstellar`

#### Scenario: Loading more

- GIVEN `/search?q=batman` showing page 1
- WHEN the user scrolls near the end of the grid
- THEN the URL becomes `?q=batman&page=2` and page 2 is appended below
