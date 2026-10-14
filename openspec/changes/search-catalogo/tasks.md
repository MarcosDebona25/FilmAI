# Tasks: Buscar (C-06)

## Review Workload Forecast

| Field                   | Value                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------ |
| Estimated changed lines | ~1,300 (without generated catalogs or `graphify-out/`)                               |
| 400-line budget risk    | High as a single PR                                                                  |
| Chained PRs recommended | Yes — four, each against `develop/ui-design`                                         |
| Delivery strategy       | ask-on-risk                                                                          |
| Chain strategy          | Sequential: each PR starts from `develop/ui-design` after the previous one is merged |

## Phase 0: SDD (PR 1)

- [x] 0.1 `proposal.md`, `design.md`, `tasks.md`
- [x] 0.2 Decisions validated with the user (14/10/2026): text + genre/rating over the first 100; any text up to 50
- [x] 0.3 `docs/decisiones.md` entry
- [x] 0.4 Doc 02 (CU-008, CU-010): any text up to 50, search as a page
- [x] 0.5 Doc 04 §5b: page instead of overlay, states and mobile sheet per the canvas

## Phase 1: Backend (PR 2)

TMDB fixtures from responses captured on 14/10/2026, never invented.

- [ ] 1.1 RED → GREEN: client `search` sends `primary_release_year` / `first_air_date_year`; `discover` sends `vote_average.lte`; cache keys unchanged when unused
- [ ] 1.2 RED → GREEN: no text → `discover` with filters and popularity order, `media_type` on every item
- [ ] 1.3 RED → GREEN: text without genre/rating → one `search` per type, year forwarded
- [ ] 1.4 RED → GREEN: text with genre or rating → window of up to 5 pages, filtered, paginated 20; fewer pages when TMDB has fewer
- [ ] 1.5 RED → GREEN: «All» alternates movies and shows, sums totals, caps pages at 500
- [ ] 1.6 RED → GREEN: genre mapping for shows in «All»; a genre with no counterpart empties that side
- [ ] 1.7 RED → GREEN: rating `N+` / `m5` with at least 50 votes, in discover and in the window
- [ ] 1.8 RED → GREEN: validation — `q` > 50 → 400 `max_length`; bad `tipo`/`nota` → 400 `invalid_choice`; `page` > 500 → 400; empty `q` = no text
- [ ] 1.9 RED → GREEN: `genres/?tipo=all`
- [ ] 1.10 Spec `tmdb-endpoints` updated

## Phase 2: Search page, desktop (PR 3)

- [ ] 2.1 Copy in `docs/i18n/copia-propuesta.csv` → generate → check
- [ ] 2.2 `lib/search.ts`: URL ⇄ state, query to `browse/`, active filter count (unit tests)
- [ ] 2.3 `MediaCard` fluid width and «No ratings»
- [ ] 2.4 `SearchView`: field, Close/Escape, type, selects, count, grid, pager, states (tests)
- [ ] 2.5 `app/search/page.tsx`

## Phase 3: Mobile and return path (PR 4)

- [ ] 3.1 Filters button with badge and `FiltersSheet` on `DialogShell` (tests)
- [ ] 3.2 Last search in `sessionStorage`; title page «Search» crumb returns to it (tests)
- [ ] 3.3 Playwright `e2e/buscar.spec.ts`: desktop and mobile, no horizontal overflow
- [ ] 3.4 Spec `search-ui`, doc 05 (C-06 ✅), delete `openspec/changes/search-catalogo/`
