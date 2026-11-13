# Design: Similar titles for lists and title pages (pendiente 5)

## 1. Where this lives

```
Frontend (Next.js)                                      Backend (Django + DRF)
──────────────────                                      ──────────────────────
/lists/[id]  ListDetailView                             listas/views.py
 └─ <ListSuggestions/>  (MediaRow + «+ Add», «Refresh»)    ListaSugerenciasView ── seeds = items of the list
      GET /api/lists/{id}/suggestions/?pagina=N ───────▶      + name vector (optional, Ollama)
      POST /api/lists/{id}/items/ (exists) ─────────────▶                      │
                                                                               ▼
/movie/[id], /tv/[id]  TitleView                         catalogo/services/similares.py  (new, shared)
 └─ <SimilarTitles/>  (MediaRow, loaded near viewport)     vector_semilla() · candidatos() · relleno_tmdb()
      GET /api/catalogo/{tipo}/{id}/similar/ ──────────▶   pool() · pagina()
                                                         catalogo/views.py               │        │
                                                           SimilaresView ── seed = 1 title│        │
                                                                                          ▼        ▼
                                                                         PostgreSQL + pgvector   TMDB /recommendations
                                                                         (produccion_embedding)  (through tmdb-cache, 24 h)
                                                                                          │
                                                                         Redis: pools, name vectors, «Ollama down» flag
```

Both endpoints call the same three steps: **seeds → pool → page**. Only what
goes in (one title or a list plus its name) and what is removed per user
(«Vistas») differ.

## 2. The engine (`catalogo/services/similares.py`)

```python
@dataclass(frozen=True)
class Pool:
    ids_locales: list[int]          # ProduccionAudiovisual.pk, in shuffled order
    tmdb: list[dict]                # TMDB results already shaped as cards
    nombre_usado: bool              # the list name entered the vector
    completo: bool                  # False → short TTL (seed without vector, Ollama skipped)

def vector_semilla(produccion_ids, *, vector_nombre=None, peso_nombre=0.0) -> np.ndarray | None
def candidatos(vector, *, excluir_ids, tipos, limite=100) -> list[tuple[int, float]]
def relleno_tmdb(semillas_tmdb, *, servicio, excluir_pares) -> list[dict]
def armar_pool(...) -> Pool                     # cached by the caller's key
def pagina(pool, *, excluir_pares, numero, tamano=10) -> list[dict]
```

The engine knows nothing about lists, users or HTTP. The views decide the
seeds, the cache key and what to remove per user.

```
Client            View                         similares.py                  Redis      Postgres    Ollama   TMDB
  │ GET …           │                                │                         │           │          │        │
  │────────────────▶│ seeds, key                     │                         │           │          │        │
  │                 │── get(key) ─────────────────────────────────────────────▶│           │          │        │
  │                 │◀─ miss ──────────────────────────────────────────────────│           │          │        │
  │                 │ [list] name vector? ──────────▶│ get(name key) ─────────▶│           │          │        │
  │                 │                                │  miss → modelo_cargado() / embed ──────────────▶│        │
  │                 │── armar_pool ─────────────────▶│ avg(vector) ───────────────────────▶│          │        │
  │                 │                                │ k-NN, excluded in SQL ─────────────▶│          │        │
  │                 │                                │ < 20 close? recommendations ×≤3 ───────────────────────▶│
  │                 │                                │ weighted shuffle (seeded)           │          │        │
  │                 │── set(key, pool, ttl) ──────────────────────────────────────────▶│           │          │        │
  │                 │── pagina(pool, minus «Vistas») ▶│                                    │          │        │
  │◀── 200 (OK) ────│  enqueue materialization of TMDB cards shown                         │          │        │
```

## 3. Seed vector

### Titles

`avg(vector)` in SQL over the `ready` embeddings of the seeds, then L2
normalized in Python. Measured on 13/11/2026 (local Docker, 6 077 vectors):

