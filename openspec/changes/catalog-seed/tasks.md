# Tasks: Initial Catalog Seed (C-04c)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~420-500 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes — two |
| Suggested split | PR1 (client) → PR2 (command) |
| Delivery strategy | ask-on-risk |
| Chain strategy | independent PRs off `main` |

> Lesson carried from C-04b: a commit pushed while a PR is being squashed is
> lost. Push, then confirm against `origin/main` that it landed.

### Suggested Work Units

| Unit | Goal | Likely PR | Est. lines | Focused test command | Rollback boundary |
|------|------|-----------|-----------:|----------------------|-------------------|
| 1 | `get_genres` + year range on `discover` (client + cache) | PR 1 | ~120 | `... test catalogo.tests.TMDBGenresTest catalogo.tests.TMDBClientCacheTest` | Revert both methods; nothing else uses them yet |
| 2 | `seed_catalogo` command + the `seed` guard + docs + spec | PR 2 | ~330 | `... test catalogo.tests.SeedCatalogoTests` | Delete the command; the catalog keeps working on C-04b alone |

## Phase 1: Client support

- [ ] 1.1 RED: add `TMDBGenresTest` — `get_genres(tipo)` hits `/genre/{tipo}/list` for both types and reuses the shared error mapping; add the cache-layer case for the new `"genres"` TTL (30 d: genre ids are effectively static)
- [ ] 1.2 GREEN: add `get_genres` to `client.py` and `cache.py`
- [ ] 1.3 RED: add cases asserting `discover()` accepts a year range and sends the parameters TMDB expects **per type** — `primary_release_date.gte/.lte` for movies, `first_air_date.gte/.lte` for series — and that the existing single-`anio` callers are unaffected
- [ ] 1.4 RED: add a case asserting `discover()` forwards `sort_by` when given
- [ ] 1.5 GREEN: extend `discover()` additively
- [ ] 1.6 Full suite + `ruff format . && ruff check .`

## Phase 2: The seed command

- [ ] 2.1 RED: add `SeedCatalogoTests` — combinations are built from the genre lists, both types, decades from `_DECADA_INICIAL`, with the right date parameters for each type
- [ ] 2.2 RED: the combination order is shuffled deterministically — same seed, same order — so an interrupted run is still diverse and a test can assert it
- [ ] 2.3 RED: pagination stops at `min(total_pages, 500)` **even when TMDB reports more** (it reports 1001 and rejects 501 — verified live 18/09/2026)
- [ ] 2.4 RED: `--limite` caps how many productions are materialized, stopping mid-round
- [ ] 2.5 RED: a production already stored and fresh is skipped **without calling `materializar()`** (resumability) and counted separately
- [ ] 2.6 RED: one failing item is logged, counted and skipped; the run continues
- [ ] 2.7 GREEN: implement `seed_catalogo`, round-robin over shuffled combinations
- [ ] 2.8 Progress output: current count, target, and which combination is being read; final summary `{materializadas, ya_estaban, omitidas, errores}`
- [ ] 2.9 RED + GREEN: `manage.py seed` refuses to delete a populated catalog above a threshold unless overridden, and says which flag overrides it
- [ ] 2.10 Integration test with `materializar()` real and TMDB faked: rows land enriched with a non-null `fecha_enriquecimiento`; a second run materializes nothing new
- [ ] 2.11 **Live run**: `--limite 50` against real TMDB; then query the database for the spread of decades, genres and types — assuming diversity is not verifying it
- [ ] 2.12 Create `openspec/specs/catalog-seed/spec.md` (Given/When/Then, RFC 2119)
- [ ] 2.13 `README.md` (how to run it, how long it takes, that it is resumable), `docs/decisiones.md`, `docs/05_Plan_de_Desarrollo.md` (C-04c done)
- [ ] 2.14 Full suite + ruff; `graphify update .`; delete `openspec/changes/catalog-seed/` per `AGENTS.md` §9

## Open question, to settle with real numbers

At 2 000 the corpus is useful; the plan's target is 10 000. Once `--limite 50`
has run and the spread is visible, decide whether 2 000 is enough for B-06 to
be interesting or whether it is worth leaving the machine on for the full run.
That decision needs the seed to exist first, so it is not a blocker here.
