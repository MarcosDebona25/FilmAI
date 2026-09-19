# Design: Initial Catalog Seed (C-04c)

## Where this runs

The seed is a **management command**, not a Celery task. It is a one-off that
runs for tens of minutes under someone's supervision, and a blocking command
with a progress counter is easier to watch, interrupt and resume than a task
whose only output is a log line an hour later.

```
$ docker compose exec backend python manage.py seed_catalogo --limite 2000
       │
       ▼
 seed_catalogo ──HTTP──▶ TMDB /genre/{tipo}/list      (once, cached 30 d)
       │        ──HTTP──▶ TMDB /discover/{tipo}        (per combination+page, cached 6 h)
       │
       └──▶ materializar(id, tipo) ──HTTP──▶ TMDB detail + credits + keywords
                    │                        (the same three calls the sync makes)
                    ├──SQL──▶ ProduccionAudiovisual
                    └──▶ on_commit → generar_embedding.delay() ──▶ Redis DB 1
                                                                       │
                                                        celery-worker ─┘  (fails until B-06)
```

Nothing new talks to anything new. The seed is a **third caller** of
`materializar()`, alongside the detail views (C-04a) and the sync (C-04b).

## Architecture Decisions

| Decision | Alternative rejected | Why |
|---|---|---|
| Sample across genre × decade × type | 500 pages of popularity-sorted discover | One unfiltered `discover` caps at 10 000 results, which is the whole target — but they would be this month's popular titles. The corpus *is* the semantic search space (B-06); a corpus of blockbusters can only recommend blockbusters. |
| `sort_by=vote_count.desc` within each combination | `popularity.desc` (the API default) | Verified live: 1980s sci-fi sorted by votes returns *Back to the Future*; by popularity it returns whatever trended this week. Vote count is a durable proxy for "this is a title people know", which is what a recommendation corpus wants. |
| Round-robin over combinations | Exhaust each combination before the next | The run is cut short by `--limite`, by Ctrl-C or by a laptop closing. Depth-first means an interrupted run holds every Action film and no Drama at all. Round-robin means an interrupted run is a smaller version of the same diverse corpus. |
| Shuffle combinations with a fixed seed | Iterate in declaration order | Same reason, one level down: cutting mid-round in declaration order biases toward whichever genre is listed first. A fixed seed keeps it deterministic, so a test can assert the order and a re-run covers the same ground. |
| Genres from `/genre/{tipo}/list` | A hard-coded list of ids | Genre ids are TMDB's, not ours. Verified: 19 movie genres, 16 TV. A list copied into the source is correct until the day it is not, and nothing would tell us. |
| Resume by consulting our own database | A progress file or a state table | `materializar()` already skips fresh rows. Loading `{(id_tmdb, tipo)}` once at startup makes resumption free and adds no state to keep in sync. The sync already uses this exact pattern. |

## Sampling

```python
# Décadas desde 1970: antes de eso TMDB tiene poco y disperso, y no es lo que
# un usuario del chatbot va a pedir. La década actual se incluye.
_DECADA_INICIAL = 1970

# (tipo_tmdb, id_genero, anio_desde, anio_hasta) — una por combinación.
# 19 géneros de película × 6 décadas + 16 de serie × 6 = 210 combinaciones.
```

Each round asks page *N* of every combination. One full round is at most
210 × 20 = 4 200 items, so `--limite 2000` does not even finish the first
round — which is exactly why the order is shuffled.

TMDB's date filters differ by type, and the client already knows this pattern
from `_DISCOVER_YEAR_PARAM`:

| Type | Parameters |
|---|---|
| `movie` | `primary_release_date.gte` / `.lte` |
| `tv` | `first_air_date.gte` / `.lte` |

`discover()` gains an optional year range alongside the existing single `anio`.
Additive: every current caller keeps working.

## The 500-page wall

**Verified live on 18/09/2026**: `/discover/movie` reports `total_pages: 1001`,
but requesting page 501 answers **HTTP 400** — *"Pages start at 1 and max at
500"*. `total_pages` is not a promise.

Any pagination here must stop at `min(total_pages, 500)`. This is the same
class of mistake as trusting `/changes` to have 74 pages when it had 98
(C-04b): the API's own numbers are input, not truth. In practice the
combinations are small enough (1 592 pages' worth of 1980s sci-fi is 80 pages)
that the wall is only reachable for the broadest ones — which is precisely when
a silent `TMDBBadRequest` would abort a four-hour run near the end.

## Pacing and failure

TMDB publishes **no rate-limit headers** and 20 rapid calls drew no `429`
(verified 18/09/2026). The client already retries `429` and `5xx` with
exponential backoff and honours `Retry-After`, so the seed adds no pacing logic
of its own; `--pausa` exists as a manual brake if a long run starts drawing
`429`s.

Failures are **per item**, the same policy as the sync and the detail views: a
title TMDB cannot return is logged, counted, skipped. A four-hour run must not
die on item 3 000.

## Cost

Per production: 3 TMDB calls (detail, credits, keywords) at ~0.5 s each,
measured. Plus roughly one `discover` call per 20 items.

| Target | Calls | Wall time |
|---|---|---|
| 2 000 | ~6 100 | ~50 min |
| 10 000 | ~30 500 | ~4 h |

Redis caches detail, credits and keywords for 24 h, so a re-run on the same day
is dramatically faster — but a fresh corpus pays full price. This is why
`--limite` defaults to 2 000: a useful corpus you can watch finish today beats
a perfect one that needs the machine awake all night.

## The `manage.py seed` hazard

`usuarios/management/commands/seed.py` calls
`ProduccionAudiovisual.objects.all().delete()` to reset development data. After
C-04c that is no longer a cheap reset — it is four hours of TMDB calls thrown
away, and the command gives no warning.

The seed command refuses to wipe a populated catalog unless told to: above a
threshold it aborts and names the flag that overrides it. The alternative —
documenting the hazard in the README — relies on somebody having read it at the
moment they are trying to reset their database.

## Testing Strategy

| Level | What |
|---|---|
| Unit | Combination building: genres × decades × types, correct date parameters per type, deterministic shuffle |
| Unit | Pagination stops at `min(total_pages, 500)` even when TMDB reports more |
| Unit | `--limite` caps materializations and stops mid-round |
| Unit | Already-stored fresh rows are skipped without calling `materializar()` |
| Unit | One failing item does not abort the run |
| Integration | With `materializar()` real and TMDB faked: rows land enriched, a second run adds nothing |
| Live | `--limite 50` against real TMDB, then query the database for decade and genre spread |

`get_genres` gets the same two tests every client method has: it hits the right
path, and it reuses the shared error mapping.
