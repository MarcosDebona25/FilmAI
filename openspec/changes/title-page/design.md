# Design: Ficha de detalle (C-07)

## 1. Who talks to whom

```
Browser (/movie/[id], /tv/[id], "use client")
   │ HTTP + cookie JWT (if any) + Accept-Language
   ▼
Django
   ├── catalogo/{tipo}/{id}/          detail (public, already exists; materializes)
   ├── catalogo/{tipo}/{id}/credits/  NEW, public ──▶ TMDBClientCache.get_credits ──Redis──▶ TMDB
   ├── reviews/?id_tmdb=&tipo=        community, NOW public, with orden/nota_min/nota_max
   ├── reviews/mias/?id_tmdb=&tipo=   my rating for this title (session)       ──SQL──▶ Postgres
   ├── reviews/ · reviews/{id}/ · reviews/{id}/texto/   write (session, C-08)
   └── lists/?id_tmdb=&tipo=          membership with item_id (session, L-01)
       lists/{id}/items/ · lists/{id}/items/{item_id}/[?borrar_calificacion=true]
```

| Block                          | Request                                 | Session |
| ------------------------------ | --------------------------------------- | ------- |
| Hero, meta, genres, synopsis   | `catalogo/{tipo}/{id}/`                 | no      |
| Director and cast              | `catalogo/{tipo}/{id}/credits/`         | no      |
| Actions (rate, toggles, lists) | `reviews/mias/?…` + `lists/?…`          | yes     |
| Your review                    | `reviews/mias/?…` (same request)        | yes     |
| Community                      | `reviews/?…&orden=&nota_min=&nota_max=` | no      |
| Breadcrumb `list-{id}`         | `lists/{id}/` (name)                    | yes     |

## 2. Backend

### 2.1 `GET /api/catalogo/{movie|tv}/{id}/credits/`

Public, `catalogo` throttle, through the cached service (`get_credits` is
already cached). Response:

```json
{
  "directores": ["Christopher Nolan"],
  "reparto": [{ "nombre": "Matthew McConaughey", "personaje": "Cooper" }]
}
```

- **Movies**: `directores` are the crew members with `job == "Director"`.
- **Shows**: `directores` are the detail's `created_by` (the frontend labels them
  «Created by»). Checked on 13/10/2026: Breaking Bad has no crew member with
  `job == "Director"` at series level, as C-04a found; `created_by` has Vince
  Gilligan. Materialization already makes the same choice.
- `reparto` keeps TMDB's order, at most 50 (Interstellar has 36). Characters come
  as TMDB has them; credits are not localized.
- Invalid id: 400 (Bad Request) like the detail. Unknown title: the same error
  the detail answers.

### 2.2 Community reviews

- `GET` becomes `AllowAny`; `POST` keeps `IsAuthenticated` (permission per
  method). Without a session nothing is excluded; with one, the user's own
  review is still excluded (it has its own card).
- `orden`: `fecha-desc` (default), `fecha-asc`, `nota-desc`, `nota-asc`. Anything
  else: 400 (Bad Request) with `invalid_choice`.
- `nota_min` / `nota_max`: integers 1-10, inclusive. The canvas options map to
  them: «9 or higher» → `nota_min=9`; «Below 5» → `nota_max=4`.
- **Cursor with any order**: DRF's `CursorPagination` positions the cursor on
  the first ordering field and breaks ties with an offset, which degrades when a
  field repeats a lot (thousands of 8s). Rating orders use an annotated unique
  key, `valor * 10^9 + id`, so the cursor always points at one review. Date
  orders keep `(-fecha, -id)` as today.
- **Totals**: `total` keeps counting what the filters return; a new
  `total_comunidad` counts all the community reviews of the title, for «Showing
  {shown} of {total}» and «From the community ({count})».

## 3. Frontend

### 3.1 Pieces

