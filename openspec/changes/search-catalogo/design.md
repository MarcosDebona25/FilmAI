# Design: Buscar (C-06)

## 1. Who talks to whom

```
Browser (/search, "use client")
   │ HTTP GET + Accept-Language (no session needed)
   ▼
Django · BrowseView  (catalogo/views.py, throttle «catalogo» 60/min)
   │ validates q / tipo / genero / anio / nota / page
   ▼
catalogo/services/browse.py · explorar()
   │ decides the mode, fans out, filters, alternates
   ▼
TMDBClientCache ──Redis (DB 0, search 1 h, discover 6 h)──▶ TMDB
   discover/movie · discover/tv · search/movie · search/tv · genre/*/list
```

Nothing is written to Postgres. Each TMDB page is cached on its own, so the
window of 5 pages is 5 cache entries: a second search with the same text but a
different genre costs no TMDB call.

## 2. Contract

`GET /api/catalogo/browse/`

| Param    | Values                                                      | Default |
| -------- | ----------------------------------------------------------- | ------- |
| `q`      | any text, trimmed; empty = no text; > 50 → 400 `max_length` | —       |
| `tipo`   | `all`, `movie`, `tv`                                        | `all`   |
| `genero` | TMDB genre id                                               | —       |
| `anio`   | year                                                        | —       |
| `nota`   | `9+`, `8+`, `7+`, `6+`, `5+`, `m5` (below 5)                | —       |
| `page`   | 1–500                                                       | 1       |

Response, the same shape as TMDB's listings so the frontend reuses
`normalizeTitles`:

```json
{ "page": 1, "total_pages": 3, "total_results": 57,
  "results": [ { "id": 438631, "media_type": "movie", "title": "Dune", ... } ] }
```

Every item carries `media_type`, also for a single type. `campos_en_ingles`
comes from the language fallback as in every listing.

## 3. Modes

| Text | Genre or rating | Per type                                                         | TMDB calls per type |
| ---- | --------------- | ---------------------------------------------------------------- | ------------------- |
| no   | any             | `discover(tipo, genero, anio, nota, page, sort=popularity.desc)` | 1                   |
| yes  | no              | `search(q, tipo, page, year)`                                    | 1                   |
| yes  | yes             | window: `search` pages 1–5, then filter genre and rating here    | 1–5                 |

«All» runs the chosen mode for movies and for shows and alternates both lists
(movie, show, movie…; the longer one's rest at the end), like the Home's
«New releases». `total_results` is the sum; `total_pages` the larger of the
two, capped at 500 (TMDB refuses higher pages).

### Window (text with genre or rating)

1. Ask page 1 of each type (in parallel for «All»).
2. With `total_pages` known, ask pages 2 to `min(total_pages, 5)` in parallel
   (`ThreadPoolExecutor`; `httpx.Client` is thread-safe, verified in 0.28.1;
   the Redis client too).
3. Keep the items that match genre and rating, in TMDB's order.
4. Page N is items `20·(N−1)` to `20·N` of each type; totals are the filtered
   counts.

### Genre in «All»

Verified lists (14/10/2026): 8 common ids (Animation, Comedy, Crime,
Documentary, Drama, Family, Mystery, Western).

| Movie genre                     | Show genre               |
| ------------------------------- | ------------------------ |
| 28 Action, 12 Adventure         | 10759 Action & Adventure |
| 878 Science Fiction, 14 Fantasy | 10765 Sci-Fi & Fantasy   |
| 10752 War                       | 10768 War & Politics     |

A movie genre with no show counterpart (Horror, History, Thriller, Music,
Romance, TV Movie) leaves the show side empty, and a show-only genre (Kids,
News, Reality, Soap, Talk) leaves the movie side empty: TMDB has no such
category on the other side. `genres/?tipo=all` lists the movie genres plus
those five show-only ones.

### Rating

| `nota` | discover                | window filter       |
| ------ | ----------------------- | ------------------- |
| `N+`   | `vote_average.gte=N`    | `vote_average >= N` |
| `m5`   | `vote_average.lte=4.99` | `vote_average < 5`  |

Always with `vote_count >= 50`: without it «Below 5» is full of titles with
no votes (verified). 50 is the threshold the Home uses for shows.

## 4. Client and cache changes

- `TMDBClient.search(query, tipo, page, anio=None)`: sends
  `primary_release_year` or `first_air_date_year`.
- `TMDBClient.discover(..., max_rating=None)`: `vote_average.lte`.
- Both enter the cache key only when used, so existing keys stay valid (same
  pattern as `min_votos`, C-05).

## 5. Frontend

```
app/search/page.tsx ── Suspense ──▶ SearchView ("use client")
   ├── URL ⇄ state: q, type, genre, year, rating, page (history.replaceState)
   ├── useCatalog(`/api/catalogo/browse/?…`)   cached per URL
   ├── useCatalog(`/api/catalogo/genres/?tipo=…`)
   ├── desktop: SearchField · TypeSelector · 3 selects · count · grid · pager
   └── mobile: heading · SearchField · TypeSelector + Filters (badge)
                 └── FiltersSheet (DialogShell): Genre · Year · rating · Clear · Show results
```

- **Typing** waits 350 ms; filters apply at once. Any change resets the page
  to 1. `replaceState` like the Home: no server round trip, and Back leaves
  Search.
- **Close / Escape** goes back when the user came from inside the app, else to
  Home. The field takes focus on desktop only (on mobile the keyboard would
  hide the results).
- **MediaCard** gains a fluid width for the grid and «No ratings» when TMDB has
  none (canvas).
- **Breadcrumb return**: the last search URL is kept in `sessionStorage`; the
  title page's «Search» crumb links to it. Read and write in try/catch; without
  it, plain `/search`.
- **Year select**: Any, then the current year down to 1900.
