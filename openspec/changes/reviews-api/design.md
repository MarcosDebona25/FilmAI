# Design: Ratings and Reviews API (C-08)

## Where this lives

The models are in `catalogo`, so the API goes there too: `catalogo/reviews.py`
for the views, next to the existing `views.py` of C-03. Splitting it into its
own module keeps the TMDB passthrough views and the local-write views apart —
they have different failure policies and different authentication.

```
frontend ──HTTP──▶ /api/reviews/ (catalogo/reviews.py)
                        │
                        ├──▶ materializar(id_tmdb, tipo) ──HTTP──▶ TMDB (detail+credits+keywords)
                        │         └──SQL──▶ ProduccionAudiovisual
                        │
                        └──SQL──▶ Calificacion 1──0..1 Resena
                                       ▲
                                       └── L-01 reads this to protect "Vistas"
                                       └── ResenaAdmin (AD-01') moderates Resena.activa
```

Nothing new talks to anything new. This is the **fifth** caller of
`materializar()`, after the detail views (C-04a), the sync (C-04b), the seed
(C-04c) and the list items (L-01).

## The resource

CU-015 treats the rating and its text as one thing the user publishes, and the
model splits them: `Calificacion` (1-10, required) with an optional 1:1
`Resena` (text ≤ 1000). The API exposes the pair under one name, `/api/reviews/`,
as the plan calls it, and the `{id}` in the path is the **`Calificacion` pk** —
the rating is what always exists.

| Verb | Path | Effect |
|---|---|---|
| POST | `/api/reviews/` | `{id_tmdb, tipo, valor, texto?}` → creates the rating, and the review if `texto` came |
| PUT | `/api/reviews/{id}/` | `{valor?, texto?}` → updates either; `texto: ""` is rejected, use the text DELETE |
| DELETE | `/api/reviews/{id}/texto/` | deletes the `Resena` row, keeps the rating |
| DELETE | `/api/reviews/{id}/` | deletes the `Calificacion`; the `Resena` follows by CASCADE |
| GET | `/api/reviews/?id_tmdb=&tipo=` | the community's reviews for that production |
| GET | `/api/reviews/mias/` | the user's own reviews, newest first |
| GET | `/api/reviews/mias/?id_tmdb=&tipo=` | the user's rating for that production, or 404 |

## Architecture Decisions

| Decision | Alternative rejected | Why |
|---|---|---|
| Two `DELETE`s, one per meaning | One `DELETE` that removes everything | Deleting the text keeps the rating (decision of 26/09/2026), so the modal's 🗑️ cannot be the only delete: L-01's own error message tells the user to *"eliminá la calificación"*, which needs an endpoint. Two paths, each doing what its URL says, beats one endpoint with a flag. |
| `{id}` is the `Calificacion` pk | Address by `(id_tmdb, tipo)` and upsert | The natural key is unique, so an upsert would work and would spare the frontend from remembering an id. But it hides two different outcomes (created / updated) behind one call, and "Mis reseñas" (P-06) already receives the id in every row. A `POST` that answers 409 on a second rating is the clearer contract. |
| The user's delete is **physical** | Logical delete with `activa=False` | CU-015 asks to *"eliminar esta reseña permanentemente"*, and `activa` already means one thing: moderated by an admin (AD-01'). Giving one column two meanings would make "why is this review hidden?" unanswerable. |
| Community reviews exclude the requester's own | Return everything and let the UI filter | §5c of the UI document renders "Tu reseña" as a separate card above the community list. Sending it twice makes every consumer deduplicate, and a paginated list cannot promise the user's own review is on page 1. |
| Only reviews **with text** in the community list | Include text-less ratings | §5c states it: a rating with no text has nothing to read. It still counts for the production's local statistics, if we ever add them. |
| Write through `materializar()` | Insert a bare `ProduccionAudiovisual` row | Same reason as L-01: a rating's FK must point at a complete production, and `materializar()` is the single write path. A user can rate from a search result the detail view never opened. |
| Cursor pagination, 20 per page | Page-number pagination | The two screens are infinite scrolls, and a new review arriving mid-scroll shifts every offset. Reuses the shape of `ListaItemCursorPagination` (L-01). |
| 409 conflicts carry a stable `codigo` | Plain 400 with a message | The frontend needs to tell "you already rated this" from a validation error, and L-01 already established the `{codigo, detail}` envelope in `listas/exceptions.py`. Consistency across the two APIs is worth more than either shape. |

## Moderation and visibility

A review moderated by the Admin (`Resena.activa = False`) is hidden from
everyone **except its author** (decision of 26/09/2026).

| Reader | Sees an inactive review? |
|---|---|
| The community list, any user | No |
| `GET /api/reviews/mias/`, the author | Yes |
| The author's own "Tu reseña" on the detail screen | Yes |
| Django Admin | Yes — AD-01' needs it to reactivate |

The author is not told it was moderated: CU-017 says nothing about notifying,
and inventing a notice is a product decision, not an implementation detail.
What matters is that their own text never vanishes from their own screens with
no explanation available.

`Calificacion.activa` is a different field. The Admin does not touch it and
this API always writes `True`, but every read filters on it anyway, so that
the day AD-01 moderates ratings nothing here has to change.

## What a rating does *not* touch

- **`ProduccionAudiovisual.calificacion_promedio`** is TMDB's `vote_average`.
  It is not recomputed. Three screens show it as "rating TMDB".
- **The embedding.** The canonical text has six sections and none of them is a
  rating, so `source_hash` does not change and nothing is re-enqueued.
- **List membership.** Rating something does not add it to `Vistas`. The UI may
  offer that as a convenience later; it is not in CU-015 and doing it silently
  from the API would write to another module's tables.

## Failure policy

Opposite to C-03's passthrough, and the same as L-01: these endpoints **fail
loudly**. A `materializar()` error must not be swallowed, because unlike a
detail view there is no useful response to fall back on — if the production
could not be stored, the rating cannot exist. `materializar()` propagates by
design (C-04a) and here that propagation is what we want.

## Testing Strategy

| Level | What |
|---|---|
| Unit | Validation: `valor` outside 1-10, text over 1000, missing `valor`, unknown `tipo` |
| Unit | A second rating of the same production answers 409 with its `codigo` |
| Unit | `PUT` changes the rating, the text, or both; adds text to a rating that had none |
| Unit | Text `DELETE` keeps the rating; rating `DELETE` removes both |
| Unit | Ownership: another user's rating is 404 on `PUT` and both `DELETE`s |
| Unit | Community list excludes text-less, inactive, and the requester's own |
| Unit | `mias/` includes the author's inactive review |
| Unit | Cursor pagination: 20 per page, newest first, stable across a new insert |
| Integration | `POST` with `materializar()` real and TMDB faked: the production lands enriched |
| Integration | **With L-01's endpoint**: rate → `Vistas` removal answers 409 → delete the rating → removal succeeds. The rule Marcos wrote finally executes end to end |