| Piece                                             | Where                                                                     |
| ------------------------------------------------- | ------------------------------------------------------------------------- |
| `app/movie/[id]/page.tsx`, `app/tv/[id]/page.tsx` | thin pages, both render `TitleView`                                       |
| `TitleView`                                       | `components/features/title/TitleView.tsx`: loads and composes             |
| `TitleHero`                                       | backdrop band, poster, breadcrumb, title, tagline, meta, genres           |
| `TitleActions`                                    | Rate/★ N, Favorite, Watched, Watchlist, Add to list                       |
| `ListsMenu`                                       | popover (desktop) / sheet (mobile) with checklist and inline creation     |
| `RatingDialog`                                    | rate / edit modal; sheet on mobile                                        |
| `StarRating`                                      | radiogroup 1-10, two rows of five on mobile (44 px targets)               |
| `ConfirmDialog`                                   | `alertdialog` for delete text, remove rating, remove from Watched         |
| `CreditsSection`                                  | directors or creators + cast, «Show more» over 10                         |
| `ReviewsSection`                                  | your review + community with sort, filter, «Load more»                    |
| `lib/title.ts`                                    | detail normalization (runtime, seasons, genres), breadcrumb from `?from=` |

`MediaCard` gets an optional `from` that it appends to `routes.title`.

### 3.2 State and flows

The page keeps three server states: the detail (+ credits), **my rating**
(`reviews/mias/?…`: `{id, valor, texto, fecha}` or 404 (Not Found)) and
**membership** (`lists/?…`: each list with `contiene` and `item_id`). Every
mutation updates them from the server's answer, not by guessing.

```
Rate ──POST reviews/──▶ 201 ──▶ my rating = answer; Watched = on (server rule)
Edit ──PUT reviews/{id}/──▶ 200 ──▶ my rating = answer
Delete review ──confirm──▶ DELETE reviews/{id}/texto/ ──▶ texto = null; rating stays
Remove rating ──confirm──▶ DELETE reviews/{id}/ ──▶ my rating = none; Watched = off
Watched off ──DELETE lists/{vistas}/items/{item}──▶ 409 rating_blocks_removal_from_watched
            └─▶ confirm (shows rating and review preview)
                └─▶ DELETE …?borrar_calificacion=true ──▶ my rating = none; Watched = off
Favorite/Watchlist/custom list ──POST or DELETE items──▶ membership refreshed
New list ──POST lists/──▶ POST items ──▶ toast «You created … and added …»
```

After any change to my rating the community block does not reload: the user's
own review is never in it.

### 3.3 Breadcrumb

`?from=home` → Home › {title}; `search` → Search › {title}; `reviews` → Profile ›
Ratings & reviews › {title}; `list-{id}` → Lists › {list name} › {title} (name
from `lists/{id}/`; if it fails, «Lists» alone). No or unknown value → Home ›
{title}. The current page is the last item with `aria-current="page"`.

### 3.4 Signed out

Hero, synopsis, credits and community reviews show. The actions are replaced by
«Log in to rate or save» linking to `/login?next=/movie/{id}`, so the user comes
back to the same page.

### 3.5 Copy

Almost all copy is seeded (`title.*`, `common.rating.*`, `common.media.*`,
`common.sort.*`, `common.filters.*`). New keys proposed for PR 3-5, added to
`docs/i18n/copia-propuesta.csv`: «Created by», «Load more reviews», «Log in to
rate or save» and the empty state «No reviews yet. Be the first to rate it.».
Ratings show as «★ 8,5» (decision of 03/10/2026), never «X/10».

## 4. Decisions validated by the user (14/10/2026)

| #   | Decision                                                                | Discarded                                    |
| --- | ----------------------------------------------------------------------- | -------------------------------------------- |
| 1   | Gonza builds the list actions (L-04) inside C-07                        | Leaving a slot for Marcos                    |
| 2   | Community reviews are public (GET without a session)                    | Session only                                 |
| 3   | Sort and rating filter on community reviews, as in the canvas           | Sort only; none                              |
| 4   | The origin travels in the URL: `?from=home\|search\|reviews\|list-{id}` | `sessionStorage` (lost on reload or new tab) |
