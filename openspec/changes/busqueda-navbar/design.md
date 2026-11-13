# Design: Search in the navbar, a person filter and hiding irrelevant titles

## Where this lives

```
Frontend (Next.js)                                         Backend (Django + DRF)
──────────────────                                         ──────────────────────
Navbar (desktop, ≥ md)                                     catalogo/urls.py
 ├─ Home · Lists                (left; «Search» leaves)     ├─ suggest/   SuggestView        (new)
 └─ <NavbarSearch/>             (right, before account)     │     └─ services/sugerencias.py ─▶ TMDB search/multi
      ├─ GET suggest/?q=        (debounce 250 ms, ≥ 2)      └─ browse/    BrowseView         (+ persona, rol)
      ├─ title  ─▶ /movie/{id} · /tv/{id}                         └─ services/browse.py
      ├─ person ─▶ /search?person={id}&role=…                          ├─ text:   search/{movie,tv} ×5 pages (exists)
      └─ Enter / «See all results» ─▶ /search?q=…                     ├─ person: person/{id}/combined_credits (cached 24 h)
                                                                       │          + person/{id} (name, cached 24 h)
MobileTabs (mobile)             unchanged                              └─ es_relevante(): the cut, shared with suggest
/search  SearchView
 ├─ filters row / FiltersSheet  + «Person» field
 ├─ active person chip with ✕ above the results
 └─ grid: relevant titles only (infinite scroll, unchanged)
title page «Director and cast»  names link to /search?person=… (proposal, last PR)
```

New code: `catalogo/services/sugerencias.py`, `SuggestView`, the person branch
and the cut in `services/browse.py`, `components/NavbarSearch.tsx`, a
`PersonFilter` field shared by the filters row and the sheet, and the person
chip in `SearchView`. The cut needs no frontend change. The combobox reuses the pattern of
`components/CountrySelect.tsx` (already ARIA 1.2 with `aria-activedescendant`).

## Measurements (13/11/2026)

Measured from the backend container against TMDB, Spanish (`es-MX`), with the
Redis cache bypassed for the cold numbers. Three runs each, median / max.

| Call                                                           | Cold (ms)      | Notes                                                     |
| -------------------------------------------------------------- | -------------- | --------------------------------------------------------- |
| `search/multi` «nolan», «chihiro», «dune», «the office», «bat» | 185–354 / 613  | 20 results per page mixing movies, shows and people       |
| `search/movie` «dune»                                          | 178 / 192      | One page of the current Search                            |
| `search/person` «christopher nolan»                            | 181 / 189      |                                                           |
| `person/525/combined_credits` (Nolan)                          | 208 / 216      | 51 cast, 80 crew, 19 «Director»                           |
| `person/31/combined_credits` (Tom Hanks)                       | 377            | 281 cast, 88 crew, 245 kB of JSON                         |
| Any cached call (Redis, service level)                         | 0.3–1.7        |                                                           |
| `browse/?q=nolan` end to end, cold → warm                      | 226–562 → 9–12 | The current text search (up to 10 TMDB calls in parallel) |

What the data showed:

- **`search/multi` ranks well for names**: «nolan» puts Christopher Nolan
  first; «tom» brings Tom Holland, Tom Hanks and Tom Cruise among the first 10.
  People carry `known_for_department` (`Acting`, `Directing`, `Writing`…),
  `gender`, `popularity` and `profile_path`.
- **The cut** (5 votes or popularity 5) over the first 100 per type:

  | Text          | Total | Relevant | Hidden | Kept only by popularity       |
  | ------------- | ----: | -------: | -----: | ----------------------------- |
  | chihiro       |    13 |        3 |     10 | —                             |
  | spirited away |     9 |        5 |      4 | —                             |
  | dune          |   195 |       97 |     98 | Dune: Part Three (0 votes)    |
  | batman        |   123 |       83 |     40 | The Batman: Part II (0 votes) |
  | the office    |   158 |       35 |    123 | 2                             |
  | love          |   200 |      174 |     26 | 23                            |
  | nolan         |    37 |       13 |     24 | —                             |
  | oppenheimer   |    32 |       11 |     21 | —                             |

  The hidden ones in «chihiro» are «La arquitectura de El Viaje de Chihiro» (1
  vote, popularity 0.2), «Sato no Chihiro» (1 vote) and concert videos with 0
  votes. Popularity rescues the announced sequels, as intended.

