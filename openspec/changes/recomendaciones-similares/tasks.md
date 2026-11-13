# Tasks: Similar titles for lists and title pages (pendiente 5)

## Review Workload Forecast

| Field                   | Value                                                                                                                      |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Estimated changed lines | ~1 500 (backend ~700, frontend ~550, e2e ~150, docs ~100)                                                                  |
| 400-line budget risk    | High as one PR; low split in five                                                                                          |
| Chained PRs recommended | Yes — five PRs: engine + title endpoint, list endpoint, list row, title row, e2e + docs                                    |
| Delivery strategy       | ask-on-risk                                                                                                                |
| Chain strategy          | Each PR from `develop` in its own worktree `~/FilmAI-worktrees/<branch>`; PR 2 stacks on PR 1, PR 3 on PR 2 (merge commit) |
| Blocking                | D-1 to D-9 decided 13/11/2026 (`design.md` §11); the canvas (task 3.1) before any frontend code                            |

### Work Units

| PR  | Goal                                                                        | Est. lines | Focused test command                                                          | Rollback boundary                                 |
| --- | --------------------------------------------------------------------------- | ---------: | ----------------------------------------------------------------------------- | ------------------------------------------------- |
| 1   | `similares.py` (seeds, candidates, TMDB fill, pool, pages) + title endpoint |       ~400 | `python manage.py test catalogo.tests_similares catalogo.tests_similares_api` | Remove the route; the service is unused           |
| 2   | List endpoint, name vector, signature cache, Ollama fallback, calibration   |       ~300 | `python manage.py test listas.tests_sugerencias`                              | Remove the route                                  |
| 3   | Canvas, `MediaRow` slots, `ListSuggestions`, copy                           |       ~350 | `npm run test:unit -- ListSuggestions MediaRow`                               | Remove `<ListSuggestions/>` from `ListDetailView` |
| 4   | `SimilarTitles` on the title page, loaded near the viewport                 |       ~200 | `npm run test:unit -- SimilarTitles`                                          | Remove `<SimilarTitles/>` from `TitleView`        |
| 5   | e2e for both rows, canonical specs, decisions, doc 05, archive the change   |       ~250 | `npm run test:e2e -- similares --workers=1`                                   | Docs only                                         |

## Phase 0: Decisions

- [x] 0.1 Gonza answered D-1 to D-9 on 13/11/2026 (`design.md` §11); D-6
      changed and the design, the spec deltas and these tasks follow it
- [ ] 0.2 Explain (skill `explicar-al-implementar`): what a centroid of
      embeddings is, cosine distance, why HNSW with a `WHERE` can return fewer
      rows, what a cache key with a signature is

## Phase 1: Engine and title endpoint (PR 1)

- [x] 1.1 Branch `feat/similares-motor` from `develop` and its worktree
- [x] 1.2 RED/GREEN optional JWT cookie authentication for the title
      endpoint (§7): an expired or invalid cookie → 200 (OK) as anonymous,
      a valid one → «Vistas» removed
- [x] 1.3 RED `catalogo/tests_similares.py` — `vector_semilla`: average
      normalized, seeds without `ready` vector skipped, none → `None`, the
      name mix with the D-1 table
- [x] 1.4 RED `candidatos`: order by distance; seeds excluded; a list made of
      the 1 000 neighbours of a title still yields 100 (iterative scan); type
      filter; no poster and no rating left out (D-5)
- [x] 1.5 GREEN `vector_semilla` (`avg()` in SQL) and `candidatos`: both
      `SET LOCAL` (`hnsw.ef_search`, `hnsw.iterative_scan = relaxed_order`)
      and the `SELECT` inside one `transaction.atomic()`; a test checks
      `SHOW hnsw.iterative_scan` in that transaction
- [x] 1.6 RED `relleno_tmdb` with `TMDBClientCache` mocked: only when fewer
      than 20 close; up to 3 seeds; round robin; drops `adult`, < 10 votes, no
      poster, seeds and local duplicates; `TMDBError` → empty, not an error;
      the TMDB call counter never passes 6
- [x] 1.7 GREEN `relleno_tmdb`, with `materializar_listado_en_segundo_plano`
      for the cards that are shown
- [x] 1.8 RED pool and pages: weighted shuffle reproducible with the same
      seed, different with another, page 1 mostly close ones (assert on mean
      rank); 60 at most; `pagina` slices and removes `excluir_pares`
- [x] 1.9 GREEN `armar_pool`, `pagina`
- [x] 1.10 RED `catalogo/tests_similares_api.py`: anonymous → 20 results,
      `public` cache and `Vary: Accept-Language`; with session «Vistas»
      removed and `private`; two users share the cached pool; title not in the
      catalog or without vector → TMDB only, 10 min TTL; invalid `id_tmdb` →
      400 (Bad Request) like the detail; throttle scope `catalogo`
