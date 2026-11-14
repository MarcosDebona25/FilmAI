# Proposal: Search in the navbar, a person filter and hiding irrelevant titles

## Intent

Three pending items of Search (C-06) that Gonza decided on 13/11/2026:

1. **Search in the desktop navbar.** Today Search is a link on the left of the
   navbar («Home · Search · Lists») that opens `/search`. Gonza looks for a
   field or a magnifier on the right, next to the account, and does not find
   it. A magnifier moves there; pressing it unfolds a field in the same place
   that suggests results while typing.
2. **Filter Search by actor or director.** Suggestions include people
   («Christopher Nolan · Director») that open Search filtered by that person.
   The same filter is available in the filters panel.
3. **Hide titles with no relevance.** A text search brings TMDB's long tail:
   «chihiro» returns 13 titles and 10 of them are things like «La arquitectura
   de El Viaje de Chihiro» (a video with 1 vote). They are left out of the
   results, unless one is named exactly as the text.

This change turns the three into a design (`design.md`), contracts (`specs/`)
and a task list split in small PRs (`tasks.md`). Nothing is implemented here.

## What is already decided

| Date          | Where                                  | What it fixes                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------- | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 13/11/2026    | Gonza                                  | Search in the right of the desktop navbar, next to the account, with up to ~5 suggestions; Enter or «See all results» opens `/search?q=…`; the «Search» link leaves the desktop navbar; mobile tabs (`MobileTabs`) stay as they are. **Variant (14/11/2026): a magnifier that unfolds into a field in the same place**; Gonza chose it after seeing an artifact with the 4 variants. The always-visible field of the first plan is discarded: it took room from the links on medium widths and competed with the page's own field |
| 13/11/2026    | Gonza                                  | Suggestions include actors and directors, which open Search with a new person filter                                                                                                                                                                                                                                                                                                                                                    |
| 13/11/2026    | Gonza                                  | In a text search, only titles with 5 votes or more, or popularity 5 or more, are shown; the rest are not shown, except a title (translated or original, without accents or case) equal to the text; if none passes, show everything. **No «See N more results» button**: people would press it and pay attention to what is irrelevant (first proposal, discarded the same day). `video`, synopsis and `adult` are discarded as signals |
| 05–06/11/2026 | Team notes                             | The person filter is a medium PR: a field with suggestions over TMDB `search/person`, `combined_credits` and in-memory filters. `discover` with `with_people` does not work (TMDB ignores it for shows) and neither does the local catalog                                                                                                                                                                                              |
| 14/10/2026    | `docs/decisiones.md` («Buscar (C-06)») | `/search` is a page; text search reads the first 100 per type and sorts by `max(votes, popularity × 100)`; `search/multi` was discarded for the grid because it mixes people                                                                                                                                                                                                                                                            |
| 13/10/2026    | `catalogo/services/creditos.py`        | For shows the title page lists the creators (`created_by`) as «Created by» instead of directors                                                                                                                                                                                                                                                                                                                                         |
| 24/10/2026    | `catalogo/presupuesto.py`              | 30 TMDB calls per request, 300 per IP per minute; answers from Redis cost nothing                                                                                                                                                                                                                                                                                                                                                       |

## Scope

### In Scope

- **Suggestions endpoint** `GET /api/catalogo/suggest/?q=` on TMDB
  `search/multi` (one call), with titles and people, the relevance cut, Redis
  cache and its own throttle scope.
- **Navbar magnifier** (desktop only) that unfolds into a field with an ARIA
  1.2 combobox: keyboard, `aria-activedescendant`, announcements, «See all
  results», optional `/` shortcut that unfolds it. The magnifier is a button
  with `aria-expanded` and `aria-controls`; the field closes with Esc, ✕ or
  on blur without text. Hidden on `/search`, where the page has its own field.
- **Person filter** in `browse/` (`persona`, `rol`) over `combined_credits`,
  combined in memory with type, genre, year, rating and text; a «Person» field
  in the filters (desktop row and mobile sheet) and, when active, a chip with
  ✕ above the results.
- **Relevance cut** in `browse/` (and in suggestions) with text or person:
  irrelevant titles are left out before counting and paginating, except an
  exact title match; if nothing passes, everything shows. Backend only: the
  answer keeps its shape and the infinite scroll is unchanged.
