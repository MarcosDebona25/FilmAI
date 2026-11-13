# list-detail-ui Specification

## Purpose

The detail of a list (`/lists/[id]`, L-03). This change adds the suggestions
row; the rest of the screen is described in `docs/decisiones.md` (15/10–18/10/2026)
and becomes part of this spec when it is merged. Visual source of truth: the
canvas artboards «List detail» desktop and mobile.

## ADDED Requirements

### Requirement: Suggestions row

The detail of a custom list or of Favorites with at least one item MUST show,
after the grid, a horizontal row «Suggested for this list» with the results of
`GET /api/lists/{id}/suggestions/`. It MUST NOT appear in Pendientes or Vistas.
It MUST appear with or without an active filter or search, after the loaded
items and only once the grid (filtered or not) has no next page. A filter that
leaves the grid empty MUST still show the row under the empty filtered state.
Filters and search MUST NOT change the request, the suggestions or the cache:
they always come from the whole list. Empty results MUST hide the row. Loading MUST show skeletons with `aria-busy`; an
error MUST show a retry inside the row and leave the list usable.

#### Scenario: Pendientes

- GIVEN the user opens Pendientes
- THEN there is no suggestions row and no request for it

#### Scenario: Filtering

- GIVEN a custom list with the «Movies» filter active and no next page
- THEN the row is shown at the end of the filtered grid
- AND its suggestions are the same as without the filter

#### Scenario: Filter with no matches

- GIVEN a filter that leaves the grid empty
- THEN the row is shown under «No titles in this list match these filters»

#### Scenario: More pages to load

- GIVEN the grid still has a next page
- THEN the row is not drawn until the last page is loaded

### Requirement: Add with one click

Each card MUST have an «+ Add» button outside the card link, labelled «Add
{title} to {listName}». It MUST add the title with the existing items endpoint,
then turn into a disabled «Added» and append the title to the grid without
refetching the row. API errors MUST be shown by code.

#### Scenario: Adding

- GIVEN the row shows «Arrival»
- WHEN the user activates «+ Add» on it
- THEN «Arrival» is in the list and its button reads «Added»

### Requirement: Refresh

A «Refresh» button MUST ask for the next page and go back to page 1 after the
last one. The current cards MUST stay until the new ones arrive, the row MUST
scroll back to its start, focus MUST stay on the button, and a polite status
MUST announce the new suggestions. After an «+ Add», «Refresh» MUST ask for
page 1 and MUST drop the titles the row already showed.

#### Scenario: Last page

- GIVEN `paginas` is 3 and page 3 is shown
- WHEN the user activates «Refresh»
- THEN page 1 is requested
