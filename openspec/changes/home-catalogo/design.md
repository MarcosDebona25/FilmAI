# Design: Home de descubrimiento (C-05)

## 1. Who talks to whom

```
Browser (/home, "use client")
   │
   │ HTTP + cookie JWT + Accept-Language          (apiFetch, one request per row)
   ▼
Django (catalogo/views.py)
   ├── trending · now-playing · discover · genres ──▶ TMDBClientCache ──Redis──▶ hit
   │        (public, no session)                            │ miss
   │                                                        └──HTTPS──▶ TMDB
   └── recommended (session required)
          ├──SQL──▶ Postgres: Calificacion ≥ 7 + Lista «vistas»
          └──────▶ TMDBClientCache.discover(...)  (same cache as above)
```

| Row                | `All`                                                       | `Movies`                    | `TV shows`                                  |
| ------------------ | ----------------------------------------------------------- | --------------------------- | ------------------------------------------- |
| Hero               | `trending?media_type=all`                                   | `trending?media_type=movie` | `trending?media_type=tv`                    |
| Recommended        | `recommended?tipo=all`                                      | `recommended?tipo=movie`    | `recommended?tipo=tv`                       |
| Trending this week | `trending?media_type=all`                                   | `trending?media_type=movie` | `trending?media_type=tv`                    |
| New releases       | `now-playing` + `discover?tipo=tv&anio=<year>&min_votes=50` | `now-playing`               | `discover?tipo=tv&anio=<year>&min_votes=50` |

The Hero and «Trending» share one request per type. The Hero labels its genres
with `genres?tipo=movie|tv`, which the backend already caches per language; the
page asks for each list once and keeps it in memory. Nothing here
calls `materializar()`: a card is not a visit to the title page.

## 2. `GET /api/catalogo/recommended/`

```
Browser          RecommendedView              Postgres                  TMDBClientCache
   │ GET ?tipo=all     │                          │                            │
   │──────────────────▶│ idioma_tmdb(request)     │                            │
   │                   │ for tipo in (movie, tv): │                            │
   │                   │── ratings ≥7 of tipo ───▶│                            │
   │                   │◀─ generos_ids per row ───│                            │
   │                   │ top 3 genre ids          │                            │
   │                   │── discover(tipo, "a|b|c", popularity.desc, ≥100 votes)──▶│
   │                   │◀────────────── page 1 (20 items) ─────────────────────────│
   │                   │── ids in «vistas» ──────▶│                            │
   │                   │ drop seen, keep 15       │                            │
   │                   │ interleave movie/tv      │                            │
   │◀── 200 {generos, results} ──│                │                            │
```

- **Authentication**: DRF's default (`JWTCookieAuthentication` +
  `IsAuthenticated`). Without a session: 401 (Unauthorized) with the error
  envelope. It does not inherit `CatalogoBaseView`, which is public; it keeps
  its `catalogo` throttle (60/min) and its language through
  `servicio_localizado(idioma_tmdb(request), ...)`, so items carry
  `campos_en_ingles` like every other catalog list.
- **`tipo`**: `all` (default), `movie` or `tv`. Anything else: 400 (Bad Request)
  with `validation_error` and, in field `tipo`, `invalid_choice` with
  `allowedValues: ["all", "movie", "tv"]`, the same shape `discover` already
  answers.
- **Genres of one type**: active ratings (`activa=True`) with `valor >= 7` whose
  production has that `tipo`, newest first (the model's ordering,
  `-fecha, -id`). Count every id in `generos_ids`; keep the 3 most frequent. Ties
  go to the genre seen first, i.e. the one in the most recent rating
  (`Counter.most_common` keeps insertion order on ties).
- **Why OR**: TMDB joins `with_genres` with `|` as OR and `,` as AND. Checked on
  13/10/2026 with Thriller, Drama and Crime in movies: 14,610 results with OR,
  841 with AND. AND would shrink the row for users with varied taste.
- **Why `vote_count.gte=100`**: on the same day, 9 of 20 movies on the first
  page had fewer than 100 votes (one with 0), and the TV page included an adult
  anime that TMDB does not flag as `adult`. With 100, none of the 20 did, and
  the pool is still 14,610 movies and 2,816 shows.
- **Exclusion**: the `(id_tmdb, tipo)` pairs in the user's «Watched» list
  (`clave=vistas`). With «rated ⇒ watched» (30/09/2026) that also drops
  everything rated. «Watchlist» is not excluded (doc 04 §3.3).
- **Size**: up to 15 per type, from TMDB's first page only. Excluding seen titles
  can leave fewer; we accept that instead of paying a second TMDB page.
- **`all`**: computes both types and alternates movie, tv, movie… (if one runs
  out, the other fills in) up to 15.
- **Response** (200 (OK), also when empty):

```json
{
  "generos": ["Thriller", "Drama", "Crime"],
  "results": [
    {
      "media_type": "movie",
      "id": 1,
      "title": "…",
      "poster_path": "…",
      "backdrop_path": "…",
      "release_date": "2026-01-01",
      "vote_average": 7.5,
      "genre_ids": [53],
      "campos_en_ingles": []
    }
  ]
}
```

