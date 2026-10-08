# List endpoints

## Purpose

Authenticated users manage only their own lists and the productions contained
in them through `/api/lists/`.

## Requirements

### Stable identity of existing predetermined lists

`Lista.clave` MUST support `favoritos`, `pendientes`, and `vistas`, and MUST
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

When `id_tmdb` and `tipo` (`movie` or `tv`) are supplied together, every list
MUST also include `contiene` and, when true, `item_id`. Supplying only one of
those parameters MUST return 400 and the lookup MUST NOT materialize data.

### List management

`POST /api/lists/` MUST create a personalized list for the authenticated user.
`PUT /api/lists/{id}/` MUST rename only personalized lists. `DELETE
/api/lists/{id}/` MUST permanently delete only personalized lists and their
items.

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
addition date, and the production fields needed by a MediaCard.

`POST /api/lists/{id}/items/` MUST accept `(id_tmdb, tipo)`, call
`materializar()` before creating `Tiene`, and reject an existing relation with
409. `DELETE /api/lists/{id}/items/{item_id}/` MUST remove only an item owned
by that list. Removing from the predetermined `Vistas` list while an active
rating exists for that production MUST return 409.

`Vistas` also changes from outside this API: since 30/09/2026, rating a
production adds it to its author's `Vistas` and deleting the rating removes it
(`reviews-api`, "A rated production is in `Vistas`"). Those writes go through
`listas/services.py` (`agregar_a_vistas`, `quitar_de_vistas`) so that the lists
module keeps owning `Tiene`.

### Errors and ownership

All endpoints MUST require authentication. A list or item belonging to another
user MUST appear as 404. Business conflicts MUST expose a stable `codigo` and a
human-readable `detail`.