| Seeds | `avg()` in SQL, median / max | Same in Python (load + `numpy.mean`) |
| ----: | ---------------------------: | -----------------------------------: |
|     1 |                       0.5 ms |                               1.1 ms |
|    10 |                       0.6 ms |                               3.6 ms |
|   100 |                       1.9 ms |                                27 ms |
| 1 000 |                 13.6 / 18 ms |                         273 / 343 ms |

So the average stays in SQL and only one 1 024-float vector travels. Every
title weighs the same. Weighting by recency was considered (a playlist leans
on what was added last) and left out: it adds a parameter without evidence.

Seeds without a `ready` vector (just added, embedding pending) are skipped,
and **one is enough** to mark the pool `completo=False` (5 min TTL): the
signature does not change when an embedding goes from `pending` to `ready`, so
a 24 h pool would ignore that title until it expired. If **no** seed has a
vector, there is no local search and the pool is TMDB only.

Averaging assumes the list has one theme. A list with two unrelated groups
gives a vector between both. Measuring it is the last task of PR 2; the
follow-up, if it shows up, is k-means with 2–3 centroids and interleaved
results, not part of this change.

### List name (lists only, custom lists only)

Favorites has a system label, never a meaningful name, so it never uses it.

**When the name says something (D-2)**: normalize (lowercase, `unaccent`),
drop digits, split on spaces, remove a fixed set of filler words in English and
Spanish (`list`, `lista`, `my`, `mi`, `mis`, `new`, `nueva`, `movies`,
`películas`, `pelis`, `series`, `shows`, `tv`, `watch`, `ver`, `to`, `para`,
`de`, `the`, `and`, `y`, `misc`, `varios`, `cosas`, `stuff`). If a word of 3 or
more letters remains, the name is used. «Lista 3» and «My list» are not; «Sci
Fi», «Pelis para llorar» and «Domingo de lluvia» are. Names allow only letters,
digits and spaces (19/09/2026), so there is nothing else to clean. A semantic
test (distance between the name and the list) was discarded: bge-m3 gives
moderate similarity to almost anything, so a threshold would be arbitrary and
the rule would not be testable without Ollama.

**Weight (D-1)**: with `n` titles with a vector,

```
v = normalize( (1 − w) · normalize(avg) + w · normalize(nombre) ),   w = max(0.15, 1 / (n + 1))
```

| n   | 1    | 2    | 3    | 4    | 5    | 6+   |
| --- | ---- | ---- | ---- | ---- | ---- | ---- |
| w   | 0.50 | 0.33 | 0.25 | 0.20 | 0.17 | 0.15 |

With one title the name is what tells «Titanic in "Pelis para llorar"» from
«Titanic in "Barcos"». With many titles the titles speak and the name only
tilts. bge-m3 is multilingual, so a Spanish name against English canonical
texts works (B-06 already relies on it for the chatbot).

**Text embedded**: the name as the user wrote it, trimmed, with no label or
prefix (bge-m3 needs none for short queries, as in `buscar_semantico`). The
normalized form is only for the rule above and the cache key.

**Name vector cache**: `similares:nombre:{MODEL_VERSION}:{sha256(normalized
name)}`, 30 days. Names repeat across users («Sci Fi», «Terror»), so most
requests never reach Ollama.

**Ollama not loaded (D-9)**: the chatbot waits up to 20 s for a cold load
(`PRESUPUESTO_CARGA`); a row under a list must not. The flow is:

1. Name vector in Redis → use it.
2. Flag `similares:ollama_no` set → skip the name.
3. `modelo_cargado()` (1 s timeout) is false or fails → skip the name, call
   `pedir_carga_del_modelo()` (already rate-limited to one per minute), and on
   failure set `similares:ollama_no` for 60 s, so a downed Ollama costs 1 s at
   most once a minute and not on every request.
4. Loaded → `generar_vector(nombre, **PRESUPUESTO_CHAT)` (3 s, no retries);
   on `EmbeddingProviderError` skip the name.

