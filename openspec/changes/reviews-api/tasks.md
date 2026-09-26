# Tasks: Ratings and Reviews API (C-08)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~600-700 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes — two |
| Suggested split | PR1 (write path) → PR2 (read path + docs) |
| Delivery strategy | ask-on-risk |
| Chain strategy | PR2 stacked on PR1 |

> Lesson from C-04c: reaim a stacked PR at `main` **before** deleting its base
> branch. Deleting the base closes the PR and it cannot be reopened.

### Suggested Work Units

| Unit | Goal | Likely PR | Est. lines | Focused test command | Rollback boundary |
|------|------|-----------|-----------:|----------------------|-------------------|
| 1 | POST / PUT / both DELETEs + exceptions | PR 1 | ~350 | `... test catalogo.tests_reviews.EscrituraTests` | Delete `reviews.py` and its routes; the models go back to being written by nobody |
| 2 | The three GETs + pagination + spec + docs | PR 2 | ~300 | `... test catalogo.tests_reviews.LecturaTests` | Remove the read routes; writing still works |

## Phase 1: The write path

- [ ] 1.1 Create `catalogo/tests_reviews.py`. The suite of `catalogo/tests.py`
      is at 2 950 lines and this adds ~500; a separate module keeps both
      navigable. Django's runner discovers any `test*.py`, so no wiring is
      needed — confirm with `python manage.py test catalogo` that the count
      grows
- [ ] 1.2 RED: `EscrituraTests` — `POST /api/reviews/` creates the rating,
      creates the `Resena` only when `texto` came, and answers 201 with the id
- [ ] 1.3 RED: validation — `valor` 0 and 11 reject, missing `valor` rejects,
      `texto` of 1001 chars rejects, unknown `tipo` rejects. Assert the status
      **and** which field the error names: the modal highlights fields
- [ ] 1.4 RED: a second `POST` for the same production answers 409 carrying
      `codigo` (the `UniqueConstraint` exists; the point is that the user sees
      a conflict, not a 500 from `IntegrityError`)
- [ ] 1.5 RED: `PUT` changes `valor`, changes `texto`, changes both, and adds
      `texto` to a rating that had none. `texto: ""` rejects — emptying text is
      the text `DELETE`, and accepting both would leave two ways to do it
- [ ] 1.6 RED: `DELETE /api/reviews/{id}/texto/` removes the `Resena` and
      leaves the `Calificacion`; `DELETE /api/reviews/{id}/` removes both
- [ ] 1.7 RED: ownership — another user's rating answers **404** (not 403) on
      `PUT` and on both `DELETE`s, matching L-01
- [ ] 1.8 RED: unauthenticated requests answer 401/403 on every verb
- [ ] 1.9 GREEN: `catalogo/exceptions.py` gains the conflict (reuse the
      `{codigo, detail}` envelope of `listas/exceptions.py`), `catalogo/reviews.py`
      the views, `filmai/urls.py` the routes
- [ ] 1.10 Integration: `POST` with `materializar()` real and TMDB faked — the
      production lands with genres, cast and a non-null `fecha_enriquecimiento`
      even though no detail view was opened
- [ ] 1.11 **Integration with L-01**, the reason this task is urgent: add to
      `Vistas`, rate, try to remove → 409 `calificacion_impide_quitar_de_vistas`;
      delete the rating → removal succeeds. Also assert deleting only the
      **text** still blocks removal: the rule keys on the rating
- [ ] 1.12 Full suite + `ruff format . && ruff check .`
- [ ] 1.13 Live smoke in Docker: rate a real TMDB id from `curl`/httpie, check
      the row and its production in `manage.py shell`

## Phase 2: The read path and the documents

- [ ] 2.1 RED: `LecturaTests` — `GET /api/reviews/?id_tmdb=&tipo=` returns the
      community's reviews with the fields §5c lists (avatar, `@usuario`,
      `valor`, fecha, texto) and the total count for the "Reseñas (N)" header
- [ ] 2.2 RED: that list excludes reviews without text, with `activa=False`,
      and the requester's own
- [ ] 2.3 RED: missing or malformed `id_tmdb`/`tipo` answers 400, consistent
      with `_int_param` of C-03
- [ ] 2.4 RED: `GET /api/reviews/mias/` returns the user's reviews newest
      first, **including** their moderated one, and never another user's
- [ ] 2.5 RED: `GET /api/reviews/mias/?id_tmdb=&tipo=` returns that single
      rating, and 404 when the user has not rated it
- [ ] 2.6 RED: cursor pagination — 20 per page, and a review inserted between
      two page requests does not make an item repeat or disappear
- [ ] 2.7 GREEN: views, serializers and `ResenaCursorPagination`
- [ ] 2.8 Create `openspec/specs/reviews-api/spec.md` (Given/When/Then, RFC 2119)
- [ ] 2.9 `docs/04_Lineamientos_UI.md`: fix §5c and §5d for the surviving
      rating — after deleting the text the "Tu reseña" card disappears but the
      action button shows the rating and opens the modal in edit mode. The
      wireframe's `confirmDelete()` hides the section and says nothing about
      the button; that is the gap being closed
- [ ] 2.10 `docs/05_Plan_de_Desarrollo.md`: C-08's backend done, its row
      corrected to include the three `GET`s, module 2 status, and P-06
      unblocked. `docs/decisiones.md`: the entry for 26/09/2026
- [ ] 2.11 Full suite + ruff; `graphify update .`; delete
      `openspec/changes/reviews-api/` per `AGENTS.md` §9

## Open question, for when the UI exists

Rating something does not add it to `Vistas` (out of scope, and the API should
not write another module's tables silently). But a user who rates a film has
plainly watched it, and CU-011's `Vistas` list is exactly that. Whether the
**frontend** offers "¿agregar a Vistas?" after rating is a C-07 decision, and
it needs the modal to exist before it can be judged.
