# list-detail-ui Specification

## Purpose

The detail of a list (`/lists/[id]`, L-03). This spec covers the suggestions
band at the end of the list; the rest of the screen is described in
`docs/decisiones.md` (15/10–18/10/2026). Visual source of truth: the canvas
artboards «Suggested for this list» desktop and mobile (section 14,
15/11/2026). Backend in `similar-titles`.

## Requirements

### Requirement: Suggestions band

The detail of Favorites, Vistas («Watched») or a custom list with at least one
item MUST show, after the grid, an open band (no box around it) «Suggested for
this list» with the results of `GET /api/lists/{id}/suggestions/`, in compact
rows: 3 columns on desktop and one on mobile, with posters of 74 × 111 and
64 × 96. It MUST NOT appear in Pendientes («Watchlist») or Viendo («Watching»)
(19/11/2026), in an empty list or
when there is nothing to suggest. It MUST be requested only once the grid has
no next page. Its line MUST say «Based on its N titles and its name, without
what you already watched.» when `nombre_usado` is true, and the same without
«and its name» otherwise; in Vistas it MUST say «Based on what you watched
most recently.» (19/11/2026). If the first load fails, the band MUST NOT be drawn
and the list stays usable.

#### Scenario: Pendientes and Viendo

- GIVEN the user opens Pendientes or Viendo
- THEN there is no suggestions band and no request for it

#### Scenario: Watched

- GIVEN the user opens Vistas with at least one title
- THEN the band is shown at the end, without the titles already watched

#### Scenario: More pages to load

- GIVEN the grid still has a next page
- THEN the band is not requested until the last page is loaded

### Requirement: Add with one click

Each row MUST have an «+ Add» button outside the title link, labelled «Add
{title} to {listName}», 30 px tall on mobile and 34 px on desktop with a 44 px
tap area, in a soft fill (`--raised-2`, `--line` on hover). It MUST add the
title with the existing items endpoint, remove it from the band, add it to the
grid and the counters, and move the focus to the next suggestion's button.
API errors MUST be shown by code in a toast.

#### Scenario: Adding

- GIVEN the band shows «Arrival»
- WHEN the user activates «+ Add» on it
- THEN «Arrival» is in the list grid and no longer in the band

### Requirement: Show more suggestions

«Show more suggestions» MUST ask for the next page (`?pagina=N+1`) of the same
pool and append the new suggestions below the current ones, with `aria-busy`
while it loads. It MUST be hidden on the last page (`pagina >= paginas`), and
the focus then moves to the first new suggestion. A failure MUST show a toast
and keep the button to retry. If the list changed since the first page, the
next request starts again at page 1 of the new pool, skipping what the band
already shows.

#### Scenario: Last page

- GIVEN `paginas` is 2 and page 1 is shown
- WHEN the user activates «Show more suggestions»
- THEN page 2 is appended below and the button is no longer shown
