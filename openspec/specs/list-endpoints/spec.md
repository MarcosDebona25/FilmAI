# List endpoints

## Purpose

Authenticated users manage only their own lists and the productions contained
in them through `/api/lists/`.

## Requirements

### Stable identity of existing predetermined lists

`Lista.clave` MUST support `favoritos`, `pendientes`, `viendo` (16/11/2026) and `vistas`, and MUST
remain nullable during the migration of application code to these identities.
The existing `nombre`, list IDs, and `Tiene` relations MUST be preserved.

Migration `listas.0005_lista_clave` MUST assign each existing predetermined
list its key from `Lower(nombre)`. Personalized lists MUST remain without a
key, including those whose names match a predetermined name.
An unknown predetermined name MUST stop the migration explicitly and roll
back its schema and data changes. Reversing the migration MUST clear keys
before removing the column, while preserving lists and items.

### Runtime identity and provisioning

Provisioning, presentation order, rating membership and removal guards MUST
identify predetermined lists by `clave`, independently of `nombre`.
Provisioning MUST preserve renamed lists and their IDs. During the nullable
transition it MAY locate a missing-key resource by its legacy name, without
recreating it or changing its name. A conflicting type or identity MUST fail.
The development seed and repair audit MUST use these same identities.

### Summary and membership

`GET /api/lists/` MUST return active lists belonging to the authenticated user.
Each list MUST include its ID, name, type, nullable `clave`, `cantidad_items`,
`cantidad_peliculas`, `cantidad_series`, and up to five recent non-empty poster
paths in `preview_posters`.
Personalized lists MUST expose `clave = null`. Predetermined summaries MUST
be ordered by `favoritos`, `pendientes`, `vistas`, even after a stored rename.
Personalized summaries MUST follow them, ordered by `Lista.orden` and then by ID.

`GET /api/lists/{id}/` MUST return the same summary for a single owned list,
predetermined or personalized (L-03 header and the title page breadcrumb
`?from=list-{id}`).

When `id_tmdb` and `tipo` (`movie` or `tv`) are supplied together, every list
MUST also include `contiene` and, when true, `item_id`. Supplying only one of
those parameters MUST return 400 and the lookup MUST NOT materialize data.

### List management

`POST /api/lists/` MUST create a personalized list for the authenticated user.
`PUT /api/lists/{id}/` MUST rename only personalized lists. `DELETE
/api/lists/{id}/` MUST permanently delete only personalized lists and their
items.

A new personalized list MUST be placed after the existing ones.

`PUT /api/lists/order/` MUST accept `{"ids": [...]}`, the personalized lists in
their new order (L-02, decided 15/10/2026), and return all summaries as
`GET /api/lists/`. IDs that are not one of the user's personalized lists MUST be
ignored, and personalized lists left out MUST keep their previous relative
order after the listed ones, so a stale tab cannot fail the request. Repeated
or non-positive IDs MUST return 400 on field `ids`.

#### Scenario: Reordering with a stale tab

- GIVEN personalized lists A, B, C, and a tab that only knows A and C
- WHEN it sends `{"ids": [C, A]}`
- THEN the order is C, A, B and the predetermined lists stay first

Names MUST be unique per user without case sensitivity, be at most 80
characters, and allow Unicode letters, numbers, and spaces.
Predetermined lists MUST reject rename and deletion with a 409 conflict.
Creating or renaming a personalized list MUST reject a reserved label from
any supported language, after whitespace normalization and without case
sensitivity, with `list_name_reserved`, HTTP 409 and empty params.
The reserved labels MUST match the approved default-list catalog labels.
Existing personalized names MUST be returned unchanged, without translation.

`contracts/enums.json` MUST publish `defaultListKeys`, `genderValues` and
`reservedListNames` by language. The export command MUST reproduce the file
from model values and the backend reservation registry.

### Items

`GET /api/lists/{id}/items/` MUST use cursor pagination of 20 items ordered by
most recent `fecha_agregado` first. Each item MUST include its `item_id`,
addition date, and the production fields needed by a MediaCard, including the
TMDB average as `calificacion_promedio` (`null` when TMDB has no rating, which
it reports as 0). The response MUST include `total`, the count of items that
pass the filters.

The endpoint MUST accept the L-03 filters, validated with 400 on the offending
field: `q` (up to 100 characters; matches the canonical or a translated title
without case or accents), `clase` (`movie` or `tv`), `nota` (the Search
buckets `9+`…`5+` and `m5`, over the TMDB average) and `orden`
(`agregado-desc` by default, `agregado-asc`, `titulo-asc`, `nota-desc`,
`nota-asc`). Rating buckets MUST exclude unrated productions, and rating orders
MUST place them last in both directions (decided 15/10/2026). `titulo-asc`
MUST sort by the title shown in the effective language. Every order MUST keep
the cursor stable across ties.

