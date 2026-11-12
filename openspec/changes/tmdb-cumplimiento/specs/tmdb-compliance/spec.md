# tmdb-compliance Specification

## Purpose

What FilmAI does to meet TMDB's API terms of use (issue #180): attribution in a credits section, use of the official logo, a 6-month cap on stored TMDB content, a request rate TMDB tolerates, and the recorded basis for using TMDB content with the chatbot and embeddings. Sources in `docs/tmdb-legales/`. Builds on `catalog-materialization` (single write path), `catalog-daily-sync` (scheduled tasks), `tmdb-cache` (TTLs), `tmdb-client` (retries) and `chat-api` (stored cards).

## Requirements

### Requirement: Credits section with the exact notice

`/terms` MUST contain a section with `id="credits"` that shows, in both languages and both themes: the official TMDB logo as a link to `https://www.themoviedb.org`, and the notice «This product uses the TMDB API but is not endorsed or certified by TMDB.» (English, verbatim) or its approved Spanish translation. The footer MUST show the same notice and a link to `/terms#credits` built from `lib/routes.ts`.

#### Scenario: Visitor opens the credits

- GIVEN a visitor without a session, in Spanish
- WHEN they follow «Créditos» in the footer
- THEN `/terms` opens scrolled to the credits section
- AND they see the TMDB logo linking to `https://www.themoviedb.org` and the Spanish notice

#### Scenario: English notice is verbatim

- GIVEN the English catalog
- WHEN the credits section renders
- THEN the notice equals «This product uses the TMDB API but is not endorsed or certified by TMDB.»

### Requirement: The logo is official and unmodified

The logo MUST be one of the official files in `docs/tmdb-legales/`, copied byte for byte to `frontend/public/tmdb/`, and rendered as an image so no style can change its colors. Its aspect ratio MUST be preserved and it MUST NOT be rotated or flipped. It MUST be less prominent than FilmAI's mark (smaller than the footer wordmark, never in the header, the hero, the chat or next to a title) and MUST have a translated alternative text.

#### Scenario: The served file is the official one

- GIVEN the repository
- WHEN the test compares `frontend/public/tmdb/<logo>.svg` with its source in `docs/tmdb-legales/`
- THEN both files are identical

### Requirement: Only the approved names

Visible text, emails, chatbot prompts and documentation MUST name TMDB only as «TMDB» or «The Movie Database». Links to TMDB's site written by FilmAI MUST point to `https://www.themoviedb.org`; deep links returned by the TMDB API are passed through unchanged.

#### Scenario: A wrong spelling fails the check

- GIVEN a translation that says «TMDb»
- WHEN `npm run i18n:check` (or the naming test) runs
- THEN it fails naming the key

### Requirement: Catalog rows are refreshed before 6 months

A `ProduccionAudiovisual` row is due when `fecha_enriquecimiento` is NULL or older than `DIAS_REFRESCO_TMDB` (150) days. `catalogo.refrescar_vencidos` MUST run daily at 03:30, select due rows NULL first and then oldest first, up to `CELERY_REFRESCO_LIMIT`, and refresh each through `materializar(..., forzar=True)`. One failure MUST NOT stop the run. The run MUST log how many rows remain older than 180 days, as a warning when the number is not zero. Refreshing a row MUST rewrite its translations.

#### Scenario: Old and never-enriched rows are refreshed, fresh ones are not

- GIVEN a row enriched 160 days ago, a row with NULL `fecha_enriquecimiento` and a row enriched 10 days ago
- WHEN the task runs
- THEN the first two are materialized with `forzar=True`, the NULL one first
- AND the third is not touched

#### Scenario: The cap holds

- GIVEN 500 due rows and `CELERY_REFRESCO_LIMIT = 300`
- WHEN the task runs
- THEN exactly the 300 oldest are refreshed

### Requirement: Titles TMDB no longer has

