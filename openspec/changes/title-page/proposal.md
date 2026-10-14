# Proposal: Ficha de detalle (C-07, modal de C-08 y acciones de L-04)

## Intent

Every card of the Home links to `/movie/{id}` or `/tv/{id}`, and both answer
404 (Not Found). The title page is where a user rates, reviews and saves a title:
without it, the ratings API of C-08 and the lists API of L-01 have no screen.

C-07 builds the page following the canvas artboards «Title page · desktop» and
«Title page · mobile» (section 4). It carries two pieces of other tasks that live
on the same screen:

- **The rating modal** (C-08's frontend half): rate, edit, delete the text,
  remove the rating.
- **The list actions** (L-04): Favorite, Watched and Watchlist toggles and the
  «Add to list» menu. L-04 was Marcos's; on 14/10/2026 it was agreed that Gonza
  builds it here, because Watched is tied to the rating («rated ⇒ watched»,
  30/09/2026) and both share the same confirmation flows.

## Scope

### In Scope

Backend:

- `GET /api/catalogo/{movie|tv}/{id}/credits/`: directors (for shows, the
  creators: TMDB has no series-level Director) and the cast with characters
- Community reviews (`GET /api/reviews/?id_tmdb=&tipo=`) readable **without a
  session**, as the canvas states («ratings and reviews are public»)
- Sort and rating filter on those reviews: `orden` (newest, oldest, highest,
  lowest) and `nota_min`/`nota_max`, still cursor-paginated, plus the
  unfiltered total for «Showing X of N»

Frontend:

- `/movie/[id]` and `/tv/[id]`: backdrop band, poster, breadcrumb, title,
  tagline, meta (type · year · runtime or seasons · ★ TMDB with votes), genres,
  actions, synopsis, «Director and cast», «Reviews»
- Breadcrumb from `?from=` (`home`, `search`, `reviews`, `list-{id}`); no
  parameter means Home
- Rating modal (dialog on desktop, bottom sheet on mobile) with a 1-10 star
  radiogroup, optional text up to 1000 characters and the Watched notice
- Confirmations: delete the review text, remove the rating, remove from Watched
  when the title is rated
- List actions and «Add to list» (popover on desktop, sheet on mobile) with
  inline list creation
- Reviews: «Your review» card and the community list with sort, filter and
  «Load more»
- `MediaCard` passes `from=home` on the Home
- Canonical specs `title-page-ui` and the updates to `reviews-api`
- `docs/04_Lineamientos_UI.md` §5c/§5d aligned with the canvas and these
  decisions; `docs/decisiones.md` entry

### Out of Scope

- **Search** (C-06): the next screen. The breadcrumb already accepts
  `from=search`.
- **Links from Ratings & reviews and List detail**: those screens are going to
  be redone (P-06) or built (L-03) by Marcos; they only need to add `?from=`.
- **Reporting or liking reviews**: not in CU-015.
- **Light theme**: same as the Home.

## Delivery

Five PRs against `develop/ui-design`, each under the 400-line review budget:

1. This SDD and the docs
2. Backend: credits endpoint, public community reviews with sort and filter
3. Rating modal and confirmations (components + Vitest)
4. List actions and «Add to list» (components + Vitest)
5. The page, the breadcrumb, credits and reviews sections, e2e

## Rollback

Each PR reverts on its own. Reverting 2 brings the 401 (Unauthorized) back for
anonymous readers; the page then hides the community block without a session.
Reverting 5 brings back the 404 (Not Found) at `/movie/{id}` and `/tv/{id}`.