`POST /api/lists/{id}/items/` MUST accept `(id_tmdb, tipo)`, call
`materializar()` before creating `Tiene`, and reject an existing relation with
409. `DELETE /api/lists/{id}/items/{item_id}/` MUST remove only an item owned
by that list, and always answers 204 (No Content): since 16/11/2026 a rating no
longer blocks removal from `Vistas` and it is kept. A `?borrar_calificacion=`
flag sent by an old client is ignored.

### One status per production (16/11/2026)

`Pendientes` (Watchlist), `Viendo` (Watching) and `Vistas` (Watched) are a
single status: a production MUST be in at most one of them for the same user.
`Favoritos` stays independent. Every write into those three lists goes through
`listas/services.py::poner_estado(usuario, produccion, estado)`, which locks the
three lists, puts the production in the requested one and removes it from the
other two in one transaction. It is used by `POST /api/lists/{id}/items/` on
those lists, by rating (`reviews-api`) and by the status endpoint.
`quitar_de_vistas` remains only for deleting a rating.

`PUT /api/lists/status/` sets the status atomically and is also the Undo:
body `{id_tmdb, tipo, estado}` with `estado` in `pendientes`, `viendo`, `vistas`
or `null` (required even when `null`, so a missing key never clears the status).
It answers 200 (OK) with `{estado, estado_anterior, listas}`, where `listas` is
the same array as `GET /api/lists/?id_tmdb=&tipo=`. Repeating the current status
is idempotent and keeps the item's date. The production is materialized only
when `estado` is not `null`. Errors: 400 (Bad Request) for an invalid body,
401 (Unauthorized), 404 (Not Found) if TMDB does not know the title, and the
write throttle. The client undoes a change by sending `estado_anterior`.

Migration `listas.0009_lista_viendo` creates `Viendo` in every account, moves
every active rating with no status to `Vistas`, and keeps only the most recent
list (`fecha_agregado`, `Vistas` on a tie) for a production in both `Pendientes`
and `Vistas`. A custom list already named «Viendo» is renamed to «Viendo 2» (or
the first free number) and keeps its items. «Watching» and «Viendo» become
reserved names. The reverse is a documented no-op.

`Viendo` is treated as already seen by `vistos()`: it is excluded from the Home
«Recommended» row, from list suggestions, from «More like» on the title page and
from the chatbot's recommendations, and the chatbot context lists it in its own
line. List suggestions answer 404 (Not Found) for `Pendientes` and `Viendo`.

#### Scenario: Marking as watched something pending

- GIVEN a production in the user's `Pendientes`
- WHEN they add it to `Vistas`, or rate it
- THEN it is in `Vistas` and no longer in `Pendientes`

#### Scenario: The status is free after rating

- GIVEN a rated production in `Vistas`
- WHEN the user sets its status to `Viendo`
- THEN it is only in `Viendo`
- AND the rating is kept

#### Scenario: Undo

- GIVEN a production in `Pendientes`
- WHEN the status is set to `Viendo` and then to the returned `estado_anterior`
- THEN it is back in `Pendientes` only

### Write limits and quantity caps (26/10/2026)

Every write of reviews, lists and profile MUST share one per-user rate limit (`EscrituraThrottle`, scope `escritura`, 60 per minute); reads (`GET`, `HEAD`, `OPTIONS`) do not count. Past it the answer is 429 (Too Many Requests) with `throttled`. A user MUST NOT own more than 100 custom lists (`MAX_LISTAS_PERSONALIZADAS`): the next creation answers 409 with `list_limit_reached` and `maxLists`. A custom list MUST NOT hold more than 1000 items (`MAX_ITEMS_POR_LISTA`): the next addition answers 409 with `list_items_limit_reached` and `maxItems`, before materializing anything. Default lists have no item cap, because `Vistas` grows when the user rates. `PUT /api/lists/order/` rejects more than 100 ids with 400 `max_length`.

#### Scenario: Creating one list too many

- GIVEN a user with 100 custom lists
- WHEN they create another
- THEN the answer is 409 with `list_limit_reached` and `maxLists` = 100

#### Scenario: Rating keeps working with a large «Vistas»

- GIVEN a `Vistas` list with more than 1000 items
- WHEN the user adds or rates another title
- THEN the item is added

### Errors and ownership

All endpoints MUST require authentication. A list or item belonging to another
user MUST appear as 404. Business conflicts MUST expose a stable `code` and the common error envelope, without interface text.

### Definitive error contract

OT-83 removes public `codigo`, `detail` and root field keys. Use `list_name_duplicated`, `list_name_reserved`, `list_item_duplicated`, `list_limit_reached`, `list_items_limit_reached` and `default_list_protected`, with the common error envelope. Request fields and enum values retain their spelling. Frontend labels for default lists use the exported stable keys.
