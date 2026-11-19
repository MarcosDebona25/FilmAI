# lists-ui Specification

## Purpose

The Lists overview (`/lists`, L-02) and the list page (`/lists/{id}`, L-03), including the Watching list (PR 4, 17/11/2026). Consumes `list-endpoints`. Visual source of truth: the canvas artboards «Lists», «List detail», «Watching · list page» and «Watching · Lists», each with its phone version.

## Requirements

### Requirement: Lists grid

`/lists` MUST show the four default lists first, in the order Favorites, Watchlist, Watching, Watched, and then the user's own lists, followed by the «Create new list» card. The grid MUST have 4 columns from 73,75 rem (1180 px), 2 from 40 rem and 1 below, so the four defaults fill the first row on wide screens. A list card MUST stack up to 4 posters on desktop and 3 on phones, with «N more» for what is not shown at that size.

#### Scenario: Wide screen

- GIVEN a viewport of 1440 px
- THEN the four default lists share the first row and the own lists start on the second

### Requirement: List page layout

The list page MUST show the breadcrumb, then the title with the live count on the same line («4 items · 1 movie · 3 TV shows»; phones show only «4 items»), then the search, the filters (Type, TMDB rating, Sort) and the card grid. Removing a title from Watched MUST keep its rating: it is a plain removal with a confirmation.

### Requirement: Watching cards

On the Watching list each card MUST carry a «⋯» button instead of «✕»: top-right of the poster, always visible, 36 px (a 44 px target on phones), with `aria-haspopup="menu"`, `aria-expanded` and the name «More for {title}». It opens a menu (a panel on desktop, a bottom sheet with «Cancel» on phones) with «Mark as finished», «Rate it…» and «Remove from Watching». Only one menu MUST be open at a time; Escape or a click outside closes it and the focus MUST return to the «⋯».

- «Mark as finished» MUST call `PUT /api/lists/status/` with `vistas`; the card leaves the grid at once and the count updates. On failure the card MUST return to its place and an error toast without Undo MUST show.
- «Remove from Watching» MUST call it with `null` (the title keeps no status).
- «Rate it…» MUST open the same rating dialog as the title page. Rating a title without a rating moves it to Watched; one that already had a rating is edited and not moved.
- The toast MUST be the title page's: «{title} moved to Watched» with «Rate it» (desktop only) and Undo, or «{title} removed from Watching» with Undo, for 6 s; a new action replaces it, and Undo only reverts the last one. Undo MUST call the same endpoint with `estado_anterior` and put the card back in its previous position in the grid. Leaving the page closes the toast.

#### Scenario: Mark as finished, then Undo

- GIVEN Watching has «Lanterns», «Harbor Lights» and «Night Shift»
- WHEN the user marks «Harbor Lights» as finished and presses Undo
- THEN the grid is again «Lanterns», «Harbor Lights», «Night Shift»

### Requirement: Watching empty state

When Watching has no titles the page MUST show «Nothing in progress», its text and «Open Watchlist», which goes to the Watchlist list, in the same block as any empty list. Taking the last title out MUST show it; Undo MUST bring the card back and hide it.
