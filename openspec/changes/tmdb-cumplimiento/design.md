# Design: TMDB terms of use compliance (issue #180)

## Where this lives

```
Frontend (Next.js)                                   Backend (Django + Celery)
──────────────────                                   ─────────────────────────
Footer ── short notice + link ──▶ /terms#credits     celery-beat
app/terms/page.tsx                                     ├─ 03:00 catalogo.sync_catalogo_diaria   (exists)
 └─ <TmdbCredits/>  notice · logo · link               ├─ 03:30 catalogo.refrescar_vencidos     (new)
public/tmdb/logo-*.svg (official, unmodified)          │        └─ materializar(forzar=True) ──▶ catalogo/client.py ──▶ TMDB
                                                       ├─ 04:00 catalogo.backfill_embeddings    (exists)
Chat history                                           └─ 04:30 chatbot.recortar_tarjetas       (new)
 └─ GET /api/chat/messages/ ── rehydrates trimmed cards from ProduccionAudiovisual
```

New code: `catalogo/services/vencimiento.py` (which rows are due and what to
do with each), two tasks, one small component and the rehydration in the chat
serializer. Nothing in the request path calls TMDB because of this change.

## Inventory of what FilmAI stores from TMDB

The 6-month clock applies to TMDB **content** (texts, image paths, ratings,
lists of names). Ids (`id_tmdb`, `tipo`, `generos_ids`) are references, not
content, and are kept as long as the row exists.

| Store                                                                         | What it holds                                                                        | Today's maximum age                                                                          | After this change                                                                                                 |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `ProduccionAudiovisual`                                                       | Title, synopsis, poster, cast, directors, genres, keywords, rating, runtime, seasons | Unbounded if TMDB never lists it as changed and nobody opens it; unbounded if never enriched | Refreshed before 150 days; ≤ 180 days guaranteed (see below)                                                      |
| `ProduccionTraduccion`                                                        | Title, synopsis, poster per language                                                 | Same as its production                                                                       | Rewritten in the same `_enriquecer()` call (task 2.1 verifies it overwrites, not only fills gaps)                 |
| `ProduccionEmbedding`                                                         | Vector of the canonical text                                                         | Same as its production                                                                       | Re-embedded when the refresh changes `source_hash`; an unchanged text means the vector already matches fresh data |
| `Mensaje.tarjetas`                                                            | `{id_tmdb, tipo, titulo, poster, anio}`                                              | Forever                                                                                      | `titulo`, `poster`, `anio` removed after 180 days                                                                 |
| `Chat.contexto.ya_recomendados`                                               | Last 30 cards as `{id_tmdb, tipo, titulo, anio}`                                     | Forever for an idle chat                                                                     | Each entry gets `fecha`; after 180 days only `{id_tmdb, tipo, fecha}` remain                                      |
| Redis, normal keys                                                            | API responses                                                                        | 30 days (`genres`)                                                                           | Unchanged                                                                                                         |
| Redis, backup (`RESPALDO_TTL`)                                                | Last good response                                                                   | 30 days                                                                                      | Unchanged; a test pins every TTL ≤ 180 days                                                                       |
| Browser cache                                                                 | API responses                                                                        | `Cache-Control` of the catalog views                                                         | Task 2.8 checks no `max-age` exceeds 180 days                                                                     |
| `frontend/public/collage-posters/Opcion 1.jpg`                                | A collage of posters                                                                 | Since 13/08/2026                                                                             | **Out of scope** (07/11/2026); revisit by 13/02/2027                                                              |
| Test fixtures (`e2e/api-simulada.ts`, `catalogo/test_datos/tmdb_buscar.json`) | Copies of TMDB responses                                                             | Since they were written                                                                      | **Out of scope** (07/11/2026): test data, never served                                                            |

`Calificacion`, `Resena` and list items hold user data plus a foreign key to
the production; they store no TMDB content of their own.

## Catalog rows: the refresh task

**Reference field: `fecha_enriquecimiento`.** It already says when the detail
was last fetched from TMDB, and it is written in the same `save()` as the
data. No new column. A row is **due** when

```
fecha_enriquecimiento IS NULL  OR  fecha_enriquecimiento < now − DIAS_REFRESCO_TMDB (150)
```

NULL rows are due on purpose: they were born from a listing, already carry a
title and a poster, and have no date to start the clock from. Enriching them
is also what the catalog wants anyway (they lack genres, cast and keywords).

**`catalogo.refrescar_vencidos`**, daily at 03:30, after the sync and before
the embedding backfill (so the backfill at 04:00 picks up re-embeddings):

