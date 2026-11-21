# search-ui Specification

## Purpose

The Search page (C-06, CU-008 and CU-010): typing a title or browsing the catalog with filters, following the canvas artboards «Search · desktop» and «Search · mobile». It builds on `GET /api/catalogo/browse/` (`tmdb-endpoints`, «Buscar combina discover y search») and links every card to the title page (`title-page-ui`).

## Requirements

### Requirement: Page and state

`/search` MUST render the Search page, public like the Home and the title page. The search MUST live in the URL (`q`, `type`, `genre`, `year`, `rating` as `9`…`5` or `lt5`, `person`, `role` as `director` or `actor`, `page`) and change through `history.replaceState`, so reload and share keep it and Back leaves Search. Any change except the page itself MUST go back to page 1. Titles left out by the relevance cut (`tmdb-endpoints`) MUST NOT be offered behind any button or link (Gonza, 13/11/2026).

#### Scenario: Reload keeps the search

- GIVEN `/search?q=dune&genre=878&page=2`
- WHEN the page loads
- THEN it asks `browse/?q=dune&tipo=all&genero=878&page=2`

#### Scenario: Reload with a person

- GIVEN `/search?person=66633&role=director&type=tv`
- WHEN the page loads
- THEN it asks `browse/?tipo=tv&persona=66633&rol=director&page=1`

### Requirement: Field and closing

The field MUST look like the navbar magnifier field (same pill, colors, border, radius, 2.75 rem height, icon, focus ring, placeholder and clear button, from `components/campo-busqueda.ts`) on desktop and mobile (21/11/2026). The field MUST accept any text up to 50 characters and search 350 ms after the last keystroke, or at once on Enter. On desktop it MUST take the focus; on mobile it MUST NOT. «Close» and Escape MUST go back when the user arrived from inside the app and to Home when `/search` was opened directly; with a dialog open, Escape belongs to the dialog.

#### Scenario: Typing waits

- GIVEN the user types «dun» and then «dune» within 350 ms
- THEN only `?q=dune` reaches the URL, once

### Requirement: Field suggestions (14/11/2026)

The field MUST suggest like the navbar magnifier (`navbar-search`): the same `suggest/` request, timings (250 ms after the last keystroke, from 2 characters), per-language cache, groups «People» and «Titles», keyboard, ARIA 1.2 combobox with `aria-activedescendant` and polite live region, and a list that closes on Escape (first Escape), Tab, blur or an error. The list MUST open under the field without moving the chip or the filters, and MUST NOT end with «See all results» (the page already shows them). Choosing a person MUST set `person` and `role` and remove the text (field and `q`), keeping the other filters; choosing a title MUST open `/{type}/{id}?from=search`. Enter with no active option MUST close the list and search the text in titles as before: a title called «Nolan» has to stay searchable. The field MUST keep searching while the user types.

#### Scenario: Choosing a person

- GIVEN `/search?q=ryan&type=movie` and the list shows «Ryan Gosling · Actor»
- WHEN the user picks it
- THEN the URL becomes `/search?type=movie&person=30614&role=actor`
- AND the field is empty and the chip reads «Ryan Gosling · Actor»

#### Scenario: Choosing a title

- GIVEN the list shows «Drive · Movie · 2011»
- WHEN the user picks it
- THEN the page is `/movie/64690?from=search`

#### Scenario: Enter searches the text

- GIVEN the user typed «nolan» and the list is open with no active option
- WHEN the user presses Enter
- THEN the list closes and the URL is `/search?q=nolan`

### Requirement: «Looking for…?» notice (14/11/2026)

With text `q` and no person filter, above the results, the page MUST show one line «Looking for {name}? See their titles» (with a small photo and the role) when the `suggest/` answer for that same text (same function and cache as the field) has a person whose name, lowercased and without accents, contains every word of the text. Only the first matching person MUST be offered; with none, nothing. «See their titles» MUST be a real button that sets `person` and `role` and removes `q`.

#### Scenario: A name typed in the field

- GIVEN `/search?q=ryan+gosling` and `suggest/` returns «Ryan Gosling · Actor» first
- THEN a line reads «Looking for Ryan Gosling? See their titles · Actor»
- AND pressing «See their titles» makes the URL `/search?person=30614&role=actor`

#### Scenario: No notice

- GIVEN `/search?q=ryan+gosling` and only «Ryan Reynolds» comes back as a person
- THEN no «Looking for…» line is shown
- AND the same holds when `person` is already in the URL

### Requirement: Filters

The page MUST offer the type selector (All · Movies · TV shows), Genre (from `genres/?tipo=` of the current type), Year (Any, «Upcoming» — what premieres after today —, single years from the current one down to 1990, then decades «1980s» … «1900s») and TMDB rating (Any, 9 or higher … 5 or higher, Below 5). Changing the type MUST keep the genre only when it has the same id for movies and shows. The five show-only genres TMDB does not translate (Kids, News, Reality, Soap, Talk) MUST use the app's copy. On mobile the filters MUST live in a «Filters» sheet opened by a button that announces how many are active; each change applies at once and «Show results» closes it.

#### Scenario: Mobile sheet

- GIVEN a mobile viewport with genre and year chosen
- THEN the button reads «Filters, 2 active»
- AND choosing «Below 5» in the sheet adds `rating=lt5` to the URL


### Requirement: Person filter (13/11/2026)

A person reaches Search from a navbar suggestion (`navbar-search`), which sets `person` and `role` in the URL; a person is also reachable from the field's own suggestions and the «Looking for…?» notice (see «Field suggestions»); the separate «Person» field of the filters was dropped (`busqueda-navbar`, task 6.3). With a person, the page MUST show, above the results, a chip with the photo, «Name · Role» (role by TMDB gender: «Director» / «Directora», «Actor» / «Actriz», or «Dirección» / «Actuación» when unknown) and a ✕ button labelled «Remove filter {name}» that removes `person` and `role`. The name MUST come from the API's `persona`, never from the URL. A person MUST count as one active filter, MUST survive a change of type, and «Clear filters» MUST remove it. Without text, the count MUST read «N results for “{name}”». A `person_not_found` error MUST show the empty state with «Clear filters».

#### Scenario: From a navbar suggestion

- GIVEN the user picks «Christopher Nolan · Director» in the navbar
- THEN the page is `/search?person=525&role=director`
- AND the chip above the results reads «Christopher Nolan · Director»
- AND it asks `browse/?tipo=all&persona=525&rol=director&page=1`

#### Scenario: Removing the person

- GIVEN `/search?person=525&role=director&genre=878`
- WHEN the user presses the chip's ✕
- THEN the URL becomes `/search?genre=878`

#### Scenario: Combined with a type

- GIVEN `/search?person=525&role=director`
- WHEN the user chooses «TV shows»
- THEN the URL keeps `person=525&role=director`
- AND the page shows «Nothing with these filters» with «Clear filters»

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
