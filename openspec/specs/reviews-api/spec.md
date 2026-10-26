# reviews-api Specification

## Purpose

The user's own ratings and reviews (CU-015): publishing, editing and deleting a 1-10 rating with optional text, plus the reads the detail screen and "Mis reseñas" need. Covers C-08. Builds on `catalog-materialization`, whose `materializar()` it calls before writing, and completes two capabilities that shipped depending on ratings existing: the `Vistas` rule of `list-endpoints` (CU-011, completed on 30/09/2026 by "a rated production is in `Vistas`") and the review moderation of the Django Admin (CU-017).

## Requirements

### Requirement: The rating is the resource, the text hangs off it

A rating (1-10) is required; its text is optional and at most 1000 characters. The API MUST expose the pair as one resource under `/api/reviews/`, and the `{id}` in every path MUST be the `Calificacion` primary key, because the rating is what always exists.

A user MUST NOT rate the same production twice. A second attempt MUST answer 409 with a stable `code`, not a 500 from the database constraint.

#### Scenario: Rating without text

- GIVEN an authenticated user who has not rated a production
- WHEN they POST a rating with no text
- THEN the rating is stored
- AND no review row is created
- AND the response carries the rating's id

#### Scenario: Rating the same production twice

- GIVEN a user who already rated a production
- WHEN they POST another rating for it
- THEN the response is 409 with `code: "rating_duplicated"`
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

#### Scenario: An `id_tmdb` beyond the column range

- GIVEN a payload whose `id_tmdb` is greater than 2147483647 (the maximum of a Postgres `integer`)
- WHEN it is posted, or used as a read filter
- THEN the response is 400 (Bad Request) with `max_value` on `id_tmdb`
- AND no TMDB request is issued (security audit F7, 24/10/2026)

#### Scenario: An `id_tmdb` that TMDB does not know

- GIVEN TMDB answers 404 (Not Found) for the posted `id_tmdb`
- WHEN it is posted
- THEN the response is 404 (Not Found) with `upstream_not_found`
- AND neither a rating nor a production row is left in the database

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

`GET /api/reviews/?id_tmdb=&tipo=` MUST return the reviews other users wrote about that production, cursor-paginated at 20, with the author's username and avatar, the rating, the date and the text. Since 14/10/2026 (C-07) reading is public: it MUST answer without a session; writing still requires one.

It MUST exclude three populations: ratings without text (there is nothing to read), moderated reviews, and — when there is a session — the requester's own, which the detail screen renders separately, above the list.

`orden` MUST accept `fecha-desc` (default), `fecha-asc`, `nota-desc` and `nota-asc`; `nota_min` and `nota_max` MUST filter by rating, inclusively, with integers from 1 to 10. Anything else MUST answer 400 naming the field. Following `next` MUST never repeat or skip a review, even when many share the same rating.

The response MUST carry a `total` with the filtered count, which cursor pagination does not provide on its own, and a `total_comunidad` with the unfiltered count, for «From the community (N)» and «Showing X of N».

Both query parameters are required; either one missing or malformed MUST answer 400. A production with no reviews MUST answer 200 with an empty list, not 404.

#### Scenario: The requester's own review is not in the list

- GIVEN a production reviewed by the requester and by another user
- WHEN the community list is requested
- THEN only the other user's review is returned
- AND `total` is 1

#### Scenario: Anonymous reader with a filter

- GIVEN four reviews rated 3, 6, 8 and 10 and no session
- WHEN the list is requested with `nota_min=8`
- THEN the reviews rated 8 and 10 are returned, newest first
- AND `total` is 2 and `total_comunidad` is 4

#### Scenario: Sorting by rating over many ties

- GIVEN 25 reviews rated 8 and 5 rated 9
- WHEN the list is followed page by page with `orden=nota-desc`
- THEN the 30 reviews arrive once each, the 9s first

#### Scenario: A deactivated author's review is anonymous (26/10/2026)

- GIVEN a review whose author's account was deactivated (`estado = baja`)
- WHEN the community reviews of that production are read
- THEN the review is listed with its rating, date and text
- AND `nombre_usuario` and `avatar_id` are `null` and `autor_dado_de_baja` is `true`
- AND the frontend shows «Usuario dado de baja» / «Deleted account» instead of the username

#### Scenario: A moderated review is hidden

- GIVEN a review with `activa = False`
- WHEN any other user requests the community list
- THEN that review does not appear

