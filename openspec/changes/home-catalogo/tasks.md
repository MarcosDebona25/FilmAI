# Tasks: Home de descubrimiento (C-05)

## Review Workload Forecast

| Field                   | Value                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------ |
| Estimated changed lines | ~1,100 (without generated i18n catalogs or `graphify-out/`)                          |
| 400-line budget risk    | High as a single PR                                                                  |
| Chained PRs recommended | Yes — four, each against `develop/ui-design`                                         |
| Delivery strategy       | ask-on-risk                                                                          |
| Chain strategy          | Sequential: each PR starts from `develop/ui-design` after the previous one is merged |

### Suggested Work Units

| Unit | Goal                                                                      | PR   | Est. lines | Focused test command                                                 | Rollback boundary                                  |
| ---- | ------------------------------------------------------------------------- | ---- | ---------: | -------------------------------------------------------------------- | -------------------------------------------------- |
| 0    | SDD, doc 04 and decision                                                  | PR 1 |       ~350 | —                                                                    | Docs only                                          |
| 1    | `recommended` + `min_votes`                                               | PR 2 |       ~350 | `python manage.py test catalogo.tests_recomendado`                   | Remove the route; the Home hides the row           |
| 2    | `routes.title`, `lib/catalog.ts`, `TypeSelector`, `MediaCard`, `MediaRow` | PR 3 |       ~350 | `npm run test:unit -- catalog media`                                 | Unused components, nothing links to them           |
| 3    | `/home`, `HomeHero`, navbar variant, login redirect                       | PR 4 |       ~400 | `npm run test:unit -- home` + `npx playwright test e2e/home.spec.ts` | `/home` back to 404 (Not Found), login back to `/` |

## Phase 0: SDD (PR 1)

- [x] 0.1 `proposal.md`, `design.md`, `tasks.md` (this change)
- [x] 0.2 Validate design §5 with the user (13/10/2026)
- [x] 0.3 `docs/decisiones.md`: route of the title page, order Home → title page →
      Search, 3 genres with OR, minimum votes, Hero rule, and the §5 items
- [x] 0.4 `docs/04_Lineamientos_UI.md`: §2 Home becomes «Mixta»; §3.3 gets the
      top 3, OR, `vote_count.gte` and the size; §5 gets the Hero rule, the
      sign-up callout, the selector position and the `/movie/[id]` and
      `/tv/[id]` links

## Phase 1: Backend (PR 2)

Tests go in a new `catalogo/tests_recomendado.py` (`catalogo/tests.py` is already
long; Django finds any `test*.py`). TMDB is mocked at the `TMDBClientCache`
level, with items copied from a real response captured on 13/10/2026, never
invented (lesson of C-04a).

- [x] 1.1 RED: without a session → 401 (Unauthorized) with the envelope
- [x] 1.2 RED: no ratings, or only ratings below 7 → 200 `{generos: [], results: []}`
      and TMDB is never called
- [x] 1.3 RED: the top 3 genres by count reach `discover` joined with `|`, with
      `popularity.desc` and `vote_count.gte=100`
- [x] 1.4 RED: a tie between genres goes to the most recent rating
- [x] 1.5 RED: a title in «Watched» does not come back; one in «Watchlist» does
- [x] 1.6 RED: a movie and a show with the same TMDB id: excluding the movie
      does not drop the show (the pair, not the id)
- [x] 1.7 RED: `tipo=movie` only uses movie ratings; `tipo=tv` only TV ratings
- [x] 1.8 RED: `tipo=all` alternates movie and TV, fills with the other type when
      one runs out, and caps at 15
- [x] 1.9 RED: `generos` comes in the request's language (`Accept-Language: es`)
- [x] 1.10 RED: an inactive rating (`activa=False`) does not count
- [x] 1.11 RED: `tipo=foo` → 400 (Bad Request) with `invalid_choice`
- [x] 1.12 GREEN: `RecommendedView` + the service in `catalogo/services/recomendado.py`
- [x] 1.13 RED → GREEN: `discover?min_votes=50` reaches TMDB as `vote_count.gte`
      and changes the cache key; `min_votes=0` → 400 (Bad Request)
- [x] 1.14 Regenerate `contracts/openapi.yaml` (`FILMAI_ACTUALIZAR_REFERENCIAS=1`)
- [x] 1.15 Canonical spec `openspec/specs/recommendations-api/spec.md`
- [x] 1.16 `ruff format . && ruff check .` and the full `python manage.py test`

## Phase 2: Shared frontend pieces (PR 3)

- [x] 2.1 `routes.title(tipo, id)` → `/movie/{id}` and `/tv/{id}`
- [x] 2.2 `lib/catalog.ts` + Vitest: a TMDB movie and show normalize to the same
      shape; no date → no year; `campos_en_ingles` comes through
- [x] 2.3 `TypeSelector` + Vitest: `aria-pressed`, keyboard, labels from `home.*`
- [x] 2.4 `MediaCard` + Vitest: meta with and without type, `★ 8,5` in Spanish,
      placeholder without poster, `lang="en"` on an English fallback
- [x] 2.5 `MediaRow` + Vitest: previous/next buttons, skeletons, hidden when empty
- [x] 2.6 No new file enters the exceptions of `scripts/i18n/rules.mjs`;
      `npm run i18n:check`, `npm run format:check`, `npm run lint`

## Phase 3: The page (PR 4)

- [ ] 3.1 `HomeHero` + Vitest: the Hero rule (three different Heroes, skipped
      backdrops, real rank in the label)
- [ ] 3.2 `app/home/page.tsx`: rows by type, `?type=` in the URL, recommended only
      with a session, sign-up callout without one
- [ ] 3.3 Errors: a failed row hides and one toast shows; all failed → «Try again»
- [ ] 3.4 Navbar over the Hero on desktop for `/home` (tell Marcos: his component)
- [ ] 3.5 Login and `/complete-signup` land on `routes.explore`
- [ ] 3.6 «Ask FilmAI» floating button, signed in only, to `routes.askFilmAI`
- [ ] 3.7 Playwright `e2e/home.spec.ts` with the API mocked, desktop and mobile:
      signed out, signed in with and without recommendations, selector, a failed row
- [ ] 3.8 Canonical spec `openspec/specs/home-ui/spec.md`; doc 05 rows C-05 and
      A-04; the «Interfaces» table at the top of doc 05 and, with Marcos, the canvas note
- [ ] 3.9 `graphify update .`, lint, Vitest, Playwright and build
