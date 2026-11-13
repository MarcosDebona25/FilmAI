# Delta for search-ui

## ADDED Requirements

### Requirement: Person filter (13/11/2026)

The filters (desktop row and mobile sheet) MUST offer a «Person» field with suggestions of people from `suggest/?tipo=person`, with the keyboard and announcements of `navbar-search`. Choosing someone MUST set `person` and `role` in the URL. With a person, the page MUST show, above the results, a chip with the photo, «Name · Role» (role by TMDB gender: «Director» / «Directora», «Actor» / «Actriz», or «Dirección» / «Actuación» when unknown) and a ✕ button labelled «Remove filter {name}» that removes `person` and `role`. The name MUST come from the API's `persona`, never from the URL. A person MUST count as one active filter, MUST survive a change of type, and «Clear filters» MUST remove it. Without text, the count MUST read «N results for “{name}”». A `person_not_found` error MUST show the empty state with «Clear filters».

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

## MODIFIED Requirements

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