- **Shows in `combined_credits`**: Vince Gilligan has `Creator` for Breaking
  Bad and Better Call Saul, and `Director` for 2 to 9 episodes of several
  shows; Phoebe Waller-Bridge has `Creator` for Fleabag. `Creator` exists and
  matches what the title page shows («Created by»).

## 1. Suggestions endpoint

**`GET /api/catalogo/suggest/?q=<text>`**, public, in `CatalogoBaseView`
(no authentication, gzip, `Cache-Control: public, max-age=300`, `Vary:
Accept-Language`, TMDB call caps).

- `q`: trimmed, 2 to 50 characters. Shorter → 400 (Bad Request) `min_length`;
  longer → 400 `max_length` (same limit and error shape as `browse/`).
- `tipo`: `all` (default) or `person` (only people, for the «Person» field of
  the filters).

Answer:

```json
{
  "results": [
    {
      "media_type": "person",
      "id": 525,
      "name": "Christopher Nolan",
      "rol": "director",
      "gender": 2,
      "profile_path": "/x.jpg"
    },
    {
      "media_type": "movie",
      "id": 27205,
      "title": "El origen",
      "release_date": "2010-07-15",
      "poster_path": "/y.jpg",
      "vote_average": 8.4
    }
  ]
}
```

Titles keep TMDB's field names so the frontend normalizes them with
`normalizeTitles` like any listing; people get `rol` (`director` or `actor`)
instead of `known_for_department`.

**Why not `browse/` with a parameter.** A text search in `browse/` makes 10
TMDB calls (20 in Spanish when titles need the English fill) and never returns
people. Suggestions need one call and must return people. `search/multi` was
discarded for the grid on 14/10/2026 precisely because it mixes people; here
that is what we want.

**Algorithm** (`catalogo/services/sugerencias.py`):

1. One call: `search/multi?query=q&page=1&include_adult=false`, through the
   cache (new endpoint key `search_multi`, TTL 1 h like `search`; backup copy
   as every endpoint).
2. Keep, in TMDB's order:
   - movies and shows that pass `es_relevante()` (§4); if none of the 20
     passes, the titles as they come (same rule as the grid);
   - people with `known_for_department` in `Acting` or `Directing` and
     `popularity ≥ 1` (drops «Nolan Yee», 0.1, and «Chihiro Yoshioka», 0.4;
     keeps Nolan North, 2.2). At most 2.
3. Cut to 5 in total. With `tipo=person`, only people, up to 5.

**Mixing titles and people.** TMDB's relevance order, not the grid's score.
In the measured queries it already does the right thing: a person query puts
the person first («nolan»), a title query puts titles first («dune»), and the
cut removes the zero-vote titles that made TMDB's order bad for the grid on
14/10/2026. No groups or headers in the list: each option says what it is
(«Movie · 2024», «Director»).

**Language.** The Spanish service fills empty `title`/`name` from English
(`CatalogoConRespaldo`). For suggestions only the title or name matters, not
the synopsis, so the fill checks those two fields on the kept items only: in
practice it costs 0 extra calls (TMDB already falls back to the original
title).

**No materialization.** `browse/` and the listings enqueue the materialization
of every result. Suggestions do not: each keystroke would enqueue up to 5
tasks for titles nobody opened. The title page materializes on open.

**Throttle.** A new scope `sugerencias`, 120/min per IP, separate from
`catalogo` (60/min), so typing does not eat the budget of the page the user is
about to open. The per-IP TMDB limit (300 calls/min) and the per-request cap
(30) stay; a suggestion costs 1 call (2 at most).

### Cost per typed search

| Situation                                       | Requests to the backend |                           TMDB calls |
| ----------------------------------------------- | ----------------------: | -----------------------------------: |
| «christopher nolan» typed at a normal pace      |          2–4 (debounce) |                   2–4 cold, 0 cached |
| The same text again (any user, within 1 h)      |                     0–1 |                                    0 |
| Backspace to a text already seen in the session |       0 (session cache) |                                    0 |
| Enter → `/search?q=…` (unchanged grid)          |              1 per page | up to 10 (20 in Spanish), first page |

Latency: cold, debounce (250 ms) plus one `search/multi` (185–354 ms median)
≈ 450–600 ms from the last keystroke; cached, ≈ 260 ms, almost all of it the
debounce.

