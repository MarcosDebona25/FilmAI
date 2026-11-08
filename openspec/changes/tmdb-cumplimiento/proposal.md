# Proposal: TMDB terms of use compliance (issue #180)

## Intent

FilmAI's catalog, images and chatbot all run on TMDB. TMDB's API terms ask
four things of every application: credit TMDB in an «About» or «Credits»
section with an exact notice and its logo, respect its brand, cache nothing
for longer than 6 months, and stay away from commercial use (which, for
TMDB, includes chatbots and ML). Sources: `docs/tmdb-legales/` (the summary in
`Consideraciones Legales TMDB.txt` and the official logos `logo1.svg` …
`logo5.svg`).

Today FilmAI meets none of the four on paper:

1. **Attribution.** The footer (`footer.main.tmdbAttribution`) says «Data and
   images provided by TMDB. FilmAI is an independent project and is not
   affiliated with or endorsed by TMDB.» It is close in meaning but it is not
   the text TMDB asks for, there is no logo, and there is no «About» or
   «Credits» section.
2. **Brand.** No TMDB logo is shown anywhere, so there is nothing to check yet.
3. **Persistence.** `ProduccionAudiovisual` refreshes a row only when TMDB
   lists it as changed or when someone opens it after 90 days
   (`_DIAS_RED_DE_SEGURIDAD`). A row nobody opens and TMDB never lists can stay
   forever, and so can rows born from a listing that were never enriched
   (`fecha_enriquecimiento` NULL). Chat messages keep each card's title and
   poster with no expiry (`Mensaje.tarjetas`, `Chat.contexto.ya_recomendados`).
4. **AI use.** The terms forbid using TMDB content in ML or AI applications and
   chatbots without a commercial agreement. That was decided on 07/11/2026
   (issue #180): FilmAI is an academic, non-profit project, and that covers
   the current chatbot and embeddings. If it is ever commercialized, a meeting
   with TMDB's commercial team is evaluated. It is not yet in
   `docs/decisiones.md`.

This change turns the issue into a contract (`specs/tmdb-compliance`) and a
task list.

## What was already decided

| Date | Where | What it fixes |
|---|---|---|
| 07/11/2026 | Issue #180 | Academic, non-profit use covers the chatbot and embeddings; commercialization ⇒ talk to TMDB first. Accepted risk |
| 07/11/2026 | This change, with Marcos | Credits go in a section of `/terms` (`/terms#credits`), not a new page |
| 07/11/2026 | This change, with Marcos | Chat cards older than 6 months are trimmed to `{id_tmdb, tipo}` and rehydrated from the local catalog when read |
| 07/11/2026 | This change, with Marcos | The access-screen collage (`frontend/public/collage-posters/Opcion 1.jpg`) and the test fixtures copied from TMDB (`frontend/e2e/api-simulada.ts`, `backend/catalogo/test_datos/tmdb_buscar.json`) are **out of scope**: they are recorded as exceptions, not changed |
| 09/10/2026 | `docs/decisiones.md` | Cards stored as shown, no FK. This change narrows it: as shown **for 6 months** |
| 16/10/2026 | `docs/decisiones.md` | Redis backup of 30 days (`RESPALDO_TTL`). Already under 6 months; kept |

## Scope

### In Scope

- **Attribution.** The exact notice «This product uses the TMDB API but is not
  endorsed or certified by TMDB.» with its Spanish translation (en/es parity),
  in a «Credits» section of `/terms` with the logo and a link to
  `https://www.themoviedb.org`. The footer keeps a short line, now pointing to
  that section.
- **Brand.** One official logo, chosen in the Claude Design canvas when
  development starts (none is fixed here), copied as-is to `frontend/public/`,
  shown in both themes, smaller and quieter than FilmAI's mark, with translated
  alternative text. An audit of every mention: only «TMDB» or «The Movie
  Database», in the UI, the emails, the chatbot prompts and the docs; every
  link to the site points to `https://www.themoviedb.org`.
- **Persistence (6 months).** An inventory of everything stored from TMDB, a
  nightly Celery task that refreshes the oldest catalog rows before they turn
  150 days old, a rule for titles TMDB no longer has, and the trimming of chat
  cards. Tests that pin the cap.
- **API use.** Measure the request rate of the seed, the nightly sync and
  `rellenar_traducciones` against the ~40 requests per second ceiling; keep
  honoring 429 (Too Many Requests); confirm TMDB images are only used as part
  of the catalog.
- **AI use.** The 07/11/2026 decision recorded in `docs/decisiones.md`, and the
  condition (no revenue from TMDB content) written down where it will be seen.
- **Docs.** `docs/decisiones.md`, `docs/04_Lineamientos_UI.md` (logo and
  attribution), `docs/06_TMDB_API_Referencia.md` (persistence and limits), the
  new canonical spec `tmdb-compliance`, and the notes in the specs it touches
  (`catalog-daily-sync`, `catalog-materialization`, `tmdb-cache`, `chat-api`).

### Out of Scope

- **The access-screen collage and the test fixtures** (decision of 07/11/2026
  above). The collage was committed on 13/08/2026, so it reaches 6 months on
  13/02/2027; that date goes into the decision entry so the exception is
  revisited, not forgotten.
- **A commercial agreement with TMDB.** Only if FilmAI is commercialized.
- **A new `/about` page.** Credits live in `/terms`.
- **Merchandise or packaging** with TMDB's name or logo. There is none.
- **Redesigning `/terms` on desktop** (pending on its own; the credits block
  follows the current mobile canvas).

## Risks and rollback

| Risk | Mitigation | Rollback |
|---|---|---|
| The refresh task floods TMDB or starves the worker | A per-run cap (`CELERY_REFRESCO_LIMIT`), oldest first, after the 03:00 sync; every call goes through the client that honors 429 and `Retry-After` | Remove the beat entry; rows go back to being refreshed only by the sync and the 90-day net |
| A title TMDB deleted (404 (Not Found)) can never be refreshed, and deleting the row cascades to users' ratings, reviews and lists | Rows nobody references are deleted; referenced rows have their TMDB text blanked and are flagged, so the UI shows them as unavailable (design, «Titles TMDB no longer has»). **To confirm with Gonza before PR 2 merges** | Drop the 404 branch: the row stays as it was and is logged |
| Trimming cards changes what an old conversation looks like | Rehydration from the local catalog shows the current title and poster, in the reader's language; only an id that is no longer in the catalog falls back to a neutral card | Stop the trimming step; trimmed cards stay rehydrated, which is still correct |
| The chosen logo reads poorly on one theme | The variant, size and theme treatment are designed in the canvas before implementing (task 1.0); no logo is fixed in this plan | Swap the SVG file |
| The non-profit condition is broken later (ads, subscriptions) without anyone remembering #180 | Decision entry in `docs/decisiones.md` and a line in `PRODUCT.md` (task for whoever integrates) | — |

Each PR in `tasks.md` names its own rollback boundary.
