# Tasks: TMDB terms of use compliance (issue #180)

## Review Workload Forecast

| Field                   | Value                                                                                                                                                                                                                      |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Estimated changed lines | ~1 150 (frontend ~350, backend ~600, docs ~200)                                                                                                                                                                            |
| 400-line budget risk    | Medium                                                                                                                                                                                                                     |
| Chained PRs recommended | Yes — four PRs, mostly independent (below)                                                                                                                                                                                 |
| Delivery strategy       | ask-on-risk                                                                                                                                                                                                                |
| Chain strategy          | Integration branch `feat/tmdb-y-calidad-chat` (from `develop`, 13/11/2026); each PR in its own herdr worktree `~/FilmAI-worktrees/<branch>` based on it, PR against it; one final PR to `develop`; merge commit, no rebase |
| Owners                  | To agree between Gonza and Marcos. PR 1 is frontend only; PRs 2–3 are backend; PR 4 is closing                                                                                                                             |
| PR-Agent                | At most 3 passes per PR, while the workflow stays disabled (06/11/2026) the gate is local verification                                                                                                                     |

### Work Units

| PR  | Goal                                                   |  Est. lines | Focused test command                                              | Rollback boundary                                                              |
| --- | ------------------------------------------------------ | ----------: | ----------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 1   | Credits in `/terms`, logo, footer notice, naming audit |        ~350 | `npm run test:unit -- terms footer` + `npx playwright test terms` | Remove `<TmdbCredits />` and restore the old footer key                        |
| 2   | Catalog refresh task, 404 rule, cache cap              |        ~450 | `test catalogo.tests_vencimiento catalogo.test_cache_tope`        | Remove the beat entry and the task; reverse the `disponible_en_tmdb` migration |
| 3   | Chat card trimming and rehydration                     |        ~250 | `test chatbot.tests_recorte`                                      | Remove the beat entry; rehydration of untrimmed cards is a no-op               |
| 4   | API rate measurement, AI-use decision, docs, specs     | ~100 + docs | manual + full suite                                               | Docs only                                                                      |

Branching (13/11/2026): this change and pendiente 4 of the plan (chatbot
quality) share the integration branch `feat/tmdb-y-calidad-chat`. Each work
unit is a branch from it, in a worktree created with
`herdr worktree create --cwd ~/FilmAI --base feat/tmdb-y-calidad-chat --branch <branch> --path ~/FilmAI-worktrees/<branch>`;
its PR targets the integration branch (CI runs on PRs to `feat/**`). When
every unit is in, one PR takes the branch to `develop`. Order and parallel
lanes are in `docs/05_Plan_de_Desarrollo.md`, pendiente 1.

Dependencies: PR 1 and PR 2 start with no wait. PR 3 needs PR 2's
`disponible_en_tmdb` only for the «unavailable» placeholder; it can start
before and stack. PR 4 waits for the other three (it records their numbers).

The rule for titles TMDB no longer has was confirmed by Gonza on 12/11/2026
(design, «Titles TMDB no longer has»): tombstone, and a visible «Title no
longer available» card in lists and My reviews.

## Phase 1: Attribution and brand (PR 1)

- [ ] 1.0 Canvas first (07/11/2026; staged 13/11/2026): design in Claude
      Design the credits block of «Terms» and the footer line with its
      «Credits» link, in staged rounds with a review gate after each:
      (a) one comparison artboard per theme with the credits block on mobile
      and each official logo (`logo1.svg` stacked, `logo2.svg` two lines,
      `logo3`–`logo5` horizontal), 10 combinations; Marcos keeps at most two;
      (b) the kept logos at their size in «Terms · mobile» and «Terms ·
      desktop», both themes, plus the footer line in «Footer · desktop» and
      «Footer · mobile» with and without a small horizontal logo;
      (c) the chosen combination only, rendered to check it, and every
      discarded artboard removed. No logo is fixed before this step. Record
      the choice in `docs/decisiones.md`
- [ ] 1.1 Explain: why the notice is a catalog key and not a literal; why the
      logo is an `<img>` from `public/` and not an SVG component (no
      recoloring); what an anchor link is and how `routes.terms` builds it
- [ ] 1.2 Copy: in `traducciones/claves.csv`, new keys `legal.credits.title`,
      `legal.credits.notice` («This product uses the TMDB API but is not
      endorsed or certified by TMDB.» / «Este producto usa la API de TMDB,
      pero TMDB no lo respalda ni lo certifica.»), `legal.credits.logoAlt`
      («TMDB logo» / «Logo de TMDB»), `footer.main.creditsLink`; replace
      `footer.main.tmdbAttribution` with the notice; align
      `legal.thirdParty.tmdb` and `emails.shared.copyrightAttribution`.
      Marcos approves the Spanish. Regenerate catalogs; `npm run i18n:check`