- [x] 1.11 GREEN `SimilaresView` + routes `movie/<id>/similar/`,
      `tv/<id>/similar/`; log line per request
- [x] 1.12 `contracts/openapi.yaml` regenerated if the contract test asks
- [x] 1.13 `ruff format . && ruff check .`; tests of `catalogo`, `listas`,
      `usuarios.tests` and `filmai.tests_esquema` with `docker compose run --rm`
      (817 tests; the full suite runs in CI, the local WSL has little memory)

## Phase 2: List endpoint (PR 2)

- [ ] 2.1 Branch `feat/similares-listas` from PR 1's branch and its worktree
- [ ] 2.2 RED name rule (D-2): «Lista 3», «My list», «Nueva lista» → no; «Sci
      Fi», «Pelis para llorar», «Domingo de lluvia» → yes; Favorites never
- [ ] 2.3 RED name vector: cached by normalized name; Ollama via
      `MockTransport`; not loaded → skipped, `pedir_carga_del_modelo` called,
      5 min TTL; `/api/ps` failing → flag for 60 s and a second request does
      not call Ollama
- [ ] 2.4 RED `listas/tests_sugerencias.py`: 401 (Unauthorized) without
      session; 404 (Not Found) for someone else's list, an inactive one,
      Pendientes and Vistas; `pagina` 0, -1, `abc` → 400 (Bad Request); empty
      list → 200 (OK) empty without TMDB; list of only shows → only shows
      (D-3); «Vistas» removed after the cache
- [ ] 2.5 RED signature: adding or removing an item and renaming change the
      key; rating a title (adds to «Vistas») does not
- [ ] 2.6 GREEN `ListaSugerenciasView` + route `<id>/suggestions/`
- [ ] 2.7 Contract tests and `contracts/` if they ask
- [ ] 2.8 Calibrate `DISTANCIA_MAXIMA` with three real lists of the dev
      database (one theme, mixed types, two unrelated themes): print the
      distances and the first 10 with and without the name. Record in
      `design.md` §4 and decide whether the multi-centroid follow-up is needed
- [ ] 2.9 Measure with Ollama loaded: cold with name, cold without, cached;
      write the numbers in `design.md` §8
- [ ] 2.10 `ruff format . && ruff check .`; full backend suite

## Phase 3: List row (PR 3)

- [ ] 3.1 **Design the list row in the Claude Design canvas** (artboards «List
      detail» desktop and mobile): «Suggested for this list», the «+ Add» and
      «Added» states, «Refresh», loading, error, and the title page row «More
      like {title}». Done by Gonza in the canvas before any code; read the
      canvas again before implementing (it is edited live)
- [ ] 3.2 Copy of `design.md` §9 approved and added to the CSV;
      `npm run i18n:generate`, `npm run i18n:check`
- [ ] 3.3 RED Vitest `MediaRow`: `encabezado` and `accion` render; the Home
      rows are unchanged without them
- [ ] 3.4 RED Vitest `ListSuggestions`: hidden for Pendientes and Vistas,
      while there is a next page and with empty results; shown with an active
      filter, also under the empty filtered state, without refetching when
      the filter changes; add →
      «Added», disabled, appended to the grid, toast by error code; refresh →
      next page, wraps to 1, old cards kept until the new ones arrive, status
      announced; error → retry inside the row
- [ ] 3.5 GREEN `MediaRow` slots, `ListSuggestions`, wiring in
      `ListDetailView`
- [ ] 3.6 `npx prettier --check .`, ESLint, `tsc`, `npm run test:unit`

## Phase 4: Title page row (PR 4)

- [ ] 4.1 RED Vitest `SimilarTitles`: no request until the sentinel
      intersects; then 20 cards with type; empty or error → nothing drawn;
      `from` kept
- [ ] 4.2 GREEN `SimilarTitles` in `TitleView`, after credits
- [ ] 4.3 `npx prettier --check .`, ESLint, `tsc`, `npm run test:unit`

## Phase 5: e2e and documentation (PR 5)

- [ ] 5.1 Playwright with the controlled API: add from the row, refresh, the
      keyboard path (Tab to «+ Add», Enter), axe on both rows at 375 and
      1440 px. Locally with `--workers=1`
- [ ] 5.2 `docs/decisiones.md`: close the entry with D-1 to D-9 as answered,
      `DISTANCIA_MAXIMA` and the latencies
- [ ] 5.3 Canonical specs: new `openspec/specs/similar-titles/spec.md`;
      merge the deltas of `list-detail-ui` (new) and `title-page-ui`
- [ ] 5.4 Doc 05: pendiente 5 closed, Mejoras futuras updated
- [ ] 5.5 `graphify update .` and commit `graphify-out/` with the docs
- [ ] 5.6 Remove `openspec/changes/recomendaciones-similares/`