- **Proposal, separate PR**: names in the title page's «Director and cast»
  link to Search filtered by that person.
- **Docs**: `docs/decisiones.md`, `docs/05_Plan_de_Desarrollo.md`,
  `docs/04_Lineamientos_UI.md` (navbar), the canonical specs it touches
  (`search-ui`, `tmdb-endpoints`, `title-page-ui`) and a new `navbar-search`.

### Out of Scope

- **Mobile.** `MobileTabs` keeps its «Search» tab and `/search` keeps its
  field. No field in the mobile header.
- **A person page** (`/person/{id}` with biography and photo). The filter is
  enough for «what did Nolan direct».
- **Semantic search in the field** (B-06 vectors). Suggestions are by name.
- **Recent searches** in the dropdown. Could come later; it needs storage per
  viewer and a privacy decision.
- **Writers, producers and other crew** as suggestions or filter roles (see
  open question Q-3).

## Open questions for Gonza

Each has a recommendation; `design.md` follows it until Gonza answers.

| #   | Question                                                              | Recommendation                                                                                                                                                                                                                           |
| --- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q-1 | What counts as «director» of a show                                   | **The creators** (`job: "Creator"` in `combined_credits`), as the title page already does. Episode directors add noise (a director with one episode of a show would list it)                                                             |
| Q-2 | Role in the filter: fixed by the suggestion, or «any role»?           | **Fixed by the suggestion** (`role=director` or `role=actor`), shown in the chip («Christopher Nolan · Director»); the chip only has ✕. To change the role, pick the person again. «Any role» exists in the API for the title page links |
| Q-3 | People known for writing or production (Vince Gilligan, «Writing»)    | **Out of v1**: only `Acting` and `Directing` are suggested. Revisit with usage                                                                                                                                                           |
| Q-4 | On `/search`, hide the navbar field or keep it in sync with the page? | **Hide it**: the page already has a big field with focus; two fields with the same text confuse and fight for Escape and `/`                                                                                                             |
| Q-5 | Order of the person's filmography without text                        | **The same as text search** (`max(votes, popularity × 100)`): best known first. Alternative: newest first, like a filmography                                                                                                            |
| Q-6 | `/` shortcut to focus the field                                       | **Yes**, desktop only, unfolds the magnifier and focuses the field; ignored while typing in another field or with a dialog open, with a `kbd` hint in the field                                                                                                                       |
| Q-7 | Links from the title page's cast and directors to Search              | **Yes, as its own last PR** (needs the person id in `credits/`); it can be dropped without touching the rest                                                                                                                             |
| Q-8 | Label of actors in Spanish                                            | **By TMDB's `gender`**: «Actor» / «Actriz», «Director» / «Directora»; unknown gender → «Actuación» / «Dirección». English: «Actor» / «Actress», «Director»                                                                               |

## Risks and rollback

| Risk                                                                             | Mitigation                                                                                                                                                   | Rollback                                                               |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| Typing fires many requests and hits the 60/min `catalogo` limit                  | 250 ms debounce, 2 characters minimum, in-flight requests aborted, a session cache per text, and its own scope `sugerencias` (120/min); 1 TMDB call per text | Remove the field from the navbar; the «Search» link comes back         |
| The unfolded field covers the left links on medium widths                        | The field unfolds over the links only while it has focus, and collapses on Esc, on ✕ or on blur without text; the magnifier itself never changes the bar's layout | Show the magnifier at every width and drop the unfolded field           |
| The cut leaves out a title someone wanted (an obscure upcoming film)             | Typing its exact name brings it back; if nothing passes, everything shows; the constants live in one place                                                   | Set both thresholds to 0: nothing is hidden                            |
| `combined_credits` of a prolific actor is large (Tom Hanks: 369 credits, 245 kB) | One call cached for 24 h; filtered and paginated in memory; talk and news shows dropped from acting credits                                                  | Remove `persona` from `browse/`; the field and the chip go with the PR |
| A shared URL with `person=` of someone TMDB deleted                              | `browse/` answers 404 (Not Found) with `person_not_found` and the page offers «Clear filters»                                                                | —                                                                      |

Each PR in `tasks.md` names its own rollback boundary.