- [ ] 1.3 Logo: copy the variant chosen in 1.0 unchanged to
      `frontend/public/tmdb/`, with the size and theme treatment the canvas
      fixed
- [ ] 1.4 RED `frontend/tests/tmdb-credits.test.tsx`: the block renders the
      exact English notice, the logo with its alt, the link to
      `https://www.themoviedb.org`, and `id="credits"`; Spanish renders the
      Spanish notice
- [ ] 1.5 RED: a Vitest that the file in `frontend/public/tmdb/` is
      byte-identical to its source in `docs/tmdb-legales/`
- [ ] 1.6 GREEN `components/TmdbCredits.tsx` and its place at the end of
      `app/terms/page.tsx`; footer line with the notice and the «Credits»
      link to `${routes.terms}#credits`
- [ ] 1.7 Naming audit: grep `traducciones/`, `frontend/messages/`,
      `frontend/content/legal/`, `backend/templates/correos/`,
      `backend/chatbot/prompts.py` and `docs/` for «TMDb», «Tmdb»,
      «themoviedb» as a visible word and for links to TMDB's site that are not
      `https://www.themoviedb.org`; fix what turns up
- [ ] 1.8 Add the naming rule to `npm run i18n:check` (or a Vitest over the
      generated catalogs) so a wrong spelling fails
- [ ] 1.9 e2e: `/terms#credits` in both languages and both themes (a11y with
      axe on that section); update the footer snapshots that change
- [ ] 1.10 Verify: prettier, `npm run i18n:check`, unit tests (with
      `--maxWorkers=4`), the touched e2e

## Phase 2: Catalog persistence (PR 2)

- [x] 2.1 Explain: what «cache» means in TMDB's terms (anything stored, not
      only Redis); why refresh and not delete (CASCADE to ratings); how a
      beat entry reaches the worker
- [x] 2.2 RED `catalogo/tests_vencimiento.py`: the pure function
      `cuota_nocturna(total, por_dia, techo)` (design, «Nightly quota»):
      empty catalog gives 0; 10 000 spread rows give 67; 10 000 rows 150 days
      old give 334; NULL and overdue rows count as due tonight; the ceiling
      caps it. The query side groups rows by the day they turn 180 in one
      query, and `a_refrescar(cuota)` returns NULL rows first, then oldest
      `fecha_enriquecimiento`, exactly `cuota` of them
- [x] 2.3 RED: `refrescar_vencidos` calls `materializar(forzar=True)` for each
      due row; one `TMDBError` does not stop the rest; the summary counts
      refreshed / not found / failed and the rows still over 180 days
- [x] 2.4 RED: refreshing a row overwrites its `ProduccionTraduccion` texts
      (not only fills empty ones); if it does not, fix `guardar_traducciones`
- [x] 2.5 RED: the first 404 (Not Found) only sets `fecha_404` and leaves the
      row due; a second 404 (Not Found) applies the rule only if `fecha_404` is before
      today (a second run the same night does not); a timeout, 500 (Internal
      Server Error), 429 (Too Many Requests) or 401 (Unauthorized) never
      counts; a successful refresh clears `fecha_404`
- [x] 2.5b RED: two 404s (Not Found) on a row nobody references delete it
      (and its translations and embedding)
- [x] 2.6 RED: 404 (Not Found) on a row with a rating keeps the rating, blanks
      the TMDB fields, sets `disponible_en_tmdb = False` and
      `fecha_enriquecimiento`, deletes its `ProduccionTraduccion` rows and
      the embedding; semantic search,
      Recommended, the chatbot tools (`mis_listas` included) and the detail
      page never return it
- [x] 2.6b RED: `Calificacion` and `Tiene` protect the production
      (`on_delete=PROTECT`; `Resena` hangs from its `Calificacion`): a
      rating created between the check and the
      delete makes the delete fail (inside its own savepoint) and the row
      becomes a tombstone instead. Before the change, review every place that
      deletes a production (design lists them: `_descartar_cascaron`, the
      seed, the admin, tests) and how each handles `ProtectedError`
- [x] 2.6c RED: a tombstone TMDB answers with 200 (OK) again is filled in,
      `disponible_en_tmdb = True`, `fecha_404` cleared, embedding enqueued
- [x] 2.7 GREEN: migration `disponible_en_tmdb` (default `True`), `fecha_404`
      (nullable) and `PROTECT` on the two foreign keys to the production
      (`Calificacion`, `Tiene`);
      `catalogo/services/vencimiento.py`; task `catalogo.refrescar_vencidos`;
      settings `DIAS_REFRESCO_TMDB = 150`, `CELERY_REFRESCO_TECHO = 1000`;
      index on `fecha_enriquecimiento`;
      beat entry at 03:30 with its comment
