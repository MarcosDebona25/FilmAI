# Tasks: Ficha de detalle (C-07)

## Review Workload Forecast

| Field                   | Value                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------ |
| Estimated changed lines | ~1,600 (without generated catalogs or `graphify-out/`)                               |
| 400-line budget risk    | High as a single PR                                                                  |
| Chained PRs recommended | Yes — five, each against `develop/ui-design`                                         |
| Delivery strategy       | ask-on-risk                                                                          |
| Chain strategy          | Sequential: each PR starts from `develop/ui-design` after the previous one is merged |

## Phase 0: SDD (PR 1)

- [x] 0.1 `proposal.md`, `design.md`, `tasks.md`
- [x] 0.2 Decisions validated with the user (14/10/2026)
- [x] 0.3 `docs/decisiones.md` entry
- [x] 0.4 `docs/04_Lineamientos_UI.md` §5c/§5d: breadcrumb by `?from=`, public reviews with sort and filter, creators for shows, «★ N» instead of «X/10», L-04 inside C-07
- [x] 0.5 `docs/05_Plan_de_Desarrollo.md`: L-04 now built by Gonza with C-07

## Phase 1: Backend (PR 2)

Tests with real TMDB responses captured on 13-14/10/2026, never invented.

- [x] 1.1 RED → GREEN: credits of a movie → directors from the crew, cast with characters, in TMDB order
- [x] 1.2 RED → GREEN: credits of a show → `directores` from `created_by`, not from the crew
- [x] 1.3 RED → GREEN: credits cap at 50; invalid id → 400 (Bad Request)
- [x] 1.4 RED → GREEN: community reviews without a session → 200, nothing excluded
- [x] 1.5 RED → GREEN: with a session the user's own review is still excluded
- [x] 1.6 RED → GREEN: `POST` without a session is still 401 (Unauthorized)
- [x] 1.7 RED → GREEN: each `orden` sorts as stated; unknown value → 400
- [x] 1.8 RED → GREEN: `nota_min`/`nota_max` filter inclusively; out of range → 400
- [x] 1.9 RED → GREEN: following `next` with `orden=nota-desc` over many equal ratings never repeats or skips a review
- [x] 1.10 RED → GREEN: `total` counts the filtered set and `total_comunidad` the whole community
- [x] 1.11 Regenerate `contracts/openapi.yaml`; update `openspec/specs/reviews-api` and `tmdb-endpoints`
- [x] 1.12 `ruff` and the full `python manage.py test`

## Phase 2: Rating modal and confirmations (PR 3)

- [x] 2.1 `StarRating` + Vitest: arrows, Home/End, hover preview, `aria-checked`, two rows on mobile
- [x] 2.2 `RatingDialog` + Vitest: publish disabled without a rating, counter, 1000 limit, Watched notice only if not in Watched, edit preloads, «Remove rating» only when editing
- [x] 2.3 `ConfirmDialog` + Vitest: focus starts on Cancel, Escape cancels, the review preview is clamped
- [x] 2.4 No new copy needed for the dialogs (all seeded); the new keys go with PR 5. `i18n:check` clean

## Phase 3: List actions (PR 4)

- [x] 3.1 `TitleActions` + Vitest: toggles reflect membership, `aria-pressed`, toasts
- [x] 3.2 Watched off with a rating: 409 → confirm → retry with `borrar_calificacion=true`
- [x] 3.3 `ListsMenu` + Vitest: checklist, counts, inline creation with name errors from the API codes

## Phase 4: The page (PR 5)

- [ ] 4.1 `lib/title.ts` + Vitest: runtime and seasons, breadcrumb for each `from`
- [ ] 4.2 `TitleView`, `TitleHero`, `CreditsSection`, `ReviewsSection`
- [ ] 4.3 `/movie/[id]` and `/tv/[id]`; `MediaCard` with `from=home`
- [ ] 4.4 Playwright `e2e/ficha.spec.ts`, desktop and mobile: signed out, rate and edit, delete text, remove rating, Watched with a rating, add to a new list, community sort and filter, no horizontal overflow
- [ ] 4.5 Canonical spec `title-page-ui`; doc 05 rows C-07, C-08, L-04 and the «Interfaces» table
- [ ] 4.6 Remove `openspec/changes/title-page/` (AGENTS.md §9); `graphify update .`; all checks
