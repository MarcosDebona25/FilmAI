# Proposal: Initial Catalog Seed (C-04c, CU-021)

## Intent

C-04b keeps the catalog **fresh** but does not make it **grow**. The discovery
pass reads page 1 of four listing sources — about 60 productions a night, most
of which it has already seen. After a week the corpus is still in the low
hundreds, all of it recent and popular.

That is not enough for B-06. Semantic search answers from the rows in our own
database, so the corpus *is* the search space. A user asking for "una película
de culto de los 80 sobre paranoia" gets nothing useful from a corpus made of
this month's blockbusters, no matter how good the embedding model is.

C-04c populates that search space once: a management command that walks TMDB's
catalog along genre, decade and type, and materializes what it finds.

## Scope

### In Scope
- `catalogo/management/commands/seed_catalogo.py`: a resumable, rate-aware
  command that materializes productions in bulk
- Sampling across **genre × decade × type**, in rounds, so the corpus is diverse
  rather than a slice of this month's popularity
- `--limite` (how many to materialize, default 2 000), `--desde-anio`,
  `--tipos`, `--pausa` and `--dry-run`
- Progress reporting: the command runs for tens of minutes, so it must say
  where it is
- Resumability: re-running skips what is already stored and fresh, without
  re-requesting it from TMDB
- `get_genres(tipo)` on `TMDBClient` and `TMDBClientCache` (additive, same shape
  as the existing methods) + a `"genres"` TTL — genre ids must come from the API,
  not from a list copied into the source
- A guard on the existing `manage.py seed`, which deletes every
  `ProduccionAudiovisual` and would silently destroy a seeded catalog
- `README.md`, `docs/decisiones.md`, `docs/05_Plan_de_Desarrollo.md` updates
- Canonical spec `openspec/specs/catalog-seed/spec.md`

### Out of Scope
- **Changing `materializar()`**. The seed is a third caller of the same write
  path, exactly like the sync. If the seed needs something the helper does not
  do, that is a finding to discuss, not a reason to fork the write path.
- **Parallelism.** The obvious way to make 4 hours into 1 is to fan out across
  Celery workers. It is also the way to get rate-limited and to lose the single
  progress counter that makes the run legible. Revisit with real numbers.
- **Re-running the seed on a schedule.** This is a one-off; keeping the corpus
  current is C-04b's job.
- The real embedding provider — B-06 (Marcos). The seed will leave thousands of
  embeddings in `failed`, which the C-04b backfill picks up once the provider
  exists. That is by design, not an oversight.

## Success Criteria

1. `python manage.py seed_catalogo --limite 2000` materializes ~2 000 distinct
   productions and reports progress while doing it.
2. The resulting corpus spans **several decades and every genre**, and includes
   both films and series — verified by querying the database, not by assuming.
3. Every row goes through `materializar()`: it has genres, cast, directors and
   keywords, and a non-null `fecha_enriquecimiento`.
4. Interrupting the command (Ctrl-C, or the machine sleeping) and re-running it
   resumes: already-stored fresh rows cost no TMDB request.
5. Running it twice creates no duplicates.
6. The run survives a title TMDB cannot return: it is logged, counted, skipped.
7. `manage.py seed` can no longer wipe a populated catalog by accident.
8. Full backend suite and ruff stay green.
