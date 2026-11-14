# Tasks: Search in the navbar, a person filter and hiding irrelevant titles

## Review Workload Forecast

| Field                   | Value                                                                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Estimated changed lines | ~1 450 (backend ~700, frontend ~650, docs ~100)                                                                                      |
| 400-line budget risk    | Medium (PR 5, the navbar combobox, is the largest)                                                                                   |
| Chained PRs recommended | Yes — six small PRs plus the canvas, two lanes (below)                                                                               |
| Delivery strategy       | ask-on-risk                                                                                                                          |
| Chain strategy          | Each PR from `develop` in its own worktree `~/FilmAI-worktrees/<branch>`, PR against `develop`; a PR that needs another stacks on it |
| Owners                  | To agree between Gonza and Marcos. Task 2.0 (canvas) is Gonza's                                                                      |
| PR-Agent                | At most 2 passes per PR, only clear errors                                                                                           |

### Work Units

| PR  | Goal                                               | Est. lines | Focused test command                                                     | Rollback boundary                                             |
| --- | -------------------------------------------------- | ---------: | ------------------------------------------------------------------------ | ------------------------------------------------------------- |
| 1   | Relevance cut in `browse/` (exact title exception) |       ~150 | `python manage.py test catalogo.tests_browse`                            | Set both thresholds to 0                                      |
| 2   | Canvas in Claude Design (Gonza, no code; task 2.0) |          — | —                                                                        | —                                                             |
| 3   | `suggest/` endpoint on `search/multi`              |       ~250 | `python manage.py test catalogo.tests_sugerencias`                       | Remove the route and the throttle scope                       |
| 4   | Person filter in `browse/` (`persona`, `rol`)      |       ~300 | `python manage.py test catalogo.tests_browse_persona`                    | Remove the parameters; `browse/` answers as before            |
| 5   | Navbar magnifier + field with suggestions, `/`     |       ~400 | `npm run test:unit -- navbar` + `npx playwright test navbar --workers=1` | Restore the «Search» link and drop `<NavbarSearch/>`          |
| 6   | Person field and chip in Search                    |       ~250 | `npm run test:unit -- search` + `npx playwright test search --workers=1` | Remove the field and the chip; `person` in the URL is ignored |
| 7   | (Optional, Q-7) Cast and directors link to Search  |       ~120 | `test catalogo.tests_ficha` + `npm run test:unit -- title`               | Names go back to plain text; `id` in `credits/` is harmless   |

Update 14/11/2026: PRs 1, 3 and 4 (the whole backend) go together in one PR
(`feat/buscar-backend`), as small commits in that order; the frontend PRs
follow the lanes below.

Lanes: **backend** 1 → 3 → 4 (independent of each other; this order is by
value) and **frontend** 5 (after 3 and the canvas) → 6 (after 4 and 5), with
7 at the end. 1, 3 and the canvas (2.0) can start at once. The cut has no
frontend part: the answer keeps its shape.

Each PR updates the canonical spec it touches (`openspec/specs/…`) and adds
its line to the decision entry of 13/11/2026 in `docs/decisiones.md` when it
changes something there (measurements, an answered question).

## Phase 1: Relevance cut, backend (PR 1)

- [x] 1.1 `normalizar()` and `es_relevante(item, q)` with the two constants in
      `catalogo/services/browse.py`; tests at the edges (4 and 5 votes; 4.9
      and 5 popularity) and for the exact title, translated or original,
      without accents, case or extra spaces.
- [x] 1.2 `_con_texto` (and later the person branch) drops what does not pass
      after the filters and before paginating; if nothing passes, keeps
      everything. `total_results` and `total_pages` count what is shown.
- [x] 1.3 Fixture from a real «chihiro» answer (`test_datos/`): 3 shown,
      «La arquitectura de El Viaje de Chihiro» left out; a title with 0 votes
      named exactly as the text is shown; no extra TMDB call.
- [x] 1.4 Spec `tmdb-endpoints` («Buscar combina discover y search»).

## Phase 2: Canvas (Gonza)

- [ ] 2.0 **Canvas first (Gonza, Claude Design)**, the first task of the
      frontend work, in rounds with a review after each: (a) «Navbar ·
      desktop» with the variant Gonza chose on 14/11/2026 (the magnifier that
      unfolds into a field, on the right) at 1440, 1024 and 768 px, both
      themes, signed in and out: the magnifier closed, the field unfolded and
      the open dropdown with titles, a person and «See all results»; the `/`
      hint and the unfold animation; (b) «Search · desktop» and «Search ·
      mobile» with the «Person» field and the active person chip with ✕
      above the results. Approve the copy of `design.md` §7 in the same pass.

## Phase 3: Suggestions endpoint (PR 3)