### Requirement: The user's own reviews

`GET /api/reviews/mias/` MUST return every rating of the authenticated user, newest first, cursor-paginated at 20, each with the production's title, type and poster so the row can navigate to its detail screen.

Since 15/10/2026 (profile per the canvas) the list MUST accept, all optional and combinable: `q` (up to 100 characters, trimmed, matching the canonical title or any translation, case- and accent-insensitive through Postgres `unaccent`), `texto` (`con` | `sin`: with or without review), `clase` (`movie` | `tv`; not `tipo`, which selects the single-rating response), `nota_min` / `nota_max` (1–10, inclusive) and `orden` (`fecha-desc` by default, `fecha-asc`, `nota-desc`, `nota-asc`; the rating sorts use the unique key `valor × 10⁹ + id` so the cursor never repeats or skips ties). Invalid values MUST answer 400 naming the field. The page MUST carry `total` (with the filters) and `total_propias` (without them).

#### Scenario: Accent-insensitive search

- GIVEN the user rated «Amélie»
- WHEN they ask `reviews/mias/?q=AMELIE`
- THEN the list holds only «Amélie», with `total` 1 and `total_propias` counting all their ratings

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

### Requirement: Only production filters select the single-rating response

`GET /api/reviews/mias/` answers a paginated list unless the request carries `id_tmdb` or `tipo`. Any other query parameter, the pagination `cursor` included, MUST NOT switch it to the single-rating response: following a `next` link must keep returning list pages. (Found by P-06 on 03/10/2026: the second page answered 400 because every parameter was read as a production filter.)

#### Scenario: Loading the next own-review page

- GIVEN more than 20 own ratings
- WHEN the client follows the returned cursor without production filters
- THEN the API returns the remaining ratings as a paginated list, without duplicates
- AND only `id_tmdb`/`tipo` select the single-production response

### Requirement: A rated production is in `Vistas`

Every rating's production MUST be in its author's predetermined `Vistas` list (decided 30/09/2026: "if you rated it, you watched it"). CU-011 already enforced one half — a rated production cannot leave `Vistas` without confirming the rating's deletion. This requirement adds the other:

- `POST /api/reviews/` MUST add the production to `Vistas` when it is not there, **in the same transaction** as the rating. If it cannot be added, the rating MUST NOT be stored. Entering `Vistas` this way also removes it from the author's `Pendientes` (`list-endpoints`, 14/10/2026).
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
- THEN the response is 409 with `code: "rating_blocks_removal_from_watched"`
- AND nothing is deleted

## What this capability does not touch

- **`calificacion_promedio`** holds TMDB's `vote_average`, not the average of our users' ratings. It is never recomputed here; three screens display it as "rating TMDB".
- **Embeddings.** The canonical text is `Title + Genres + Directors + Cast + Keywords + Synopsis`; a rating changes none of it, so nothing is re-enqueued.
- **Other lists.** Only `Vistas` follows the rating. `Favoritos`, `Pendientes` and custom lists never change when a rating is created or deleted.
- **`Calificacion.activa`.** This API always writes `True` and every read filters on it, so that moderating ratings later needs no change here.

## Known limitations

- Both paginated lists count their total with a `COUNT(*)` on every page request, inside `paginate_queryset()`. Fine at the current scale; if it ever hurts, the count belongs on the first page only.
- `Calificacion.fecha` is a `DateField`, so every rating from the same day ties; the cursor breaks the tie by descending id. An ordering closer to real time would need a `DateTimeField` and a migration.

### Requirement: Account deactivation preserves community reviews

Logical account deactivation MUST preserve existing active ratings and reviews.
The community endpoint continues to expose their text, rating and author's
username to other users, as established by the current account lifecycle.

#### Scenario: An author deactivates their account

- GIVEN an active rating with an active review
- WHEN its author successfully calls `POST /api/account/deactivate/`
- THEN the account is in state `baja`
- AND another authenticated user still sees the review text, rating and username
  through `GET /api/reviews/?id_tmdb=...&tipo=...`

### Definitive error contract

Errors expose only `code`, `params`, `errors` and conditional development `debug`. Previous `codigo`, `detail` and root field keys are removed. Rating duplication uses `rating_duplicated`; removal from the watched list uses `rating_blocks_removal_from_watched`. The frontend displays localized messages and marks fallback English titles with `lang="en"`.