## 2. The field in the navbar

### Layout

- **≥ 1024 px (`lg`)**: a field of 18–20 rem on the right of the bar, before
  the account (or «Log in · Sign up»), with a magnifier, the placeholder
  «Search titles and people» and a `kbd` «/» hint. The left keeps «Home» and
  «Lists».
- **768–1023 px (`md` to `lg`)**, plan B, only if the canvas shows that the
  field does not fit: a magnifier button in the same place; pressing it
  expands the field in place, over the left links, with focus in it; Escape
  or leaving it empty and blurring collapses it.
- **< 768 px**: no field. `MobileTabs` keeps its «Search» tab.
- **On `/search`**: the field is not rendered (Q-4). The page has its own big
  field with focus on desktop; two fields with the same text would fight for
  Escape (the page closes Search with it) and for `/`.

The navbar variant is still being chosen by Gonza with an artifact
(13/11/2026); this design starts from the field with suggestions, his choice
so far, and keeps the expanding magnifier as plan B. The exact sizes, the
dropdown's look (poster thumbnails, round photos for
people, the «See all results» row) and the plan B are designed in the canvas
first (task 3.0, Gonza).

### Behavior

- Suggestions are asked 250 ms after the last keystroke, from 2 characters
  (trimmed). The page's field waits 350 ms because each request is a full
  search; here a request is one cached call and the list must feel live.
- A new request aborts the previous one (`AbortController`; `apiFetch`
  already takes a `signal`), and an answer is shown only if its text is still
  the field's text.
- Answers are kept in a module `Map` per language and text, like
  `useCatalog`'s cache: going back to a text shows its list at once.
- While a new list loads, the previous one stays (no flicker), with
  `aria-busy`.
- **Enter** with no active option, or the «See all results for “text”» row
  (always last), navigates to `/search?q=text`, without the previous Search
  filters (a fresh search).
- A **title** navigates to `/movie/{id}` or `/tv/{id}` without `from` (the
  crumb goes to Home, as for any title opened outside Search).
- A **person** navigates to `/search?person={id}&role={director|actor}`.
- After navigating, the field is cleared and the list closes.
- Errors (429, 503) close the list silently; Enter still goes to Search, which
  shows its own error.

### `/` shortcut (Q-6)

On desktop, `/` focuses the navbar field when the focus is not in an
editable element (`input`, `textarea`, `select`, `[contenteditable]`) and no
`dialog[open]` exists. On `/search` it focuses the page's field. The handler
lives in `NavbarSearch` (one listener). The field shows the hint «/» while it
is empty and unfocused.

## 3. Accessibility: ARIA 1.2 combobox

The same pattern as `CountrySelect.tsx`, with an editable input (APG «List
autocomplete with manual selection»):

- The `<input>` has `role="combobox"`, `aria-autocomplete="list"`,
  `aria-expanded`, `aria-controls` pointing to the `role="listbox"` and,
  while an option is active, `aria-activedescendant` with its id. The field
  is wrapped in `<search>` with its label («Search FilmAI») and a visible or
  `sr-only` `<label>`.
- Each option has `role="option"`, a stable id (`sug-movie-27205`,
  `sug-person-525`, `sug-all`) and `aria-selected="true"` when active. Its
  accessible name reads the whole row: «El origen, Movie, 2010», «Christopher
  Nolan, Director», «See all results for “nolan”». Images have `alt=""`.
- Keyboard: ↓ / ↑ move the active option (from the field ↓ goes to the first;
  past the last it returns to the field, no active option); Enter follows the
  active option or, with none, goes to Search; Escape closes the list, and a
  second Escape clears the field; Tab closes the list without choosing;
  Alt+↓ opens the list with the last answer. Typing never moves the active
  option (manual selection: nothing is chosen for the user).
- Mouse: hovering does not change `aria-activedescendant`; a click follows
  the option (`onMouseDown` with `preventDefault` so the field keeps focus).
- **Announcements**: a polite live region, always in the DOM, says «5
  suggestions» / «No suggestions for “text”» when a list arrives, at most
  once per answer; `aria-activedescendant` changes are read by the screen
  reader itself.
- Focus ring and target sizes as the rest of the navbar (44 px rows).
- The list closes on blur, on route change and on Escape; the bar's
  `z-index` keeps it above the Home hero and the title page backdrop.