- [x] 2.8 RED `catalogo/test_cache_tope.py`: every value in `ENDPOINT_TTLS`,
      `RESPALDO_TTL`, `RESPALDO_TTLS` and every catalog `max-age` is ≤ 180
      days
- [x] 2.9 RED: the refresh honors 429 (Too Many Requests) with `Retry-After`
      (`httpx.MockTransport`, `time.sleep` patched)
- [x] 2.10 Serializers and cards for an unavailable title: «Title no longer
      available» key (en/es) in the frontend, no link, grey card; in lists
      and My reviews it keeps the rating and review, and can still be removed
      from the list or have its review deleted; unit test
- [x] 2.11 Manual (no Docker in this planning worktree; in the PR's
      worktree with `RUN_MIGRATIONS=false` as usual): run the task once
      against the dev database, record the quota and how it was obtained,
      how long it took, and how many TMDB calls it made
- [x] 2.12 Verify: `ruff format . && ruff check .`, `python manage.py test`

Done 13/11/2026 on `feat/tmdb-refresco`. 2.4, 2.8 and 2.9 pinned behavior that
already held (translations were already overwritten, TTLs were already under
30 days, the client already honored `Retry-After`), so their tests were green
from the start. The 2.11 run is recorded in `docs/decisiones.md`.

## Phase 3: Chat cards (PR 3)

- [ ] 3.1 Explain: why trimming is a nightly task and not a read-time filter;
      what `bulk_update` saves; how one prefetch avoids a query per card
- [ ] 3.2 RED `chatbot/tests_recorte.py`: cards of a message older than 180
      days become `{id_tmdb, tipo}`; a 30-day-old message is untouched; a
      second run changes nothing
- [ ] 3.3 RED: `ya_recomendados` entries get `fecha` when written and when a
      card is shown again; the task strips `titulo` and `anio` from entries
      older than 180 days or without `fecha`
- [ ] 3.4 RED: the history `GET` rehydrates trimmed cards in the reader's
      language with a fixed number of queries per page; a missing or
      unavailable production gives `titulo: null`; no TMDB call
- [ ] 3.5 RED: the system prompt resolves stripped `ya_recomendados` titles
      from the catalog in one query; an id not in the catalog stays in the
      no-repeat set but not in the «Ya recomendados» line
- [ ] 3.6 GREEN: task `chatbot.recortar_tarjetas`, beat entry at 04:30;
      serializer rehydration; orchestrator writes `fecha`; prompt builder
- [ ] 3.7 Panel: a card with `titulo: null` renders the «Title no longer
      available» placeholder without a link; Vitest
- [ ] 3.8 Update `contracts/` if the history card shape documents
      `titulo` as required
- [ ] 3.9 Verify: ruff, `python manage.py test`, prettier, unit tests

## Phase 4: API use, AI decision and docs (PR 4)

- [ ] 4.1 Measure the peak request rate with `registrar_llamada`'s counter:
      a seed of 200 titles, a sync, `rellenar_traducciones --limite 200`,
      and the refresh task, each with the worker running. Record the numbers
      in doc 06. Only if any run exceeds ~30 requests per second, open a
      follow-up for a shared limiter
- [ ] 4.2 Check that no TMDB request path bypasses `catalogo/client.py`
- [ ] 4.3 Grep for `image.tmdb.org` outside `lib/catalog.ts` and its tests;
      confirm images are only shown as catalog content
- [ ] 4.4 `docs/decisiones.md`: one entry for #180 with the AI-use basis
      (academic, non-profit; revisit before any ad, subscription or paid
      tier), the credits location, the 150/180-day rule and its reference
      field, the 404 rule as finally agreed, the card trimming (narrowing the
      09/10/2026 decision), and the accepted exceptions (access collage until
      13/02/2027, test fixtures)
- [ ] 4.5 `PRODUCT.md`: one line under constraints — no revenue from TMDB
      content without an agreement with TMDB (#180)
- [ ] 4.6 `docs/04_Lineamientos_UI.md`: the credits block, logo variant,
      size, themes and the footer line (§ Footer)
- [ ] 4.7 `docs/06_TMDB_API_Referencia.md`: the inventory of stored TMDB data,
      the refresh rule, the 404 rule, the TTL cap and the measured rate
- [ ] 4.8 Canonical specs: add `openspec/specs/tmdb-compliance/` from this
      change; note the new task in `catalog-daily-sync`, the 404 branch in
      `catalog-materialization`, the TTL cap in `tmdb-cache`, the trimmed
      cards in `chat-api` and `chat-ui`
- [ ] 4.9 Issue #180: tick the checklist; list the exceptions
- [ ] 4.10 Whoever merges last: `graphify update .`, and remove
      `openspec/changes/tmdb-cumplimiento/`
