# reviews-api Specification

## Purpose

The user's own ratings and reviews (CU-015): publishing, editing and deleting a 1-10 rating with optional text, plus the reads the detail screen and "Mis reseñas" need. Covers C-08. Builds on `catalog-materialization`, whose `materializar()` it calls before writing, and completes two capabilities that shipped depending on ratings existing: the `Vistas` rule of `list-endpoints` (CU-011, completed on 30/09/2026 by "a rated production is in `Vistas`") and the review moderation of the Django Admin (CU-017).

## Requirements

### Requirement: The rating is the resource, the text hangs off it

A rating (1-10) is required; its text is optional and at most 1000 characters. The API MUST expose the pair as one resource under `/api/reviews/`, and the `{id}` in every path MUST be the `Calificacion` primary key, because the rating is what always exists.

A user MUST NOT rate the same production twice. A second attempt MUST answer 409 with a stable `codigo`, not a 500 from the database constraint.

#### Scenario: Rating without text

- GIVEN an authenticated user who has not rated a production
- WHEN they POST a rating with no text
- THEN the rating is stored
- AND no review row is created
- AND the response carries the rating's id

#### Scenario: Rating the same production twice

- GIVEN a user who already rated a production
- WHEN they POST another rating for it
- THEN the response is 409 with `codigo: "calificacion_duplicada"`
- AND the stored rating keeps its original value

### Requirement: Writing goes through materialization

The API MUST call `materializar()` before creating a rating, so the foreign key points at a complete production row. A user can rate from a search result no detail view ever opened.

Validation MUST happen before materialization: an out-of-range rating must not cost three TMDB requests nor leave a production stored as a side effect.

#### Scenario: Rating a production that is not stored yet

- GIVEN a production absent from the database
- WHEN a user rates it
- THEN the production is stored with its genres, cast, directors and keywords
- AND its `fecha_enriquecimiento` is not null

#### Scenario: An invalid payload reaches no external service

- GIVEN a payload with `valor` outside 1-10
- WHEN it is posted
- THEN the response is 400 naming the field
- AND no TMDB request is issued

### Requirement: Deleting the text and deleting the rating are different operations

`DELETE /api/reviews/{id}/texto/` MUST delete the text and **keep** the rating. `DELETE /api/reviews/{id}/` MUST delete the rating, and its text with it.

The text-only delete MUST be idempotent: applied to a rating with no text it MUST answer 204, not an error, since nothing about that state is a problem.

Deletion by the user MUST be physical. `activa` means one thing only — moderated by an administrator — and giving one column two meanings would make "why is this review hidden?" unanswerable.

#### Scenario: Deleting the text

- GIVEN a rating of 9 with text
- WHEN the text is deleted
- THEN the review row is gone
- AND the rating still reads 9

#### Scenario: Deleting the rating

- GIVEN a rating with text
- WHEN the rating is deleted
- THEN both rows are gone from the database

### Requirement: Ownership is invisible

Every endpoint MUST require authentication. A rating belonging to another user MUST answer 404 on update and on both deletes — never 403, which would confirm that the row exists. The same policy as `list-endpoints`.

#### Scenario: Touching someone else's rating

- GIVEN a rating owned by another user
- WHEN a user tries to update or delete it
- THEN the response is 404
- AND that rating is unchanged

### Requirement: The community's reviews of a production

`GET /api/reviews/?id_tmdb=&tipo=` MUST return the reviews other users wrote about that production, cursor-paginated at 20, newest first, with the author's username and avatar, the rating, the date and the text.

It MUST exclude three populations: ratings without text (there is nothing to read), moderated reviews, and the requester's own — which the detail screen renders separately, above the list.

The response MUST carry a `total` for the "Reseñas de la comunidad (N)" heading, which cursor pagination does not provide on its own.

Both query parameters are required; either one missing or malformed MUST answer 400. A production with no reviews MUST answer 200 with an empty list, not 404.

#### Scenario: The requester's own review is not in the list

- GIVEN a production reviewed by the requester and by another user
- WHEN the community list is requested
- THEN only the other user's review is returned
- AND `total` is 1

#### Scenario: A moderated review is hidden

- GIVEN a review with `activa = False`
- WHEN any other user requests the community list
- THEN that review does not appear

### Requirement: The user's own reviews

`GET /api/reviews/mias/` MUST return every rating of the authenticated user, newest first, cursor-paginated at 20, each with the production's title, type and poster so the row can navigate to its detail screen.

Unlike the community list it MUST include ratings without text — they can be edited from there — and MUST include the user's own moderated reviews: their text must not vanish from their own screens with no explanation available.

#### Scenario: The author still sees their moderated review

- GIVEN a review of the user with `activa = False`
- WHEN they request their own reviews
- THEN the review is returned with its text

### Requirement: The user's rating for one production

`GET /api/reviews/mias/?id_tmdb=&tipo=` MUST return that single rating as an object, not as a paginated list: the uniqueness of `(usuario, produccion)` guarantees there is at most one. When the user has not rated that production it MUST answer 404, which the detail screen reads as "show the empty rate button".

Supplying only one of the two parameters MUST answer 400, never fall back to the full list: a frontend bug that drops `tipo` would otherwise show another film's rating on this film's page.

#### Scenario: Not rated yet

- GIVEN a user who has not rated a production
- WHEN they request their rating for it
- THEN the response is 404

### Requirement: A rated production is in `Vistas`

Every rating's production MUST be in its author's predetermined `Vistas` list (decided 30/09/2026: "if you rated it, you watched it"). CU-011 already enforced one half — a rated production cannot leave `Vistas` without confirming the rating's deletion. This requirement adds the other:

- `POST /api/reviews/` MUST add the production to `Vistas` when it is not there, **in the same transaction** as the rating. If it cannot be added, the rating MUST NOT be stored.
- `DELETE /api/reviews/{id}/` MUST remove the production from the author's `Vistas`, in the same transaction as the deletion. It ends in the same state as removing from `Vistas` with `borrar_calificacion=true`.
- Editing the rating or the text, and deleting only the text, MUST NOT change `Vistas`.

The converse does not hold: a production can be in `Vistas` without a rating (CU-011). The writes into `Tiene` go through `listas/services.py`, owned by the lists module. Ratings stored before this rule are repaired once by the data migration `listas.0004_calificadas_en_vistas`.

#### Scenario: Rating adds to `Vistas`

- GIVEN a production that is not in the user's `Vistas`
- WHEN they rate it
- THEN it is in their `Vistas`

#### Scenario: Rating something already watched

- GIVEN a production the user marked as watched, without rating it
- WHEN they rate it
- THEN `Vistas` still holds it once

#### Scenario: Deleting the rating removes it from `Vistas`

- GIVEN a rated production in the user's `Vistas` and in their `Favoritos`
- WHEN the rating is deleted
- THEN it is no longer in their `Vistas`
- AND it is still in their `Favoritos`
- AND other users' `Vistas` are untouched

#### Scenario: Deleting only the text keeps it in `Vistas`

- GIVEN a rated production with text, in the user's `Vistas`
- WHEN only the text is deleted
- THEN it is still in their `Vistas`

### Requirement: Removing from `Vistas` may delete the rating on request

`DELETE /api/lists/{id}/items/{item_id}/` accepts `?borrar_calificacion=`. Without it, or with a false value, the 409 required by CU-011 stands unchanged. With a true value, and only for the predetermined `Vistas` list, the rating and the item MUST be deleted **in a single transaction**.

The flag is permission, not instruction: with no rating present it is an ordinary removal, and on any other list it deletes nothing extra. A value that is neither true nor false MUST answer 400 rather than be guessed, because a typo read as false would answer 409 to a user who already confirmed the deletion.

Two frontend calls MUST NOT be the mechanism: they are not atomic, and a failure between them would lose the rating while leaving the production in `Vistas`.

#### Scenario: Confirmed removal

- GIVEN a production in `Vistas` rated by its owner
- WHEN the item is deleted with `borrar_calificacion=true`
- THEN the item and the rating are both gone
- AND the review text is gone with the rating

#### Scenario: The default is unchanged

- GIVEN the same state
- WHEN the item is deleted with no flag
- THEN the response is 409 with `codigo: "calificacion_impide_quitar_de_vistas"`
- AND nothing is deleted

## What this capability does not touch

- **`calificacion_promedio`** holds TMDB's `vote_average`, not the average of our users' ratings. It is never recomputed here; three screens display it as "rating TMDB".
- **Embeddings.** The canonical text is `Title + Genres + Directors + Cast + Keywords + Synopsis`; a rating changes none of it, so nothing is re-enqueued.
- **Other lists.** Only `Vistas` follows the rating. `Favoritos`, `Pendientes` and custom lists never change when a rating is created or deleted.
- **`Calificacion.activa`.** This API always writes `True` and every read filters on it, so that moderating ratings later needs no change here.

## Known limitations

- Both paginated lists count their total with a `COUNT(*)` on every page request, inside `paginate_queryset()`. Fine at the current scale; if it ever hurts, the count belongs on the first page only.
- `Calificacion.fecha` is a `DateField`, so every rating from the same day ties; the cursor breaks the tie by descending id. An ordering closer to real time would need a `DateTimeField` and a migration.

### Requirement: Own reviews UI with posters

`/mis-resenas` MUST display each own rating with a poster, title, type, a yellow (#f5c518) decorative star beside its X/10 value, date and optional text. The star MUST precede the numeric rating on the same line. The date MUST appear separately in the top-right corner of the card, with no overlap at mobile widths. The rating MUST have an accessible label identifying it as a rating. Read-more/read-less controls MUST only appear when the text exceeds three visible lines at the current card width, recalculating after resizing or editing. Text that fits, including exactly three lines, and absent text MUST have no expansion control. An absent review MUST display “Todavía no escribiste una reseña.” as an informative empty state with icon, subtle background, dashed border and italic text, visually distinct from authored content. Poster dimensions MUST be reserved (80 × 120 desktop, 56 × 84 mobile); absent or failed images MUST have an accessible replacement. Titles MUST remain plain text until the detail route exists.

The UI MUST progressively load cursor pages and expose a keyboard-accessible load-more button. Duplicate IDs MUST not create duplicate cards. A page failure MUST preserve previously loaded cards and offer retry.

The edit dialog MUST be titled `Editar calificación y reseña de "{title}"`. Editing MUST initially focus the review text field without focusing any star, preserve the saved rating, and keep the rating group keyboard-accessible. Editing MUST preload the rating and text, enforce integer 1–10 and at most 1000 text characters, and MUST NOT send empty text to PUT. Text deletion MUST confirm preservation of rating and Vistas, leaving the card without text. Rating deletion MUST confirm the loss of rating, optional text and Vistas membership, removing the card on success only. Dialogs MUST contain keyboard focus, support Escape when idle and restore focus.

#### Scenario: A poster cannot load

- GIVEN an own rating with an unavailable poster
- WHEN its card renders
- THEN a same-size replacement appears without breaking the layout

#### Scenario: Deleting text from an own card

- WHEN the user confirms text deletion
- THEN the card keeps its rating and explains that no review text exists
- AND Vistas membership is unchanged

#### Scenario: Loading the next own-review page

- GIVEN more than 20 own ratings
- WHEN the UI follows the returned cursor without production filters
- THEN the API returns the remaining ratings as a paginated list, without duplicates
- AND only id_tmdb/tipo filters select the single-production response
