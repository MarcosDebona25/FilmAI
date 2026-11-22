# seed-masivo Specification

## Purpose

Populate the development database at scale (hundreds of fictitious accounts,
thousands of ratings and reviews) on top of the TMDB catalog that `seed_catalogo`
already built, so lists, moderation, search and the chatbot can be exercised with
realistic volume. Review texts come from a versioned corpus written by a model.
`seed` and `seed --solo-resenas` (see `development-seed`) are unchanged.

## Requirements

### Requirement: Accounts are created in bulk and idempotently

`python manage.py seed_masivo` MUST create `usuario001`..`usuario003@filmai.com`
(languages `es`, `en`, `es`) and `masivo0001`..`masivoNNNN@filmai.com`
(`--usuarios`, default 500) with the password `Password123!`, accepted Terms
(`fecha_aceptacion_terminos`), a verified primary `EmailAddress` and languages
split about 50/50 between `es` and `en`. It MUST hash the password once and reuse
the hash. About 3 percent of the `masivo` accounts MUST be unverified
(`EstadoCuenta.PENDIENTE`, `EmailAddress.verified=False`) or deactivated
(`EstadoCuenta.BAJA`); only active accounts get ratings, lists items and chat
messages. Every account MUST get the four default lists (`favoritos`,
`pendientes`, `viendo`, `vistas`, same names and keys as
`provisioning.provisionar_recursos_por_defecto`) and the default chat, created by
hand because `bulk_create` does not fire the `post_save` signal.

Without `--reiniciar` the command MUST NOT delete anything and MUST create only
the accounts whose email does not exist yet.

#### Scenario: Run twice

- GIVEN an empty database with a catalog of at least 20 productions
- WHEN `seed_masivo --usuarios 20` runs twice
- THEN there are 23 non-staff accounts and the counts of ratings and reviews are
  the same after the second run

### Requirement: Reset keeps staff and catalog

`--reiniciar` MUST delete every non-staff user with its `EmailAddress`,
`SocialAccount`, ratings, reviews, lists, list items, chats and messages. It MUST
keep staff users (with their lists and chat) and the whole catalog.

#### Scenario: Reset with a staff user present

- GIVEN a staff user, another non-staff user and a catalog
- WHEN `seed_masivo --reiniciar` runs
- THEN the staff user and the catalog are intact and the other user is gone

### Requirement: Activity is coherent and long-tailed

Each active account MUST have a taste profile (2 to 4 genres taken from the real
catalog). The number of ratings per account MUST follow a long-tailed
distribution (log-normal) with mean about `--calificaciones-medias` (default 38),
minimum 3 and maximum 300. Titles are drawn weighted by popularity and genre
affinity; the value is an integer from 1 to 10 close to `calificacion_promedio`
with noise; (user, production) is unique. The catalog MUST have at least 20
productions with a TMDB poster path, otherwise the command aborts before writing.

The seed MUST keep these invariants: a rated title is in `Vistas`; `Favoritos`
holds only titles rated 9 or more; a title has one state (`pendientes`,
`viendo`, `vistas`) per user; `Pendientes` and `Viendo` hold no rated title. Part
of the accounts MUST have two custom lists with a genre theme.

#### Scenario: Invariants after a run

- WHEN the command runs on a test catalog
- THEN every rating's production is in its user's `Vistas`
- AND every `Favoritos` item has a rating of 9 or more
- AND no production is in two state lists of the same user

### Requirement: Reviews come from the corpus with template fallback

Exactly `--porcentaje-resenas` percent (default 80, rounded) of the ratings MUST
get a `Resena`. The text MUST be one of the corpus texts for
(`id_tmdb`, `tipo`, account language, band of the rating), chosen with the seed.
Bands: 1 to 4 `baja`, 5 to 7 `media`, 8 to 10 `alta`. With no corpus entry, or an
empty one, the text MUST come from `backend/seed_data/plantillas_genero.json`
(one of the title's genres, chosen at random, for that language and band) and,
if the file is missing or none of the title's genres is in it, from
`seed_real.TEXTOS`.
Every seventh review created MUST have `activa=False` (`development-seed`,
moderation examples).

#### Scenario: No corpus file

- GIVEN `backend/seed_data/resenas.jsonl.gz` does not exist
- WHEN the command runs
- THEN every review text is one of the genre templates or, failing that, one of the `seed_real.TEXTOS` templates

### Requirement: Light chat history

A subset of the active accounts (about a quarter) MUST get 2 to 6 alternating
messages in their default chat, in the account language.

### Requirement: Deterministic and atomic

With the same `--semilla` (default 42), arguments and catalog, the run MUST
produce the same ratings and reviews. Each account uses its own generator, so its
activity does not depend on which other accounts exist. The run MUST happen in a
single transaction, print progress and finish with a summary of counts.

### Requirement: The corpus is a versioned, deterministic file

The corpus MUST be `backend/seed_data/resenas.jsonl.gz`: one JSON line per
(production, language, band), `{"id_tmdb": int, "tipo": "movie"|"tv", "idioma":
"es"|"en", "banda": "baja"|"media"|"alta", "textos": [str, ...]}`, with two
texts per entry, sorted by (`id_tmdb`, `tipo`, `idioma`, `banda`) and gzipped with
`mtime=0` so recompiling the same content gives the same bytes.

`preparar_corpus_resenas --top N --lote 25 --salida DIR [--omitir-existentes]`
MUST write `DIR/entrada_NNNN.json` batches with the N most voted productions that
are not yet fully in the corpus (six entries), each as `{id_tmdb, tipo, titulo,
anio, generos, sinopsis}` with the synopsis cut to about 300 characters. It only
reads the database and MUST NOT write TMDB data in the repository. The model has
no vote count field, so by default titles come in insertion order (`pk`). With
`--por-votos PAGES` the command MUST rank titles by TMDB `discover` sorted by
`vote_count.desc` (PAGES of movies and a third of that for series, three movies
per series) and keep only those present in the database, in that order;
unavailable, poster-less and synopsis-less productions are skipped.

`compilar_corpus_resenas DIR` MUST read `DIR/salida_*.jsonl`, discard and report
invalid lines, merge the valid ones into the existing corpus (new entries replace
old ones by key), rewrite it deterministically and report valid, invalid and
total counts. A line is valid when it has all fields, `idioma` in `es`/`en`,
`banda` in the three bands, `tipo` in `movie`/`tv`, at least two non-empty texts
of 20 to 400 characters and no exact duplicates inside the entry.

#### Scenario: Compile mixed output

- GIVEN an output file with one valid line and several lines with a bad language,
  a short text or duplicated texts
- WHEN `compilar_corpus_resenas` runs
- THEN only the valid line enters the corpus and the invalid ones are reported
