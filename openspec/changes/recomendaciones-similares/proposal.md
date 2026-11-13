# Proposal: Similar titles for lists and title pages (pendiente 5)

## Intent

A list with titles suggests nothing today, and the title page ends without a
"what next". FilmAI already has what it needs to answer both: every title in
the local catalog (6 150 rows on 13/11/2026, 6 077 with a `ready` vector) has a
bge-m3 embedding (B-06), and pgvector can find its nearest neighbours in a few
milliseconds. No model has to be trained.

This change adds **one similarity engine** and two places that use it:

1. **«Suggested for this list»**: a horizontal row at the end of a list's
   detail (`/lists/[id]`), in custom lists and Favorites, with about 10 cards,
   a one-click «+ Add» on each and a «Refresh» button that shows others.
2. **«More like {title}»**: a horizontal row on every title page
   (`/movie/[id]`, `/tv/[id]`), visible with or without a session.

A title page is a list of one title: both ask the engine for the neighbours of
a set of seeds and fall back to TMDB `/recommendations` when the local catalog
has few close ones.

## What is already decided

| Source                                             | What it fixes                                                                                                                                                                                                                                                         |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/05_Plan_de_Desarrollo.md`, «Mejoras futuras» | Average the B-06 vectors of the list, add the list name when it says something, nearest neighbours in pgvector without the list and «Vistas»; fill with TMDB `/recommendations`                                                                                       |
| Gonza, 13/11/2026 (lists)                          | Custom lists and Favorites only (not Pendientes nor Vistas); a row at the end of the detail, «Suggested for this list», ~10 cards with «+ Add» to that list and a «Refresh» button; works from 1 title; the name joins the vector if it says something; TMDB fills in |
| Gonza, 13/11/2026 (title page)                     | Same engine; exclude «Vistas» with a session; movies and shows mixed, each marked with its type; visible without a session, excluding nothing                                                                                                                         |
| `docs/decisiones.md`, 04/11–07/11/2026             | `bge-m3` through Ollama, `hnsw.ef_search = 100`, preload with `calentar_modelo`, cold loads of more than 20 s with little memory                                                                                                                                      |
| `docs/decisiones.md`, 05/11/2026 (chatbot)         | `/recommendations`, not `/similar` (_Paddington 2_ brought _The Lord of the Rings_)                                                                                                                                                                                   |
| `catalogo/presupuesto.py`                          | 30 TMDB calls per request, 300 per IP per minute; what comes from Redis does not count                                                                                                                                                                                |
| `listas/models.py`, `listas/views.py`              | 100 custom lists, 1 000 items per custom list; `_lista_propia` answers 404 (Not Found) for someone else's list; adding an item materializes it                                                                                                                        |

## Decisions (answered by Gonza, 13/11/2026)

All follow the recommendation below except D-6, which changed: see the table
and `design.md` §11.

| #   | Question                                                  | Decision                                                                                                                                   |
| --- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| D-1 | Weight of the list name in the vector                     | `w = max(0.15, 1 / (n + 1))`: half with 1 title, 0.15 from 6 titles on                                                                     |
| D-2 | When the name «says something»                            | A deterministic rule: some word of 3 or more letters left after removing digits and a short list of filler words                           |
| D-3 | Lists of a single type                                    | Only movies → only movies; only shows → only shows; mixed → mixed                                                                          |
| D-4 | Favorites excludes «Vistas» like the rest?                | Yes, the same rule everywhere (suggestions are for discovering)                                                                            |
| D-5 | Minimum quality of a local candidate                      | Poster required; TMDB rating present (at least one vote); TMDB fill without `adult` and with 10 votes or more                              |
| D-6 | Where the list row lives with infinite scroll and filters | **Decided otherwise**: always at the end, also with a filter or search active; after the last loaded page; suggestions from the whole list |
| D-7 | Title page: how many cards and Refresh?                   | Up to 20 (two desktop pages of the row), no Refresh                                                                                        |
| D-8 | Copy in English and Spanish                               | The keys of `design.md` §9, to approve with the canvas                                                                                     |
| D-9 | Ollama not loaded: wait for the name or skip it?          | Skip it without waiting, ask for the load, and cache that answer for 5 minutes only                                                        |

## Scope

### In Scope

- **Engine** `catalogo/services/similares.py`: seed vector, candidates in
  pgvector with in-SQL exclusion, TMDB fill, a pool of up to 60 cached in Redis
  and a reproducible weighted shuffle that `Refresh` pages through.
- **Title endpoint** `GET /api/catalogo/{movie|tv}/{id_tmdb}/similar/`: public,
  with the pool cached per title and the «Vistas» of a session removed after
  the cache.
- **List endpoint** `GET /api/lists/{id}/suggestions/?pagina=N`: owner only,
  custom lists and Favorites, with the list name in the vector.
- **Frontend**: `MediaRow` gains an action slot per card and one for the
  header; the list row with «+ Add» and «Refresh»; the title page row loaded
  when it gets near the viewport. Designed first in the Claude Design canvas.
- **e2e** for both rows with a controlled API.
- **Docs**: canonical specs, `docs/decisiones.md`, doc 05, `contracts/`.

### Out of Scope

- **Training or fine-tuning** anything. Vectors stay those of B-06.
- **Changing the canonical text** of the embeddings (adding country or
  language): it changes the hash of all 6 150 rows and forces a full
  regeneration. Noted as a follow-up in `design.md` §8.
- **Clustering heterogeneous lists** (several centroids). Considered in
  `design.md` §3; left for after real use.
- **Suggestions in the chatbot or the Home.** The engine is reusable, but
  each needs its own decision.
- **The mass catalog population.** Quality grows with it; this change works
  with today's 6 150 titles.

## Risks and rollback

| Risk                                                                                          | Mitigation                                                                                                                 | Rollback                                           |
| --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| A heterogeneous list (horror + cartoons) averages into a vector close to neither              | Measured at the end of PR 2 with three real lists; the multi-centroid follow-up is described                               | —                                                  |
| HNSW with a `WHERE` returns fewer rows than asked (measured: 0 of 100 with 1 000 excluded)    | `hnsw.iterative_scan = relaxed_order` (pgvector 0.8.6 is installed); test with a list of 1 000 neighbours                  | Over-fetch `limit + excluded` and filter in Python |
| Ollama down makes every request pay the 1 s of `modelo_cargado()`                             | The unavailability is cached for 60 s; the name is optional                                                                | Name weight 0 by setting                           |
| TMDB fill brings titles from another country or language (`/recommendations` groups by theme) | Local candidates always go first; TMDB only completes                                                                      | —                                                  |
| The title page gets slower                                                                    | Separate endpoint, requested only when the row nears the viewport; the detail does not wait for it                         | Remove the row from `TitleView` (one component)    |
| The public cache leaks what a user watched                                                    | The cached pool never depends on the user; «Vistas» is removed after reading it and the answer with a session is `private` | —                                                  |

Each PR in `tasks.md` names its own rollback boundary.