Items keep TMDB's shape plus `media_type`, the same shape as `trending/all`,
so `MediaCard` reads one format. `generos` are the names of the genres
actually used, in the request's language, ordered by count and capped at 3 (in
`all`, the union of both types with the counts added up). The frontend joins
them with `Intl.ListFormat` through `lib/format.ts`. A user without ratings of
7 or more gets `{"generos": [], "results": []}`, and the row hides.

## 3. `min_votes` in `discover`

Optional positive integer, read with the existing `_int_param` (so `0`, `-1`
or `abc` answer 400 (Bad Request) with `min_value` or `invalid`, as `genero`
and `anio` do). Sent to TMDB as `vote_count.gte` and part of the cache key. Checked on
13/10/2026: TV shows from 2026 by popularity had 10 of 20 below 50 votes,
including several with 0; with `min_votes=50` none did and 150 remained. 100
would leave 73, too few for a row that changes with the selector. `now-playing`
cannot be filtered (TMDB does not accept it there); 4 of 20 were below 50, and
they are in theaters, so they stay.

## 4. Frontend

### Pieces

| Piece                    | Where                                                                                               | Reused by                                   |
| ------------------------ | --------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| `routes.title(tipo, id)` | `lib/routes.ts`                                                                                     | Every card, C-06, C-07, L-03, chatbot cards |
| `TypeSelector`           | `components/features/TypeSelector.tsx`                                                              | C-06                                        |
| `MediaCard`              | `components/features/MediaCard.tsx`                                                                 | C-06, L-03                                  |
| `MediaRow`               | `components/features/MediaRow.tsx`                                                                  | —                                           |
| `HomeHero`               | `components/features/HomeHero.tsx`                                                                  | —                                           |
| `lib/catalog.ts`         | normalizes a TMDB item into `{tipo, id, titulo, anio, nota, poster, backdrop, generoIds, enIngles}` | C-06, C-07                                  |

### Hero rule (asked for on 03/10/2026)

- `All`: the first item of `trending/all` that has a backdrop. Label
  `home.hero.trendingRank` with its real position (normally «#1 trending»).
- `Movies` / `TV shows`: the first item of that type's trending with a backdrop
  that is not the `All` Hero. Label `home.hero.weeklyHighlight` («Featured this
  week»). So the three selector options show three different Heroes.
- Synopsis clamped to 3 lines; one action, «View details» → `routes.title`.

### Cards and rows

- Meta: «Movie · 2026» in `All`, only the year in `Movies` / `TV shows`.
  Rating: «★ 8.5» with `formatRating` (comma in Spanish), accessible label
  `home.hero.tmdbRatingLabel`. No «X/10» (decision of 03/10/2026).
- Poster `w342`, backdrop `w1280`, through `next/image` with `unoptimized`
  like `ReviewCard`. No poster: the same placeholder block, with the title.
- Fields listed in `campos_en_ingles` get `lang="en"`.
- Desktop: «Previous / Next» buttons scroll one viewport. Mobile: native swipe
  with scroll snap. Keyboard: cards are links in a `role="list"`.
- Loading: 5 skeleton cards per row and a skeleton Hero. `prefers-reduced-motion`
  turns off the hover lift.

### Page states

| State                       | What renders                                                   |
| --------------------------- | -------------------------------------------------------------- |
| Signed out                  | Hero, Trending, New releases, sign-up callout (`home.guest.*`) |
| Signed in, no rating ≥ 7    | Hero, Trending, New releases                                   |
| Signed in, with ratings ≥ 7 | Hero, Recommended, Trending, New releases                      |
| One row fails               | That row hides; one toast for the page                         |
| Everything fails            | Inline error with «Try again» (`common.actions.retry`)         |

## 5. Decisions validated by the user (13/10/2026)

| #   | Decision                                                                                               | Why                                                                         | Discarded                                    |
| --- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- | -------------------------------------------- |
| 1   | «Ask FilmAI» floating button on the Home now, signed in only, linking to `routes.askFilmAI` (`/chat`)  | It is in the artboard; until B-04 it leads to the 404, like the footer link | Waiting for B-04                             |
| 2   | The selector lives in the URL: `/home?type=movie\|tv` (none = `All`)                                   | Coming back from a title page keeps the selection                           | Component state only: back resets to `All`   |
| 3   | Trending and New releases show one TMDB page (20); Recommended up to 15                                | No extra requests; doc 04 asks 10-15 for Recommended                        | Cut every row to 15                          |
| 4   | `All` alternates movie and TV in Recommended and New releases                                          | Both types stay visible near the start of the row                           | Order by popularity, which can bury one type |
| 5   | The navbar is drawn over the Hero on desktop only on `/home`                                           | It is how the artboard draws it                                             | Keep the solid navbar                        |
| 6   | A failed row hides and the page shows one toast; if everything fails, an inline error with «Try again» | Matches doc 04 §5 without a screen full of errors                           | One error block per row                      |

**Revisit after seeing real data (asked by the user):** splitting `All` into
rows of a single type, Netflix-style. It is cheap — `MediaRow` is reused and
`recommended` already computes each type — but it was discarded on 30/09/2026
(six rows plus the Hero, seven requests on load), it would make the selector
almost redundant, and the canvas draws three mixed rows.