1. Select due rows, NULL first, then oldest `fecha_enriquecimiento`, capped at
   `CELERY_REFRESCO_LIMIT` (300).
2. For each one, `materializar(id_tmdb, tipo, forzar=True)`, the single write
   path required by `catalog-materialization`. One item failing does not stop
   the rest, as in the sync.
3. Log a summary: refreshed, not found, failed, and **how many rows are still
   older than 180 days** (with `logger.warning` if any).

**Why 150 and 300.** 30 days of margin cover a week of failed nights. With a
corpus of ~10 000 rows the steady state is 10 000 / 150 ≈ 67 rows a day; 300
leaves room for the first runs, which find every NULL row and every row seeded
in August due at once, and drains a full backlog in ~34 nights. Both values
live in `settings.py`; the summary's «still older than 180 days» number says
when to raise them.

**Why not deleting.** `Calificacion`, `Resena` and `Tiene` (list items) point to
`ProduccionAudiovisual` with `on_delete=CASCADE`. Deleting a
stale row would delete a user's rating. Refreshing is the only option that
keeps both promises.

**Interaction with what exists.** The sync's change-list refresh and the
90-day net of `_necesita_enriquecimiento` stay: they keep popular rows fresher
than 150 days. The new task only catches what they miss. A row the sync just
refreshed is no longer due, so nothing is enriched twice.

### Titles TMDB no longer has

`materializar(forzar=True)` on an id TMDB answers with 404 (Not Found):

- **No user references** (no rating, review, list item): delete the row
  (translations and embedding go with it by CASCADE).
- **Referenced**: keep `id_tmdb` and `tipo`, blank every TMDB content field,
  set `fecha_enriquecimiento = now` (so it is not retried every night) and set
  a new boolean `disponible_en_tmdb = False`. Serializers and cards show it as
  «Title no longer available» (new copy key, en/es). The embedding row is
  deleted so semantic search cannot return it.

This needs one migration (`disponible_en_tmdb`, default `True`). **Open: to
confirm with Gonza before PR 2 merges** (proposal, risks). If rejected, the
fallback is to keep the row as it is and log it; it would then be the one
known case over 180 days.

## Chat cards: trimming and rehydration

Decision of 07/11/2026: cards older than 6 months keep only ids, and the
history rebuilds them from the local catalog.

- **`chatbot.recortar_tarjetas`**, daily at 04:30: for messages with
  `fecha_hora < now − 180 days` whose cards still have `titulo`, rewrite each
  card as `{id_tmdb, tipo}`. Batched with `bulk_update`; idempotent.
- **`ya_recomendados`**: the orchestrator writes `fecha` (ISO date) on every
  entry; a card shown again refreshes it. The same task strips `titulo` and
  `anio` from entries older than 180 days. Entries without `fecha` (written
  before this change) are treated as old. The prompt builder resolves titles
  of stripped entries from `ProduccionAudiovisual` in one query; an id not in
  the catalog is left out of the «Ya recomendados» line but stays in the set
  that prevents repeats.
- **History `GET`**: the serializer detects a trimmed card (no `titulo`) and
  rehydrates it from `ProduccionAudiovisual` in the reader's language
  (`texto_localizado`, the same helper lists use), with one prefetch for the
  page, not one query per card. A missing or unavailable production yields
  the card with `titulo: null`; the panel renders the «Title no longer
  available» placeholder and no link.
- **The 09/10/2026 decision** (cards stored as shown, no FK, no
  `materializar()` per card) still holds for the first 180 days, which is
  where every live conversation is. Rehydration reads only the local table and
  never calls TMDB.

## Attribution and brand

### The Credits section

`/terms` renders the legal Markdown (`frontend/content/legal/terms.{locale}.md`
via `loadTerms`) and then a `<TmdbCredits />` block with `id="credits"`,
because Markdown cannot carry the logo with its rules (size, alt, theme). The
block holds, in this order:

1. A heading «Credits» / «Créditos».
2. The logo as a link to `https://www.themoviedb.org` (`rel="noopener"`,
   accessible name from the alt text).
3. The exact notice: «This product uses the TMDB API but is not endorsed or
   certified by TMDB.» Spanish: «Este producto usa la API de TMDB, pero TMDB no
   lo respalda ni lo certifica.» (to approve in `traducciones/claves.csv`).

