# Delta for title-page-ui

## ADDED Requirements

### Requirement: More like this title

The title page MUST show, after «Director and cast» and before the reviews, a
horizontal row «More like {title}» with the results of
`GET /api/catalogo/{tipo}/{id}/similar/`, with and without a session. Each
card MUST show its type. The request MUST start only when the row is about
400 px from the viewport, never with the detail: the detail MUST NOT wait for
it. Empty results or an error MUST hide the row without an error message.

#### Scenario: Deferred load

- GIVEN a visitor opens `/movie/157336` and does not scroll
- THEN no request to `/similar/` is made

#### Scenario: Scrolling down

- GIVEN the visitor scrolls toward the reviews
- WHEN the row nears the viewport
- THEN up to 20 cards appear, movies and shows, each marked with its type
- AND their links keep the origin of the current page