## 4. Relevance cut

**Rule** (`catalogo/services/browse.py`):

```python
MIN_VOTOS_RELEVANTE = 5
MIN_POPULARIDAD_RELEVANTE = 5

def es_relevante(item, q=None):
    if (item.get("vote_count") or 0) >= MIN_VOTOS_RELEVANTE:
        return True
    if (item.get("popularity") or 0) >= MIN_POPULARIDAD_RELEVANTE:
        return True
    # Exception (a): the exact title. Someone who types the whole name wants it.
    return q is not None and normalizar(q) in {
        normalizar(item.get(campo) or "")
        for campo in ("title", "name", "original_title", "original_name")
    }
```

`normalizar()` lowercases, strips accents (NFKD without combining marks) and
collapses spaces, so «Chihiro», «chihiro » and «CHIHIRÓ» are the same text.
`video`, the synopsis and `adult` are not signals (Gonza, 13/11/2026).

**Exception (b)**: if no item of the window passes, every item is shown, as
today.

**What happens to the rest: nothing is shown.** There is no «See N more
results» button (Gonza, 13/11/2026). The first idea was to keep the hidden
titles one click away; it was discarded because people press the button and
end up paying attention precisely to what is irrelevant. A title that does
not pass and is not named exactly as the text simply is not in the results.

**Where it applies**: in `browse/` when there is text or a person, after the
filters and before paginating; and in suggestions (§1). Not without text and
person: `discover` already asks 50 votes (and «Upcoming» without votes is the
point of that option). With a rating filter it never removes anything (the
filter already asks 50 votes).

**Contract.** The answer keeps its shape: `total_results` and `total_pages`
count only what is shown, so the count «N results for “text”» and the
infinite scroll work unchanged (the window is the same 100 per type, read
from Redis; no extra TMDB call). No new parameter, no new field, no frontend
change. With the measurements above, «chihiro» shows 3 titles instead of 13
and «the office» 35 instead of 158.

**Risk accepted**: an obscure title that has fewer than 5 votes, popularity
under 5 and a name different from the text (a typo, a partial name) cannot be
reached from Search while better-known titles match. It is still reachable by
its exact name.

## 5. Person filter

### API

`browse/` takes `persona` (TMDB person id, positive integer) and `rol`
(`director`, `actor`; absent = any). Invalid values → 400 (`invalid`,
`invalid_choice`). A person TMDB does not know → 404 (Not Found) with
`person_not_found`. The answer adds:

```json
"persona": {"id": 525, "name": "Christopher Nolan", "rol": "director", "profile_path": "/x.jpg"}
```

so the chip has its name after a reload or from a shared URL. The name comes
from `person/{id}` (new cached endpoint `person_detail`, 24 h), not from the
URL: a URL cannot make the chip say something else.

### Credits

1. `person/{id}/combined_credits` (exists: `get_person_credits`, cached 24 h).
2. By role:
   - `actor`: `cast`, except shows in News or Talk (`genre_ids` with 10763 or
     10767): otherwise Tom Hanks' list fills with talk-show appearances, the
     same reason the grid excludes them.
   - `director`: in movies, `crew` with `job == "Director"`; in shows,
     `crew` with `job == "Creator"` (Q-1). Episode directors do not count:
     Gilligan directed 2 episodes of «The X-Files», which would show up as
     «directed by Vince Gilligan».
   - any: both.
3. Without duplicates by `(media_type, id)` (a person can have several jobs
   in one title).
4. The rest of the filters, in memory, with the existing `_pasa()`: type,
   genre (mapped per type as in «All»), year (`anio`, `a_estrenar`, `decada`
   by date) and rating (with 50 votes). Text, if any, keeps the titles whose
   `title`, `name`, `original_title` or `original_name` contain it, compared
   without case or accents. No call to `search/*`.
5. The cut (§4), the score order (Q-5) and the pagination of the text search
   (20 per type, 40 in «All», alternating nothing: one sorted list).

Cost: 2 TMDB calls the first time (`combined_credits` and `person/{id}`), 0
afterwards for 24 h, for every page and every filter combination. Cheaper
than a text search.

### URL and UI