Skipping the name gives `nombre_usado=false` and `completo=False`: the pool is
cached for 5 minutes instead of 24 hours, so once the model is loaded the
suggestions pick up the name. Titles' vectors are already in Postgres; Ollama
is never needed for them.

## 4. Candidates in pgvector

Everything below runs inside one `transaction.atomic()`, like
`_ids_mas_cercanos` in `semantica.py`: `SET LOCAL` only lasts until the end of
the transaction, and in Django's autocommit each `execute` would be its own, so
the settings would not reach the `SELECT`.

```sql
SET LOCAL hnsw.ef_search = 100;
SET LOCAL hnsw.iterative_scan = relaxed_order;
SELECT e.produccion_id, e.vector <=> %(v)s AS d
FROM produccion_embedding e JOIN produccion_audiovisual p ON p.id = e.produccion_id
WHERE e.estado = 'ready'
  AND e.produccion_id <> ALL(%(excluir)s)          -- the seeds
  AND p.tipo = ANY(%(tipos)s)
  AND p.poster <> '' AND p.calificacion_promedio > 0   -- D-5
ORDER BY d LIMIT 100;
```

Then only those with `d ≤ DISTANCIA_MAXIMA` count as "close".

**Why exclusion in SQL with iterative scan.** Measured with a list made of the
`n` nearest neighbours of a random title (the worst case: everything around the
centroid is already in the list), asking for 100:

|     n | Fetch `100 + n`, filter in Python | `WHERE` without iterative scan | `WHERE` + `iterative_scan` |
| ----: | --------------------------------: | -----------------------------: | -------------------------: |
|     1 |                   22 ms, 100 rows |                21 ms, 100 rows |            21 ms, 100 rows |
|   100 |                   22 ms, 100 rows |              6 ms, **31 rows** |             7 ms, 100 rows |
| 1 000 |                   34 ms, 100 rows |              18 ms, **0 rows** |            21 ms, 100 rows |

Without iterative scan the index stops after `ef_search` candidates and the
filter empties them silently, the same trap as `ef_search = 40` in B-06.
pgvector 0.8.6 is installed, so `relaxed_order` is available; the final
`ORDER BY d` restores the exact order. At 6 000 rows the planner often picks
an exact scan (seen in `EXPLAIN`), which is why everything sits around 20 ms;
the index matters after the mass population.

**Close enough (`DISTANCIA_MAXIMA`)**: cosine distance of the k-th neighbour of
a single title, 40 random titles:

| Rank |   p10 | median |   p90 |
| ---: | ----: | -----: | ----: |
|    1 | 0.169 |  0.269 | 0.339 |
|   10 | 0.307 |  0.336 | 0.376 |
|   50 | 0.341 |  0.363 | 0.409 |
|  100 | 0.355 |  0.376 | 0.420 |

Start with **0.40**: a typical title has 50+ neighbours under it and a niche
one has few, which is exactly when TMDB should fill. A centroid of many titles
is closer to everything, so the value is checked with three real lists in PR 2
and fixed in `docs/decisiones.md`.

**Type (D-3)**: the canonical text has no type, so movies and shows mix
naturally. A list with only movies asks `tipos=['pelicula']`, only shows
`['serie']`, mixed both. The title page always mixes (decided), and each card
shows its type (`showType`).

**Adult content**: `ProduccionAudiovisual` has no adult flag, and nothing in the
local catalog comes from a listing with `include_adult=true`. The TMDB fill
drops `adult: true`. The quality floor of D-5 (poster and at least one vote)
is what keeps out the obscure rows that `recomendado.py` saw on 13/10/2026.
A real adult filter stays in Gonza's pending decisions.

## 5. TMDB fill

When fewer than **20** local candidates are under `DISTANCIA_MAXIMA`:

- **Seeds**: the title of the page; for a list, the 3 most recently added
  items. `GET /{tipo}/{id}/recommendations`, page 1 (20 results each), through
  `TMDBClientCache` (24 h, already used by the chatbot) and the localized
  service. Calls: 1–3, up to 6 if the language fallback completes in English.
  Well under 30 per request; a cached seed costs none.
- **Filter**: drop `adult`, `vote_count < 10`, no poster, the seeds, the list
  items, and anything already among local candidates (by `(id_tmdb, tipo)`).
- **Order**: local close ones first, then TMDB interleaved round robin by seed
  (so one seed does not take every slot), then local beyond the threshold.
- **Materialization**: the TMDB cards shown are enqueued with
  `materializar_listado_en_segundo_plano`, like every listing (at most once
  per 10 minutes per title). They enter the catalog and get a vector, so the
  next pool can find them locally. «+ Add» goes through the existing
  `POST /api/lists/{id}/items/`, which materializes synchronously.
- **Failure**: `TMDBError` or the budget runs out → the pool is local only,
  `completo=False` (5 min TTL). A missing fill is not an error.

**Known limit**: `/recommendations` groups by theme and popularity, not by
country or language: on 06/11/2026, for _Relatos salvajes_ it brought almost
only English-language films. The local vectors do not encode country either
(the canonical text has title, genres, people, keywords and synopsis), but
they keep the people and keywords, so for an Argentine film they at least pull
other films with the same director or cast. Putting local first is the
mitigation. Adding country and original language to the canonical text would
help both rows, at the cost of regenerating every vector: a separate change.

## 6. Pool, pages and «Refresh»

**Pool**: up to **60** entries (local close + TMDB + local far), already
ordered and shuffled. 60 is six «Refresh» pages, plus margin for what
«Vistas» removes.

**Controlled randomness**: a pool ordered strictly by distance makes «Refresh»
go from good to worse, and the same list always shows the same first ten. The
pool is shuffled once, with weights, using the Efraimidis–Spirakis key
`u^(1/peso)`, where `peso` decreases with the position (`1 / (1 + rank / 10)`)
and `u` comes from `random.Random(seed)`. The seed is the cache key's
signature, so:

- the order is reproducible (tests, and two tabs see the same pages);
- page 1 is mostly, not only, the closest ten;
- changing the list changes the signature and gives a new shuffle.

**Pages**: `pagina(pool, excluir_pares, numero)` removes «Vistas» (and, for
lists, nothing else: the seeds are already out) and returns slice
`[(numero − 1) · 10, numero · 10)`. «Refresh» asks for the next number; after
the last one it goes back to 1. No recalculation: the pool comes from Redis.

**After «+ Add»**: the item enters the list, so the signature changes and the
next request recomputes a new pool, which is a new shuffle. The frontend does
not refetch: it marks that card as added and keeps the rest. The row keeps the
set of `(id_tmdb, tipo)` it has shown; after an add, «Refresh» asks for page 1
of the new pool (not page 2) and drops what was already shown, so a card never
appears twice.

## 7. Endpoints

### `GET /api/catalogo/{movie|tv}/{id_tmdb}/similar/`

- **Permission**: `AllowAny`, with the project's JWT cookie authentication so a
  session is recognized. Throttle scope `catalogo` (60/min). `TopesTMDBMixin`.
  DRF authenticates before checking permissions, so an expired or invalid
  cookie would answer 401 (Unauthorized) even with `AllowAny`, and the row
  would vanish for that visitor. The view uses an optional authentication
  class: the project's JWT cookie class, returning `None` (anonymous) on
  `InvalidToken` or `AuthenticationFailed` instead of raising.
- **Seed**: `ProduccionAudiovisual` by `(id_tmdb, tipo)`. With a `ready`
  vector → engine. Not in the catalog or without vector → TMDB fill only,
  `completo=False` (10 min). The detail views already enqueue its
  materialization, so after a few minutes the title has its vector and the
  next pool is local.