- [x] 3.1 `search_multi` in `TMDBClient` and `TMDBClientCache` (TTL 1 h,
      backup copy like the rest; listed in the endpoints the cache knows).
- [x] 3.2 `catalogo/services/sugerencias.py`: TMDB order, the cut on titles,
      people with `Acting`/`Directing` and `popularity ≥ 1`, at most 2 people
      and 5 in total; `rol` and `gender` for people; `tipo=person`.
- [x] 3.3 `SuggestView` in `CatalogoBaseView` with `q` 2–50 characters and
      `tipo`; no materialization; throttle scope `sugerencias` (120/min) in
      `settings.py`.
- [x] 3.4 Spanish fill limited to `title`/`name` of the kept items.
- [x] 3.5 Tests with fixtures from real «nolan», «dune» and «tom» answers:
      one call, caps, filters, validation, scope, no enqueued task.
- [x] 3.6 Measure again end to end (cold and warm) with `docker compose run
  --rm`; record the numbers in the decision entry.
- [x] 3.7 Spec `tmdb-endpoints` («Suggestions»); `docs/06_TMDB_API_Referencia.md`
      (`search/multi`, `person/{id}`).

## Phase 4: Person filter, backend (PR 4)

- [ ] 4.1 `person_detail` (`person/{id}`) in the client and the cache (24 h).
- [ ] 4.2 `browse/`: `persona` and `rol` validated; 404 `person_not_found`
      (error code in `filmai/exceptions.py` and the error contract).
- [ ] 4.3 `services/browse.py`: credits by role (movies `Director`, shows
      `Creator`, cast without News/Talk), deduplication, `_pasa()` filters,
      text by substring without accents, cut, score order, pagination;
      `persona` in the answer.
- [ ] 4.4 Tests with fixtures from real Nolan, Gilligan and Hanks credits:
      `Creator` counts and an episode `Director` does not; Tom Hanks without
      talk shows; Nolan + «TV shows» is empty; 2 calls cold, 0 cached.
- [ ] 4.5 Spec `tmdb-endpoints` and the error contract.

## Phase 5: Navbar field (PR 5)

- [ ] 5.1 `components/NavbarSearch.tsx`: the combobox of `design.md` §3 on
      the pattern of `CountrySelect.tsx`; debounce 250 ms, 2 characters,
      abort, session cache per language, stale answers dropped.
- [ ] 5.2 `Navbar.tsx`: «Search» leaves `NAV_LINKS`; the magnifier button
      (`aria-expanded`, `aria-controls`, `aria-keyshortcuts="/"`) before the
      account from `md`; pressing it unfolds the field and focuses it; Esc
      or ✕ fold it and return the focus to the magnifier; blur folds it only
      with no text; not rendered on `/search` nor below `md`.
- [ ] 5.3 Navigation: title → title page, person → `/search?person=…&role=…`,
      Enter / «See all results» → `/search?q=…`; clear and close after.
- [ ] 5.4 `/` shortcut (Q-6) with its guards: it unfolds the magnifier and
      focuses the field; on `/search` it focuses the page field.
- [ ] 5.5 Keys (en/es) and `npm run i18n:check`.
- [ ] 5.6 Vitest (magnifier `aria-expanded` and focus on open and on Esc,
      keyboard, `aria-activedescendant`, live region, stale answers,
      shortcut) and e2e (navbar → person → Search; absent on
      `/search` and mobile; axe with the list open).
- [ ] 5.7 `vercel-quality` checklist; new canonical spec `navbar-search`;
      `docs/04_Lineamientos_UI.md` (navbar).

## Phase 6: Person field and chip (PR 6)

- [ ] 6.1 `lib/search.ts`: `person` and `role` in the URL and in
      `consultaApi`; a person counts as one active filter; «Clear filters»
      removes it.
- [ ] 6.2 Chip above the results with photo, «Name · Role» and ✕ (Q-2), on
      desktop and mobile.
- [ ] 6.3 «Person» field reusing the combobox with `suggest/?tipo=person`.
- [ ] 6.4 Count «N results for “Name”» without text; empty state; 404
      `person_not_found` with «Clear filters».
- [ ] 6.5 Vitest + e2e; spec `search-ui` («Filters», «Page and state»).

## Phase 7: Links from the title page (PR 7, optional)

- [ ] 7.1 `credits/` adds `id` to directors, creators and cast.
- [ ] 7.2 Names in «Director and cast» link to Search with the person and
      the role.
- [ ] 7.3 Tests; spec `title-page-ui`.

## Closing

- [ ] 8.1 `docs/05_Plan_de_Desarrollo.md`: mark the pending item done.
- [ ] 8.2 Close this change as the repo does with finished ones once every PR is in and
      the canonical specs reflect it.
