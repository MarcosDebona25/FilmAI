# Proposal: Ratings and Reviews API (C-08, CU-015)

## Intent

`Calificacion` and `Resena` have existed since F-04 and nothing can write to
them. The only rows in any developer's database came from `manage.py seed`.

That gap is not only C-08's own: two merged deliverables already depend on
ratings existing.

1. **L-01 (#27)** refuses to remove a production from the predetermined
   `Vistas` list while an active rating exists, answering 409 with
   *"Eliminá la calificación antes de quitar esta producción de Vistas."*
   The rule is implemented and tested, and it can never fire in production —
   nor can a user obey its instruction, because no endpoint deletes a rating.
2. **AD-01' (#30)** moderates reviews that nobody can publish.

C-08 closes CU-015: publish, modify and delete one's own rating and review.
It is also the last backend work in Module 2 — C-05, C-06 and C-07 consume
the C-03 endpoints that already exist.

## Scope

### In Scope

- `POST /api/reviews/` — rate a production (1-10) with optional text
- `PUT /api/reviews/{id}/` — change the rating and/or the text
- `DELETE /api/reviews/{id}/texto/` — delete **only the text**, keep the rating
- `DELETE /api/reviews/{id}/` — delete the rating **and** its text
- `GET /api/reviews/?id_tmdb=&tipo=` — the community's reviews for one
  production, cursor-paginated (C-07's "Reseñas de la comunidad (N)" and its
  "Cargar más")
- `GET /api/reviews/mias/` — every review of the authenticated user, newest
  first, cursor-paginated (P-06, "Mis reseñas")
- `GET /api/reviews/mias/?id_tmdb=&tipo=` — the user's own rating for one
  production, so C-07 can render "Tu reseña" and open the modal pre-filled
- Writing through `materializar()`, as L-01 does: a rating needs a local
  `ProduccionAudiovisual` row and the API receives a TMDB identity
- Moderated reviews (`activa=False`) hidden from everyone except their author
- Canonical spec `openspec/specs/reviews-api/spec.md`
- `docs/04_Lineamientos_UI.md`: the detail screen must state what happens
  after deleting the text, because the rating survives (see below)

### Out of Scope

- **The UI.** The modal, the star widget and the review sections are C-07 and
  C-08's frontend half, and land with the rest of the catalog UI.
- **Recomputing `calificacion_promedio`.** That column holds TMDB's
  `vote_average`, not our users' average. Mixing the two would change the
  meaning of a field three screens already display. If a local average is
  wanted, it is a new field and a separate decision.
- **Regenerating embeddings.** The canonical text is
  `Title + Genres + Directors + Cast + Keywords + Synopsis`; a rating changes
  none of it, so nothing needs re-embedding.
- **Moderating ratings.** `Calificacion.activa` exists and the Admin of AD-01'
  does not use it. This API always writes `True` and reads only active rows;
  wiring it to the Admin is AD-01's business, not ours.
- **Likes, replies or reporting reviews.** Not in CU-015.

## The GET endpoints are not optional

The plan's row for C-08 lists only `POST | PUT | DELETE /api/reviews/`. But
`docs/04_Lineamientos_UI.md` §5c asks the detail screen for "Tu reseña" plus
"Reseñas de la comunidad (N)" with a "Cargar más reseñas" button, and §5i asks
"Mis reseñas" for an infinite scroll of the user's reviews. Neither screen can
be built without reading. The three `GET`s above are therefore part of C-08,
and the plan's row is corrected rather than followed literally.

## One decision the documents do not settle

Deleting a review **removes the text and keeps the rating** (decided
26/09/2026). That contradicts `docs/04_Lineamientos_UI.md`, which says the
"Calificar" button returns after deleting — it cannot, because the rating is
still there. The UI document is updated: after deleting the text the button
shows the surviving rating and opens the modal in edit mode, and the "Tu
reseña" card disappears (§5c already says only reviews *with text* are
listed).

This is also why there are two `DELETE`s. The text-only one serves the 🗑️ of
the modal; the full one is what L-01's error message tells the user to do.

## Success Criteria

1. A user can rate a production 1-10, with or without text, and rating the
   same production twice answers 409 instead of creating a second row.
2. Ratings outside 1-10 and text over 1000 characters are rejected with 400.
3. The rating's production is materialized: the row has genres, cast and a
   non-null `fecha_enriquecimiento` even if nobody opened its detail page.
4. Deleting the text keeps the rating; deleting the rating removes both, and
   afterwards the production can be removed from `Vistas` — L-01's 409 stops
   firing. Verified end to end against L-01's endpoint.
5. Community reviews exclude entries without text, inactive ones and the
   requester's own; the author still sees their own moderated review.
6. Every endpoint requires authentication, and another user's rating is 404,
   never 403 — the same ownership policy as L-01.
7. Full backend suite and ruff stay green.
