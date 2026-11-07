# semantic-search Specification

## Purpose

Conceptual search over the local catalog («algo melancólico sobre viajes en el tiempo»), which TMDB's `discover` cannot express. Completes B-06 on top of `embedding-infrastructure`: real vectors from BGE-M3 through Ollama, a query over pgvector with SQL filters, and an early model load so the first chat question does not pay for it. The chatbot's `buscar_semantico` tool is its first consumer. Decisions of 18/08, 28/10, 04/11 and 05/11/2026 in `docs/decisiones.md`.

Code: `catalogo/services/embeddings.py` (`generar_vector`, `modelo_cargado`), `catalogo/services/semantica.py` (`buscar_semantico`, `pedir_carga_del_modelo`), `catalogo/tasks.py` (`calentar_modelo`), `chatbot/views.py` (`PrepararChatView`). Tests: `catalogo/tests_semantica.py`, `chatbot/tests_preparar.py`.

## Requirements

### Requirement: Real vectors from Ollama

`generar_vector(texto, *, timeout=10, reintentos=2)` MUST call Ollama's `/api/embed` at `OLLAMA_URL` with model `bge-m3`, the text, and `keep_alive` taken from `OLLAMA_KEEP_ALIVE` (default `30m`; it MUST be a duration, since `-1` as text is a 400 (Bad Request)). It MUST return the first vector of the response, which MUST have 1024 floats.

It MUST retry only transient failures (connection errors, timeouts, 5xx) up to `reintentos` times, with no pause between attempts, and then raise `EmbeddingProviderError`. A 4xx or a response without a usable vector MUST fail at once, because insisting does not fix it. The backfill MUST use the defaults (10 s and 2 retries). `MODEL_VERSION` MUST be `"bge-m3"`, so every vector produced before B-06 is considered stale and the backfill regenerates it.

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

#### Scenario: Unexpected dimension

- GIVEN Ollama returns a vector of 768 floats
- WHEN `generar_vector` runs
- THEN it raises `EmbeddingProviderError` instead of storing a vector the column cannot compare

### Requirement: A chat query waits only for a model that is loading

Before embedding a chat query, `buscar_semantico` MUST call `modelo_cargado()`, which asks Ollama's `/api/ps` with a 1 s timeout and accepts `bge-m3` or `bge-m3:latest` as the loaded model. If `/api/ps` does not answer, it MUST raise `EmbeddingProviderError` at once, so a dead Ollama does not spend the wait below.

- With the model loaded, the query MUST use 3 s and no retry.
- With the model not loaded, it MUST wait up to 20 s and no retry, inside the 25 s of the chat turn, because Ollama drops a load when the client disconnects.
- If the wait fails with the model not loaded, it MUST queue the load (`pedir_carga_del_modelo`) before raising, so the load goes on in the worker.

Every query MUST log whether the model was loaded and how many milliseconds the vector took (`buscar_semantico: cargado=… vector_ms=…`).

#### Scenario: Ollama hung during a chat query

- GIVEN Ollama accepts the connection and never answers
- WHEN `buscar_semantico` asks whether the model is loaded
- THEN it gives up after 1 s, without embedding, and raises `EmbeddingProviderError`

#### Scenario: Question before the model finished loading

- GIVEN the model is not loaded and Ollama is loading it
- WHEN `buscar_semantico` runs
- THEN it waits up to 20 s for the vector
- AND it logs whether the model was loaded and how long the vector took
- AND if the wait runs out it raises `EmbeddingProviderError` and queues the load in the background

### Requirement: Query by meaning with filters after retrieval

`buscar_semantico(consulta, *, generos=None, tipo=None, anio_desde=None, anio_hasta=None, nota_minima=None, duracion_max=None, excluir=())` MUST embed the query, rank `ready` embeddings by cosine distance, take the 50 nearest, apply the filters in SQL, drop the `(id_tmdb, tipo)` pairs in `excluir`, and return at most 10 productions in ranking order.

- The query MUST set `hnsw.ef_search = 100` with `SET LOCAL`, inside its own transaction: with pgvector's default of 40, asking the HNSW index for 50 returns 40 or fewer without warning. The setting MUST NOT outlive the transaction.
- `generos` MUST match on any of the English names stored in `ProduccionAudiovisual.generos`. The chatbot tool, not this function, expands a name to its equivalent in the other type (`Science Fiction` ↔ `Sci-Fi & Fantasy`).
- `tipo` and `excluir` MUST use TMDB types (`movie`, `tv`), like `vistos()` and the cards, not the value stored in the model.
- A production missing the field a filter asks for (for example, a series without `duracion`) MUST be left out.
- Quantitative fields MUST NOT be part of the embedded text (18/08/2026).

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
- AND the chatbot tool turns it into `{"error": "tool_failed"}`, so the turn goes on without the search

### Requirement: The model loads before the first question

`POST /api/chat/preparar/` MUST require a session and enforce CSRF like every cookie-authenticated mutation: 401 (Unauthorized) without a session, 403 (Forbidden) with `code: "permission_denied"` in JSON without the CSRF header, and 405 (Method Not Allowed) for a `GET`. With a session it MUST answer 202 (Accepted) without waiting for the load. The panel calls it on every opening (05/11/2026).

`pedir_carga_del_modelo()` MUST queue `calentar_modelo` at most once per minute, using `cache.add` on the key `chatbot:carga_modelo` with a 60 s life, and the queued task MUST expire after 60 s, so an old request does not pile up when no worker is running. It MUST NOT raise: a cache or broker failure MUST be logged, MUST NOT fail the request, and a broker failure MUST delete the key so the next request can try again.

`calentar_modelo` MUST run in the Celery worker, embed a short text with a 60 s timeout and no retry, and store no result. If Ollama fails it MUST log a warning and delete the key, so the next question can ask for the load again.

#### Scenario: Opening the panel

- GIVEN an authenticated user and a model that is not loaded
- WHEN the panel opens
- THEN the response is 202 and the worker loads the model

#### Scenario: The cache is down

- GIVEN an authenticated user and a cache that fails on `add`
- WHEN the panel calls `POST /api/chat/preparar/`
- THEN the response is still 202

### Requirement: Reachable from containers in every setup

The backend and the Celery worker MUST read the Ollama address from `OLLAMA_URL` and MUST map `host.docker.internal` to the host gateway. The compose file MUST offer two optional profiles, and neither MUST start by default:

- `ollama-windows`: `ollama-puente` (`alpine/socat`, pinned) with `network_mode: host`, listening on `172.17.0.1:11435` and forwarding to the Windows Ollama on `127.0.0.1:11434`. It is the default in `.env.example` (`OLLAMA_URL=http://host.docker.internal:11435`).
- `ollama`: a containerized `ollama/ollama` (pinned) with a 2 GB memory limit, a volume for the model, and no published ports; the backend reaches it at `http://ollama:11434`.

#### Scenario: Developer with Ollama for Windows

- GIVEN Ollama for Windows with `bge-m3`, WSL in mirrored networking, and the `ollama-windows` profile up
- WHEN the backend container calls `OLLAMA_URL=http://host.docker.internal:11435`
- THEN the request reaches the Windows Ollama
- AND Ollama is not exposed to the local network