- **Cache**: `similares:titulo:{tipo}:{id_tmdb}:{idioma}:{MODEL_VERSION}`, 24 h, the
  same as TMDB's `/recommendations` cache; the local catalog changes once a
  night. The pool never holds anything about the user.
- **Per user**: with a session, remove the user's «Vistas» (`vistos()` of
  `recomendado.py`) after reading the pool. Answer `Cache-Control: private`.
  Without a session, `public, max-age=300` and `Vary: Accept-Language`, like
  the rest of the catalog.
- **Answer**: the first 20 (D-7), `{"results": [...]}`.

### `GET /api/lists/{id}/suggestions/?pagina=N`

- **Permission**: the project default (session required, 401 (Unauthorized)
  without one). Someone else's list or an inactive one → 404 (Not Found)
  `not_found` (`_lista_propia`), so it does not reveal that the id exists.
  Pendientes and Vistas → 404 (Not Found) `not_found` too: the resource does
  not exist for them, and the frontend never asks.
- **Throttle**: `catalogo` scope (it is a read; `EscrituraThrottle` counts
  only writes). `TopesTMDBMixin`.
- **`pagina`**: integer ≥ 1, default 1; 0, negative or non-numeric →
  400 (Bad Request) `invalid` on `pagina`. Greater than `paginas` → empty
  `results` (the frontend wraps to 1 before asking).
- **Empty list** → 200 (OK) with `results: []`, no TMDB, no cache.
- **Cache**: `similares:lista:{id}:{firma}`, 24 h (5 min if `completo=False`).
  `firma = sha256(MODEL_VERSION, idioma, normalized name, the sorted
production ids of the list)`, computed with one query:
  `SELECT string_agg(produccion_id::text, ',' ORDER BY produccion_id) FROM
tiene WHERE lista_id = %s` (1 000 ids: a few ms). No invalidation code: add,
  remove or rename changes the signature and the old key expires alone.
  «Vistas» is not in the signature because it is removed after the cache, so
  rating something (which adds to «Vistas») does not recompute the pool.
- **Answer**:

```json
{
  "results": [
    {
      "id_tmdb": 157336,
      "tipo": "movie",
      "titulo": "Interstellar",
      "poster": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
      "anio": 2014,
      "calificacion_promedio": 8.4,
      "campos_en_ingles": [],
      "origen": "catalogo"
    }
  ],
  "pagina": 1,
  "paginas": 5,
  "nombre_usado": true
}
```

Same fields as a list item minus `item_id` and `fecha_agregado`, so the
frontend reuses `itemATitulo`. Local rows are localized with
`texto_localizado` like the list detail; TMDB rows come in the request
language. `origen` is `catalogo` or `tmdb`, for logs and tests (the UI does
not show it). The title endpoint answers the same item shape.

Both views log one line per request: seeds, local close, TMDB fill, name used,
cache hit, milliseconds (like `buscar_semantico: cargado=… vector_ms=…`).

## 8. Latency

| Case                                               | Expected                     | Basis                                                |
| -------------------------------------------------- | ---------------------------- | ---------------------------------------------------- |
| Pool in Redis («Refresh», second visit)            | < 30 ms                      | One Redis read, one `vistos()` query                 |
| Cold, local only, name vector cached or not needed | 30–60 ms                     | `avg` 0.5–14 ms + k-NN ~21 ms (measured) + signature |
| Cold, name to embed, model loaded                  | + 80–125 ms                  | B-06 measurements (04/11/2026)                       |
| Cold, TMDB fill not cached                         | + 200–650 ms                 | Cold `browse/`, `search/` (28/10/2026)               |
| Ollama down                                        | + up to 1 s, once per minute | `modelo_cargado()` timeout, then the 60 s flag       |

