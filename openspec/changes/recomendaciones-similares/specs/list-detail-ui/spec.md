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
`GET /api/lists/{id}/suggestions/`. It MUST NOT appear in Pendientes or Vistas,
while the grid has a next page, or while a filter or search is active. Empty
results MUST hide the row. Loading MUST show skeletons with `aria-busy`; an
error MUST show a retry inside the row and leave the list usable.

#### Scenario: Pendientes

- GIVEN the user opens Pendientes
- THEN there is no suggestions row and no request for it

#### Scenario: Filtering

- GIVEN a custom list with the «Movies» filter active
- THEN the row is hidden until the filter is cleared

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
MUST announce the new suggestions.

#### Scenario: Last page

- GIVEN `paginas` is 3 and page 3 is shown
- WHEN the user activates «Refresh»
- THEN page 1 is requested
