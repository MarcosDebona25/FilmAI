# embedding-infrastructure Specification

## Purpose

Minimal Celery + pgvector plumbing that lets the catalog enqueue embedding work without blocking a request, with the actual provider left as a documented extension point. Advanced inside C-04a so that materialization has somewhere to enqueue to; the real provider (Ollama / `bge-m3`) and semantic retrieval are B-06.

## Requirements

### Requirement: Embedding lifecycle

The system MUST model an embedding's lifecycle as `pending → processing → ready | failed`. Semantic search MUST only consider `ready` rows; every other state MUST be invisible to the end user.

A production MUST remain visible in the catalog regardless of its embedding state. The embedding therefore lives in its own table, never as columns of `ProduccionAudiovisual`.

#### Scenario: Provider failure does not hide the production

- GIVEN the embedding provider fails for a production
- WHEN the task finishes
- THEN the embedding is `failed`
- AND the production is still served by the catalog endpoints

### Requirement: Database-level invariants

The system MUST enforce, in the schema and not only in Python:

- at most one embedding per production (`OneToOneField` ⇒ UNIQUE);
- `estado = "ready"` only with a non-null `vector`, via the `ck_embedding_ready_requiere_vector` check constraint;
- deletion of a production cascades to its embedding.

A `ready` row without a vector would count as done while being invisible to search, so no write path may produce one.

#### Scenario: Ready without a vector is rejected

- GIVEN an attempt to store `estado="ready"` with `vector=NULL`
- WHEN the write reaches the database
- THEN it is rejected with an integrity error

### Requirement: Canonical text and source hash

The system MUST build the embedded text from a fixed, ordered set of labelled sections: `Title`, `Genres`, `Directors`, `Cast`, `Keywords`, `Synopsis`. Labels are English and stable because the TMDB corpus is English and the target model was trained on such text; changing a label changes the hash of every production.

Array fields MUST be normalized — trimmed, empties dropped, sorted alphabetically — because TMDB does not guarantee a stable order between responses. Without this, identical content would produce different hashes and the system would regenerate embeddings forever.

The system MUST store the SHA-256 of that text as `source_hash` and the producing model as `model_version`, since vectors from different models are not comparable.

#### Scenario: Reordered arrays hash identically

- GIVEN two TMDB responses with the same genres in a different order
- WHEN the canonical text is built for each
- THEN both produce the same `source_hash`

### Requirement: Task idempotency

Celery guarantees at-least-once delivery, so `generar_embedding` MUST tolerate being delivered twice or to two workers at once. It MUST:

- no-op when the row is already `ready` with the same `source_hash` and `model_version`;
- claim the row with a conditional atomic `UPDATE` from `pending`/`failed` to `processing`, and no-op when that update affects zero rows;
- leave `ready` rows alone — a usable vector MUST NOT be downgraded because a provider is momentarily down.

#### Scenario: Two workers, one execution

- GIVEN two workers receive the same task simultaneously
- WHEN both attempt to claim the row
- THEN exactly one claim succeeds and the other returns without calling the provider

### Requirement: Provider call isolation

The call to the embedding provider MUST happen outside any open transaction: it may take seconds and must not hold a database connection or block other writers.

The task MUST NOT raise. Any provider failure MUST leave the row in `failed` and be logged. Propagating would make Celery retry in a loop and would add nothing, since the production stays visible either way.

#### Scenario: Provider error is contained

- GIVEN the provider raises any exception
- WHEN the task handles it
- THEN the row becomes `failed`
- AND no exception escapes the task
- AND the worker stays alive

### Requirement: Provider extension point

The system MUST isolate provider access in `catalogo.services.embeddings.generar_vector(texto)`. Until B-06 lands it MUST fail explicitly with `NotImplementedError` rather than returning a placeholder vector, so no meaningless data is ever stored.

Replacing that function MUST be sufficient to enable real embeddings: lifecycle, claiming, hashing, enqueueing and failure handling are already implemented and MUST NOT require changes.

#### Scenario: Stub keeps the pipeline honest

- GIVEN the provider is still the stub
- WHEN a production is materialized
- THEN its embedding ends in `failed` with a null vector
- AND no row is ever marked `ready`

### Requirement: Broker topology

The system MUST keep Celery's broker and result backend on Redis logical databases separate from the TMDB response cache, so that clearing one never destroys the other.

| Redis DB | Use |
|---|---|
| 0 | TMDB response cache |
| 1 | Celery broker |
| 2 | Celery results |

#### Scenario: Worker connects to its own database

- GIVEN the worker starts
- WHEN it connects to the broker
- THEN it uses Redis database 1, not the cache database
