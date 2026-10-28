# semantic-search Specification

## Purpose

Conceptual search over the local catalog («algo melancólico sobre viajes en el tiempo»), which TMDB's `discover` cannot express. Completes B-06 on top of `embedding-infrastructure`: real vectors from BGE-M3 through Ollama, and a query over pgvector with SQL filters. The chatbot's `buscar_semantico` tool is its first consumer. Decisions of 18/08/2026 and 28/10/2026.

## Requirements

### Requirement: Real vectors from Ollama

`generar_vector(texto, *, timeout, reintentos)` MUST call Ollama's `/api/embed` at `OLLAMA_URL` with model `bge-m3` and return a list of 1024 floats. It MUST retry transient failures (connection errors, timeouts, 5xx) up to `reintentos` times and then raise `EmbeddingProviderError`. The backfill MUST use 10 s and 2 retries; a chat query (`buscar_semantico`) MUST use 3 s and no retry, so a hung Ollama costs a chat turn at most 3 s. `MODEL_VERSION` MUST be `"bge-m3"`, so every vector produced by the stub is considered stale.

#### Scenario: Successful embedding

- GIVEN Ollama answers with one 1024-dimension vector
- WHEN `generar_vector("Title: Moon …")` runs
- THEN it returns that vector
- AND the request asked for model `bge-m3` with a `keep_alive`

#### Scenario: Ollama down during the backfill

- GIVEN Ollama refuses the connection three times
- WHEN the backfill calls `generar_vector`
- THEN it tried three times and raises `EmbeddingProviderError`
- AND the embedding row is marked `failed`, as the backfill already handles

#### Scenario: Ollama hung during a chat query

- GIVEN Ollama accepts the connection and never answers
- WHEN `buscar_semantico` embeds the query
- THEN it gives up after 3 s, without retrying, and raises `EmbeddingProviderError`

#### Scenario: Unexpected dimension

- GIVEN Ollama returns a vector of 768 floats
- WHEN `generar_vector` runs
- THEN it raises `EmbeddingProviderError` instead of storing a vector the column cannot compare

### Requirement: Query by meaning with filters after retrieval

`buscar_semantico(consulta, *, tipo=None, anio_desde=None, anio_hasta=None, nota_minima=None, duracion_max=None, excluir=())` MUST embed the query, rank `ready` embeddings by cosine distance, take the 50 nearest, apply the filters in SQL, drop the `(id_tmdb, tipo)` pairs in `excluir`, and return at most 10 productions in ranking order. Quantitative fields MUST NOT be part of the embedded text (18/08/2026).

#### Scenario: Filters after the vector

- GIVEN *Paddington 2* (Family) and *About Time* (Romance) both among the nearest to «algo liviano para ver con chicos»
- WHEN the search runs with a filter that keeps only the Family genre
- THEN *Paddington 2* is returned and *About Time* is not

#### Scenario: Excluding watched titles

- GIVEN *Moon* is the nearest result
- WHEN the search runs with `excluir={(17431, "movie")}`
- THEN *Moon* is not returned

#### Scenario: Only ready vectors

- GIVEN a production whose embedding is `pending` or `failed`
- WHEN any search runs
- THEN that production is never returned

#### Scenario: Provider failure during a query

- GIVEN Ollama is down
- WHEN `buscar_semantico` runs
- THEN it raises `EmbeddingProviderError` and returns nothing partial

### Requirement: Reachable from containers in every setup

The backend and the Celery worker MUST read the Ollama address from `OLLAMA_URL`. The compose file MUST offer two optional profiles: `ollama-windows`, a bridge that forwards from the Docker network to an Ollama running on the Windows host, and `ollama`, a containerized Ollama with a memory limit. Neither profile MUST start by default.

#### Scenario: Developer with Ollama for Windows

- GIVEN Ollama for Windows with `bge-m3`, WSL in mirrored networking, and the `ollama-windows` profile up
- WHEN the backend container calls `OLLAMA_URL=http://host.docker.internal:11435`
- THEN the request reaches the Windows Ollama
- AND Ollama is not exposed to the local network
