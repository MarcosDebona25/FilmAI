# reviews-api Specification

## Purpose

The user's own ratings and reviews (CU-015): publishing, editing and deleting a 1-10 rating with optional text, plus the reads the detail screen and "Mis reseñas" need. Covers C-08. Builds on `catalog-materialization`, whose `materializar()` it calls before writing, and completes two capabilities that shipped depending on ratings existing: the `Vistas` rule of `list-endpoints` (CU-011) and the review moderation of the Django Admin (CU-017).

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
- **List membership.** Rating a production does not add it to `Vistas`. Offering that is a decision for the detail screen, not a silent write into another module's tables.
- **`Calificacion.activa`.** This API always writes `True` and every read filters on it, so that moderating ratings later needs no change here.

## Known limitations

- Both paginated lists count their total with a `COUNT(*)` on every page request, inside `paginate_queryset()`. Fine at the current scale; if it ever hurts, the count belongs on the first page only.
- `Calificacion.fecha` is a `DateField`, so every rating from the same day ties; the cursor breaks the tie by descending id. An ordering closer to real time would need a `DateTimeField` and a migration.