Measured on 13/11/2026 against the local Docker database (6 077 vectors) with
`docker compose exec backend python manage.py shell`. Ollama was not running
during the measurement, so the name rows come from B-06; task 2.9 measures
them with the model loaded. The title page adds **nothing** to the detail: the
row is a separate request made when it nears the viewport (§9).

## 9. Frontend

The screens are drawn in the Claude Design canvas first (task 3.1, not part of
this change's writing). What follows is the behaviour the canvas must cover.

### Shared: `MediaRow`

`MediaRow` (Home) already has the heading, arrows that move one page, swipe
with snap on mobile, skeletons and «hide when empty». It gains two optional
props, without changing the Home:

- `encabezado?: ReactNode` — next to the arrows (the «Refresh» button).
- `accion?: (item: Title) => ReactNode` — rendered in the `<li>`, after the
  `MediaCard`, never inside it: the card is a `<Link>` and a button inside a
  link is invalid and unreachable for screen readers.

### List row (`components/features/lists/ListSuggestions.tsx`)

- Shown in custom lists and Favorites with at least 1 item, always at the
  end of the detail, with or without an active filter or search (D-6). With
  infinite scroll it is drawn after what is loaded, once there is no next page
  (of the filtered view when a filter is active), so it does not keep moving
  down while pages arrive.
- Filters and search never change the suggestions: the seeds, the signature
  and the cache are always those of the whole list, and the request does not
  carry the filter parameters. Changing a filter does not refetch the row.
- A filter that leaves the grid empty still shows the row, under the
  «No titles in this list match these filters» state and its «Clear» button.
- `aria-busy` and skeletons while loading. Error → a small `ErrorRetry` inside
  the section, the list keeps working. Empty `results` → the row is not drawn.
- **«+ Add»**: `POST /api/lists/{id}/items/`; the button becomes «Added» with a
  check and `disabled`, and the item is appended to the grid locally. Errors by
  code (`list_items_limit_reached`, `item_duplicate`…) with the existing toast
  messages. `aria-label`: «Add {title} to {listName}».
- **«Refresh»**: asks for `pagina + 1` (or 1 after `paginas`), keeps the old
  cards until the new ones arrive (no jump to skeleton), returns the row to its
  start, and announces «New suggestions» in a polite `role="status"`. Focus
  stays on the button.
- Keyboard: Tab goes card → its «+ Add» → next card; arrows of `MediaRow`
  already move with buttons; nothing depends on hover (`[@media(hover:none)]`
  shows the add button on touch, as the remove button does in the grid).
- `prefers-reduced-motion`: scroll without smooth behaviour (already in
  `MediaRow`).

### Title page row (`components/features/title/SimilarTitles.tsx`)

- Heading «More like {title}». After «Director and cast», before reviews.
- Requested when a sentinel is 400 px from the viewport
  (`IntersectionObserver`), never in the detail's first render: the detail
  does not wait for it and visitors who do not scroll do not pay for it.
- Skeletons while loading; empty or error → the row is not drawn (it is
  secondary; the page does not show an error for it).
- `showType` on, `from` keeps the origin of the current page.

### Copy (D-8)

New keys in `traducciones/claves-extra.csv` (or `claves.csv` if the canvas
brings them), approved by Gonza, then `npm run i18n:generate` and
`npm run i18n:check`:

| Key                              | en                                    | es                                     |
| -------------------------------- | ------------------------------------- | -------------------------------------- |
| `lists.suggestions.title`        | Suggested for this list               | Sugeridas para esta lista              |
| `lists.suggestions.add`          | Add                                   | Agregar                                |
| `lists.suggestions.addLabel`     | Add {title} to {listName}             | Agregar {title} a {listName}           |
| `lists.suggestions.added`        | Added                                 | Agregada                               |
| `lists.suggestions.refresh`      | Refresh                               | Ver otras                              |
| `lists.suggestions.refreshLabel` | Show other suggestions for {listName} | Ver otras sugerencias para {listName}  |
| `lists.suggestions.refreshed`    | New suggestions                       | Nuevas sugerencias                     |
| `lists.suggestions.loadError`    | Couldn't load suggestions.            | No se pudieron cargar las sugerencias. |
| `title.similar.title`            | More like {title}                     | Parecidos a {title}                    |

## 10. Testing

- **Engine** (`catalogo/tests_similares.py`), with fixed vectors in the test
  database (no Ollama, `MockTransport` for the name): centroid order, the
  weight table of D-1, the filler words of D-2, exclusion of 1 000 neighbours
  still returns 100 (the iterative-scan regression), type filter, quality
  floor, TMDB fill order and dedup, shuffle reproducible with the same seed
  and different with another, pages and wrap.
- **Title endpoint**: anonymous gets public cache headers and «Vistas» is
  ignored; with a session «Vistas» is removed and the answer is `private`;
  the cached pool is the same for two users; title without vector → TMDB only
  and short TTL; TMDB failure → local only, 200 (OK).
- **List endpoint**: 401 (Unauthorized) without session; 404 (Not Found) for
  someone else's list, Pendientes and Vistas; `pagina` validation; empty list;
  adding an item changes the signature; renaming changes it; rating something
  does not; Ollama down skips the name, sets the 60 s flag and the 5 min TTL;
  budget of TMDB calls (≤ 6) asserted with the counter.
- **Frontend** (Vitest): add marks «Added» and appends to the grid; refresh
  wraps; error and empty states; labels; the row waits for the last page, is
  shown with an active filter (also under the empty filtered state) and does
  not refetch when the filter changes; the title row requests only after the sentinel
  intersects.
- **e2e** (Playwright, controlled API like the profile tests): add from the
  row, refresh, keyboard path, axe on both rows.

## 11. Decisions (decided 13/11/2026)

Gonza answered the open questions on 13/11/2026. All follow the recommendation
except D-6.

| #   | Question                                  | Decision                                                                                                                                                                                                                                                                 | Why                                                                                                                                                |
| --- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| D-1 | Weight of the name                        | **`max(0.15, 1/(n+1))`**                                                                                                                                                                                                                                                 | With 1 title the name is half of the intent; with 50 it should only tilt. A fixed weight either drowns big lists or ignores the name in small ones |
| D-2 | When the name says something              | **Filler-word rule** (§3)                                                                                                                                                                                                                                                | Deterministic, testable without Ollama, and «Lista 3» never moves the vector                                                                       |
| D-3 | Lists of a single type                    | **Only that type**; mixed lists and the title page mix both                                                                                                                                                                                                              | A list of only shows is a strong signal                                                                                                            |
| D-4 | Favorites excludes «Vistas»               | **Yes**, like every row                                                                                                                                                                                                                                                  | One rule everywhere; suggestions are for discovering                                                                                               |
| D-5 | Quality floor                             | **Poster and rating locally; TMDB fill without `adult` and with ≥ 10 votes**                                                                                                                                                                                             | The local model stores no vote count, and a card without poster looks broken                                                                       |
| D-6 | List row with infinite scroll and filters | **Changed from the proposal**: always at the end of the detail, with or without filters or search; drawn after what is loaded once there is no next page (of the filtered view if filtering); also under the empty filtered state. Suggestions always use the whole list | Gonza prefers the row to be always reachable at the end. Filters only change what the grid shows, never the seeds or the cache (§9)                |
| D-7 | Title page size and Refresh               | **20 cards, no Refresh**                                                                                                                                                                                                                                                 | Two pages of the desktop row; a title page is browsed, not curated                                                                                 |
| D-8 | Copy                                      | **The table of §9, approved together with the canvas** (task 3.1)                                                                                                                                                                                                        | The wording depends on the design                                                                                                                  |
| D-9 | Ollama not loaded                         | **Skip the name without waiting, request the load, cache the pool for 5 min**                                                                                                                                                                                            | The row is secondary and the titles' vectors do not need Ollama                                                                                    |