When the refresh gets 404 (Not Found), a row no user references (ratings, reviews, list items) MUST be deleted. A referenced row MUST keep only `id_tmdb` and `tipo`, have every TMDB content field blanked (translations included), `disponible_en_tmdb = False`, `fecha_enriquecimiento` set to now, and its embedding removed. Only two 404 (Not Found) answers on different nights trigger it (the first one's date must be before today); any other error is retried. The delete MUST fail safe: `Calificacion`, `Resena` and `Tiene` protect the production, and a protected row becomes a tombstone instead. A tombstone that TMDB answers again with 200 (OK) MUST be restored. An unavailable title MUST NOT appear in recommendations, semantic search or the chatbot; in the user's lists and reviews it MUST appear as «Title no longer available», without a link, keeping the rating and review.

#### Scenario: A rated title disappears from TMDB

- GIVEN a production a user rated
- AND TMDB answers 404 (Not Found) for it
- WHEN the task refreshes it
- THEN the rating still exists
- AND the production has no title, synopsis or poster and is marked unavailable

#### Scenario: A single 404 (Not Found) is not enough

- GIVEN a production TMDB answers 404 (Not Found) for the first time
- WHEN the task refreshes it
- THEN the production keeps its content and is still available
- AND it is retried the next night

#### Scenario: A rating arrives while the row is being deleted

- GIVEN a production with no references and a second 404 (Not Found)
- AND a user rates it between the check and the delete
- WHEN the task deletes it
- THEN the delete fails because the rating protects the production
- AND the production becomes a tombstone and the rating still exists

#### Scenario: An unavailable title in the user's list

- GIVEN a production marked unavailable that a user has in a list and rated
- WHEN the user opens the list, My reviews, Recommended or asks the chatbot
- THEN the list and My reviews show «Title no longer available», without a link, with the rating and review
- AND Recommended, semantic search and the chatbot do not return it

#### Scenario: TMDB restores a title

- GIVEN a production marked unavailable
- AND TMDB answers 200 (OK) for it again
- WHEN the task refreshes it
- THEN its content is filled in and it is available again

### Requirement: Chat cards keep TMDB content for at most 6 months

`chatbot.recortar_tarjetas` MUST run daily and reduce every card of a message older than 180 days to `{id_tmdb, tipo}`, and every `ya_recomendados` entry whose `fecha` is older than 180 days (or missing) to `{id_tmdb, tipo, fecha}`. The history endpoint MUST rehydrate trimmed cards from the local catalog in the reader's language without calling TMDB; a production missing or unavailable yields `titulo: null`.

#### Scenario: An old conversation is read

- GIVEN a message from 200 days ago whose cards were trimmed
- WHEN the user loads the history in English
- THEN each card shows the current English title and poster from `ProduccionAudiovisual`
- AND no TMDB request is made

#### Scenario: A recent conversation is untouched

- GIVEN a message from 30 days ago
- WHEN the trimming task runs
- THEN its cards keep `titulo`, `poster` and `anio` as they were shown

### Requirement: Caches stay under 6 months

Every TTL in `ENDPOINT_TTLS`, `RESPALDO_TTL` and `RESPALDO_TTLS`, and every `max-age` the catalog API sends, MUST be at most 180 days.

#### Scenario: A TTL above the cap fails

- GIVEN someone sets a TTL of 200 days
- WHEN the test suite runs
- THEN the cache cap test fails naming the endpoint

### Requirement: Respectful API use

All TMDB requests MUST go through `catalogo/client.py`, which retries 429 (Too Many Requests) honoring `Retry-After`. The measured peak rate of the seed, the nightly tasks and `rellenar_traducciones` MUST be recorded in doc 06 and stay under 40 requests per second. TMDB image URLs MUST only be used to show catalog content, never as decorative or promotional graphics.

#### Scenario: The refresh task honors 429

- GIVEN TMDB answers 429 with `Retry-After: 2` and then 200 (OK)
- WHEN the refresh task materializes that row
- THEN the client waits at least 2 seconds and the row is refreshed

### Requirement: Recorded basis for AI use

`docs/decisiones.md` MUST record that TMDB content is used with the chatbot and embeddings on the basis that FilmAI is an academic, non-profit project (07/11/2026), that any revenue tied to TMDB content (ads, subscriptions, paid tiers) requires talking to TMDB first, and the exceptions accepted by issue #180 (access collage until 13/02/2027, test fixtures).