The footer replaces `footer.main.tmdbAttribution` with the same notice and a
link «Credits» to `/terms#credits`. The legal Markdown's third-party clause
(`legal.thirdParty.tmdb`) keeps its liability sentence and uses the same
notice instead of «not affiliated with or endorsed by». The `/terms` route
stays in `lib/routes.ts`; the anchor is built from it, never written as a
literal.

### The logo

**Not decided yet (07/11/2026).** Which logo, its size, and how it sits on
each theme are decided in the Claude Design canvas when development of this
change starts (task 1.0), not in this plan. Until then no variant is fixed.
What the design MUST respect, whatever is chosen:

- **Official file:** one of `docs/tmdb-legales/logo1.svg` … `logo5.svg`,
  copied byte for byte to `frontend/public/tmdb/`.
- **Unmodified:** no `fill` override, no CSS filter, no `currentColor`; served
  as `<img>` so the theme cannot recolor it. Fixed height with `width: auto`
  so the aspect ratio holds. Not rotated or flipped.
- **Less prominent than FilmAI:** smaller than FilmAI's mark, and never in
  the header, the hero, the chat or next to a title, so it cannot read as an
  endorsement.
- **Both themes:** it must read well on the light and the dark theme. Only
  white, black or TMDB's approved colors (`#0d253f`, `#01b4e4`, `#90cea1`);
  how to get there (variant, surface behind it) is part of the canvas
  decision.
- **Alt text:** «TMDB logo» / «Logo de TMDB», from the catalogs.

### Naming audit

Only «TMDB» or «The Movie Database». The audit covers `traducciones/*.csv`,
`frontend/messages/`, `frontend/content/legal/`, the email templates
(`backend/templates/correos/`),
`backend/chatbot/prompts.py` and `docs/`. A test (`i18n` check or a small
Vitest) fails on «TMDb», «Tmdb», «themoviedb» as a visible word. Links to the
site use `https://www.themoviedb.org`; deep links that TMDB itself returns
(the watch providers `link`) are left as TMDB sends them.

## API use

- **Rate.** The client is synchronous: one process sends one request at a
  time, so its rate is bounded by TMDB's latency. The expected peak is the
  worker with `--concurrency=2` plus a seed run by hand, a few processes in
  parallel; it has never been measured. Task 4.1 measures
  it with the existing call counter (`registrar_llamada`) over a seed of 200
  titles and records the number in doc 06. A shared limiter is **not** added
  unless the measurement says otherwise.
- **429 (Too Many Requests).** Already retried with backoff and `Retry-After`
  (`client.py`). A test pins that the refresh task goes through the same
  client (it does, via `materializar()`), so no new path skips it.
- **Images.** The frontend only builds `image.tmdb.org` URLs from catalog
  paths (`lib/catalog.ts`); the static collage is not hot-linked. Task 4.3
  greps for any other `image.tmdb.org` use outside catalog rendering.

## AI use

Nothing changes in code. The 07/11/2026 decision goes into
`docs/decisiones.md` with: the clause it answers (ML/AI and chatbots), why it
is accepted (academic, non-profit, no revenue from TMDB content), the trigger
to revisit (any ad, subscription or paid tier), and the exceptions of this
change (collage until 13/02/2027, test fixtures). `PRODUCT.md` gets one line
under its constraints so a future monetization plan meets it.

## Architecture Decisions

| Decision                                         | Alternative rejected                                  | Why                                                                                                               |
| ------------------------------------------------ | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Credits as a block in `/terms` with an anchor    | A new `/about` page                                   | Decided 07/11/2026. TMDB asks for an «About» or «Credits» _section_; `/terms` already lists TMDB as a third party |
| Reference date = `fecha_enriquecimiento`         | A new `fecha_sincronizacion` column                   | It already records the last TMDB fetch, in the same `save()` as the data; NULL rows are handled by being due      |
| Refresh at 150 days, cap 300 per night           | Refresh at 180; no cap                                | A margin for failed nights; a cap so the worker keeps serving `materializar_produccion` for users                 |
| Refresh, never delete referenced rows            | Delete rows older than 6 months                       | CASCADE would take users' ratings, reviews and lists                                                              |
| Trim cards to ids at 180 days, rehydrate on read | Keep them (accepted risk); store ids only from now on | Decided 07/11/2026. Live conversations keep the 09/10 behavior; old ones stay correct without TMDB calls          |
| Logo as `<img>` from `public/`                   | Inline SVG component                                  | An inline SVG invites `currentColor`/theme tweaks; the terms forbid recoloring                                    |
| No shared rate limiter                           | A Redis token bucket                                  | The client is sequential; measure first                                                                           |