- URL: `person={id}` and `role={director|actor}` (absent = any), next to `q`,
  `type`, `genre`, `year`, `rating`, `page`. A person counts as one
  active filter («Filters, 3 active»). «Clear filters» removes it.
- **Chip** above the results (between the filters and the count), on desktop
  and mobile: round photo, «Christopher Nolan · Director» and a ✕ button
  (`aria-label` «Remove filter Christopher Nolan») that removes `person` and
  `role`. SearchView does not show active filters as chips today (genre, year
  and rating stay visible in their selects), so this is a new element: its
  look is designed in the canvas. To change the role, the user picks the
  person again in the «Person» field, which suggests the role TMDB knows them
  for (Q-2).
- **«Person» field** in the filters row and in the sheet: the same combobox
  with `suggest/?tipo=person`. Choosing someone sets `person` and the role of
  the suggestion.
- **Count and empty state**: «N results for “Christopher Nolan”» when there
  is no text; «Nothing with these filters» + «Clear filters» when the
  combination leaves nothing (Nolan + «TV shows»).
- `type` changes keep the person (the filmography has both types).

## 6. Links from the title page (proposal, Q-7)

`GET /api/catalogo/{tipo}/{id}/credits/` returns names only today. It would
add `id` to each director and cast member (TMDB's credits already have it;
backward compatible). On the title page, each name becomes a link to
`/search?person={id}&role=director` (directors and creators) or
`role=actor` (cast), with the person's name as text and no extra decoration
beyond the link style of the canvas. Last PR, optional.

## 7. Texts (en / es)

New keys, to approve with the canvas (copy lives in `traducciones/claves.csv`):

| Key                             | English                                                                                      | Spanish                                                                                                                                                                    |
| ------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `nav.search.placeholder`        | Search titles and people                                                                     | Buscar títulos y personas                                                                                                                                                  |
| `nav.search.label`              | Search FilmAI                                                                                | Buscar en FilmAI                                                                                                                                                           |
| `nav.search.seeAll`             | See all results for “{query}”                                                                | Ver todos los resultados de «{query}»                                                                                                                                      |
| `nav.search.count`              | {count, plural, =0 {No suggestions} one {# suggestion} other {# suggestions}}                | {count, plural, =0 {Sin sugerencias} one {# sugerencia} other {# sugerencias}}                                                                                             |
| `nav.search.openLabel` (plan B) | Open search                                                                                  | Abrir la búsqueda                                                                                                                                                          |
| `search.person.role`            | {role, select, director {Director} other {{gender, select, female {Actress} other {Actor}}}} | {role, select, director {{gender, select, female {Directora} male {Director} other {Dirección}}} other {{gender, select, female {Actriz} male {Actor} other {Actuación}}}} |
| `search.person.label`           | Person                                                                                       | Persona                                                                                                                                                                    |
| `search.person.remove`          | Remove filter {name}                                                                         | Quitar el filtro {name}                                                                                                                                                    |
| error `person_not_found`        | We couldn't find that person                                                                 | No encontramos a esa persona                                                                                                                                               |

`gender` maps from TMDB: 1 → `female`, 2 → `male`, anything else → `other`.

## 8. Tests

- **Backend**: `es_relevante` at the edges (4/5 votes, 4.9/5 popularity) and
  the exact title (translated or original, without accents or case);
  `browse/` with text leaves out the irrelevant titles, counts and paginates
  only what it shows, and returns everything when nothing passes; `suggest/`
  makes one call, caps people at 2 and the total at 5, drops low popularity
  and other departments, validates 2–50 characters, does not enqueue
  materialization and uses its scope; the person branch: `Creator` counts in
  shows and episode `Director` does not, News/Talk dropped from cast, the
  filters and the text in memory, deduplication, 404 for an unknown person,
  `persona` in the answer, and 2 calls cold / 0 cached. Fixtures from real
  answers (`test_datos/`), no network.
- **Frontend (Vitest)**: the combobox keyboard (↓ ↑ Enter Escape Tab Alt+↓),
  `aria-activedescendant`, the live region, stale answers dropped, the `/`
  shortcut with and without focus in a field; the URL with `person` and
  `role`, and the chip's ✕.
- **e2e (Playwright, API simulated)**: type in the navbar → suggestions →
  person → Search with the chip, ✕ removes it; Enter → `/search?q=`; the field is absent on
  `/search` and on mobile. axe on the open dropdown.
