# Proposal: Home de descubrimiento (C-05)

## Intent

Every catalog screen is still missing. `/home` is linked from the navbar, the
mobile tabs, the footer, the 404 page and the landing, and it answers
404 (Not Found). After logging in, the user is sent back to the landing (`/`)
because there is nowhere else to go (A-04 🟡).

C-05 builds the first catalog screen, following the canvas artboards
«Home · desktop» and «Home · mobile» (section 3). It also builds the pieces that
the next screens reuse: the card of a title (`MediaCard`), the horizontal row
(`MediaRow`) and the `All · Movies · TV shows` selector (`TypeSelector`). Search
(C-06) and the list detail (L-03, Marcos) consume them.

The only backend work is «Recommended for you», which no endpoint serves
today. Trending, now playing and discover already exist (C-03).

## Scope

### In Scope

- `GET /api/catalogo/recommended/?tipo=all|movie|tv`: authenticated, built from
  the user's ratings of 7 or more (see design §2)
- `min_votes` as a new optional parameter of `GET /api/catalogo/discover/`
  (`vote_count.gte` in TMDB), for the TV half of «New releases»
- `/home` page, public: Hero, «Recommended for you» (signed in only), «Trending
  this week», «New releases» and, signed out, the sign-up callout
- `TypeSelector`, `MediaCard`, `MediaRow` and `HomeHero` components, with
  loading skeletons
- `routes.title(tipo, id)` → `/movie/[id]` and `/tv/[id]`. The cards link there
  and get 404 (Not Found) until C-07 builds the page
- Navbar over the Hero backdrop on desktop, as the artboard draws it
- «Ask FilmAI» floating button, signed in only, linking to `/chat`: it answers
  404 (Not Found) until B-04, like the footer link
- Login and Google sign-up land on `/home` instead of `/` (closes A-04)
- Canonical specs `openspec/specs/recommendations-api/spec.md` and
  `openspec/specs/home-ui/spec.md`
- `docs/04_Lineamientos_UI.md` §2, §3.3 and §5 updated with what this change
  decides; `docs/decisiones.md` entry

### Out of Scope

- **The title page** (C-07). The cards link to its routes, nothing else.
- **«See more» per row.** Doc 04 marks it optional and the canvas does not
  draw it.
- **Light theme.** The app is dark only until Settings gets Appearance (Marcos,
  12/10/2026). Every component uses the semantic tokens, so it will follow.
- **LLM-based recommendations.** Doc 04 §3.3 keeps them as a future improvement.

## Approach

The page is a client component (`"use client"` + `apiFetch`), the pattern
Marcos set for `/profile`, `/settings` and `/my-reviews`. Each row asks the
backend for its own data, so a failed row disappears without taking the others
with it. The backend only proxies TMDB through the existing Redis cache, except
for «Recommended», which reads the user's ratings and «Watched» list from
Postgres.

## Delivery

Four PRs against `develop/ui-design`, each under the 400-line review budget
(details in `tasks.md`):

1. This SDD and the docs
2. Backend: `recommended` and `min_votes`
3. Shared frontend pieces: `TypeSelector`, `MediaCard`, `MediaRow`, `routes.title`
4. The `/home` page, the navbar variant and the login redirect

## Rollback

Each PR is reverted on its own. Reverting 2 leaves the Home without the
«Recommended» row: the frontend already hides an empty or failed row. Reverting
4 brings back the 404 (Not Found) at `/home` and the redirect to `/`.
