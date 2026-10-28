# Tasks: Recommendation chatbot (Module 5)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~3 000 (backend ~1 800, frontend ~1 200) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes — eight, in order |
| Delivery strategy | ask-on-risk |
| Chain strategy | Each PR from `main` after the previous one merges (no stacking) |
| Way of working | Pair programming, Gonza and Marcos; every async concept explained from zero as it appears |

### Work Units

| PR | Goal | Est. lines | Focused test command | Rollback boundary |
|----|------|-----------:|----------------------|-------------------|
| 1 | B-06: real vectors, semantic query, Ollama profiles | ~350 | `test catalogo.tests_semantica` | Revert `generar_vector` to the stub; remove the profiles |
| 2 | Tools, profile, anonymizer (sync) | ~450 | `test chatbot.tests_tools chatbot.tests_contexto` | Delete `chatbot/tools/`, `contexto.py`, `anonimizar.py`; nothing calls them yet |
| 3 | Provider, prompt, async orchestrator, `chatear` | ~400 | `test chatbot.tests_orquestador` | Delete the modules; no endpoint uses them |
| 4 | Persistence and history `GET` | ~250 | `test chatbot.tests_historial` | Reverse migration; remove the route |
| 5 | ASGI and the SSE `POST` | ~400 | `test chatbot.tests_sse` | Remove the route and `daphne` |
| 6 | Panel: provider, FAB, stream, cancel | ~500 | `npm run test:unit -- chat` | Remove the provider from the layout |
| 7 | History, badge, «Ask FilmAI», copy, e2e | ~400 | `npx playwright test chat` | Restore the `/chat` links |
| 8 | Golden set, RNF #6, docs | ~250 | manual | Docs only |

## Phase 1: Semantic search (PR 1)

- [ ] 1.1 RED `catalogo/tests_semantica.py`: `generar_vector` sends model
      `bge-m3`, `keep_alive` and the text to `OLLAMA_URL/api/embed`, and returns
      the vector (`httpx.MockTransport`)
- [ ] 1.2 RED: 3 connection failures → `EmbeddingProviderError`; a 768-float
      vector → `EmbeddingProviderError`
- [ ] 1.3 GREEN: `generar_vector` with `httpx`, 10 s timeout, 2 retries;
      `MODEL_VERSION = "bge-m3"`; `OLLAMA_URL` in settings
- [ ] 1.4 RED: `buscar_semantico` returns the nearest `ready` rows in order,
      skips `pending`/`failed`, applies each filter, honours `excluir`, caps
      at 10 (vectors built by hand in the test DB, query vector faked)
- [ ] 1.5 GREEN: `catalogo/services/semantica.py` with pgvector's
      `CosineDistance`, overfetch 50
- [ ] 1.6 `docker-compose.yml`: profile `ollama-windows` (`ollama-puente`,
      `alpine/socat` pinned, `network_mode: host`, bind `172.17.0.1:11435`),
      profile `ollama` (pinned `ollama/ollama`, `mem_limit: 2g`, volume);
      `extra_hosts` on backend and worker; `.env.example` `OLLAMA_URL`
- [ ] 1.7 Manual: both developers bring up the bridge and run the backfill;
      record counts and time in `docs/decisiones.md`
- [ ] 1.8 Explain: what an embedding is, cosine distance, why filters run after
      the vector, how the bridge works

## Phase 2: Tools, profile, anonymizer (PR 2)

- [ ] 2.1 RED `catalogo` client: `get_similar(id, tipo)` and
      `search_person(nombre)` hit the right TMDB paths; `discover` accepts
      `with_people` (C-01 fake transport)
- [ ] 2.2 GREEN: the three client methods and their cache wrappers; doc 06
- [ ] 2.3 RED `chatbot/tests_tools.py`: each search tool returns
      `ProduccionResumen` items (≤ 10, synopsis ≤ 300) without «Vistas», and
      records the returned ids in the turn context
- [ ] 2.4 RED: `mostrar_tarjetas` drops unseen ids, «Vistas» and duplicates,
      keeps 3, and returns the card dicts in the turn language
- [ ] 2.5 RED: `mis_listas` reads only the context user's lists; a custom list
      of another user is not found
- [ ] 2.6 RED: a tool that raises returns `{"error": "tool_failed"}`; the TMDB
      budget error too
- [ ] 2.7 GREEN: `chatbot/tools/` (registry, schemas, functions), reusing
      `servicio_localizado`, `vistos()` and the TMDB budget
- [ ] 2.8 RED `chatbot/tests_contexto.py`: liked/disliked/watched/favorites
      with their caps and excerpt length; a changed rating moves sections
- [ ] 2.9 RED: `anonimizar` replaces name, last name, email and username,
      case- and accent-insensitive, whole words only
- [ ] 2.10 GREEN: `contexto.py`, `anonimizar.py`

## Phase 3: Provider and orchestrator (PR 3) — first async code

- [ ] 3.1 Explain from zero, before writing code: what blocks a server thread,
      event loop, `async def`/`await`, async generators, `sync_to_async`,
      why only one bridge
- [ ] 3.2 `llm.py`: `ProveedorLLM` protocol; `ProveedorFalso` replaying a
      script of deltas, tool calls, errors and delays
- [ ] 3.3 RED `chatbot/tests_orquestador.py` with `ProveedorFalso`: plain
      answer → `texto…`, `tarjetas []`, `fin`-ready result
- [ ] 3.4 RED: tool round → `estado searching`, tool executed in the bridge,
      result fed back, answer streamed, cards validated
- [ ] 3.5 RED: 5th tool round → error; timeout → error; provider exception →
      error; tool exception → turn continues
- [ ] 3.6 RED: the messages sent to the provider contain the anonymized
      profile, ≤ 10 history messages with the cards line, `ya_recomendados`,
      and no name/email/username
- [ ] 3.7 RED: the TMDB budget `ContextVar` is visible inside a tool run
      through the bridge
- [ ] 3.8 GREEN: `prompts.py`, `orquestador.py`, `ProveedorOpenAICompatible`
      (`openai` dependency; thinking off by default; `max_tokens` 800)
- [ ] 3.9 `manage.py chatear` (interactive, prints events); try it against
      DeepSeek with the `.env` key

## Phase 4: Persistence and history (PR 4)

- [ ] 4.1 Migration: `Mensaje.tarjetas` (`JSONField`, default list); update
      `Chat.contexto` help text (it still describes the discarded precomputed
      profile)
- [ ] 4.2 RED: `guardar_turno()` saves both messages atomically, appends to
      `ya_recomendados` (cap 30), and leaves nothing when it fails
- [ ] 4.3 RED `chatbot/tests_historial.py`: `GET /api/chat/messages/`
      newest first, cursor of 20, own messages only, cards as stored, 401
      without session
- [ ] 4.4 GREEN: the service, serializer, cursor pagination (pattern of
      `pagination_reviews.py`), route, OpenAPI regenerated

## Phase 5: ASGI and the SSE endpoint (PR 5)

- [ ] 5.1 Explain: WSGI vs ASGI, what `daphne` changes in `runserver`,
      `StreamingHttpResponse` with an async iterator, SSE framing, how a
      disconnect becomes a cancellation
- [ ] 5.2 `daphne` in `INSTALLED_APPS` (first), `ASGI_APPLICATION`; run the
      full suite under it
- [ ] 5.3 Error codes `chat_request_in_progress`, `chat_unavailable` in the
      catalog; front translations; contract tests green
- [ ] 5.4 RED `chatbot/tests_sse.py` (`AsyncClient`): 401, 403 CSRF as JSON,
      400 length, 409 lock, 429 with `retry_after_seconds`
- [ ] 5.5 RED: a full turn yields the event sequence and stores the pair on
      `fin`; provider failure yields `error` and stores nothing
- [ ] 5.6 RED: closing the response mid-stream stores nothing and frees the
      lock
- [ ] 5.7 GREEN: `views.py :: enviar_mensaje`, lock, hourly counter,
      `idioma_efectivo` once, `contar_llamadas` for the turn
- [ ] 5.8 `contracts/sse-chat.md`; OpenAPI entry for the `POST` with its
      pre-stream responses
- [ ] 5.9 Manual: `curl -N` against the dev server shows events arriving one
      by one

## Phase 6: The panel (PR 6)

- [ ] 6.1 Dependencies `react-markdown`, `rehype-sanitize` (rebuild + `up -d
      -V frontend`, `npm install` on the host)
- [ ] 6.2 RED Vitest `lib/chat.ts`: frames split across chunks, unknown events
      ignored, missing `fin` → network error, pre-stream 409/429 → `ApiError`
- [ ] 6.3 RED: Markdown renderer neutralizes `<script>`, `<img onerror>`,
      `javascript:` links
- [ ] 6.4 GREEN: `lib/chat.ts`, `ChatProvider`, `ChatFab`, `ChatPanel`,
      `ChatBubble`, `ChatTarjetas`, `ChatInput` following the canvas
- [ ] 6.5 RED/GREEN: cancel keeps the draft and shows «Solicitud cancelada»;
      answer at the same instant discarded
- [ ] 6.6 Explain: reading a stream in the browser, `AbortController`, why
      the provider sits in the layout

## Phase 7: History, badge, links, copy (PR 7)

- [ ] 7.1 Copy: curate the 22 `chatbot` rows of `traducciones/claves.csv`, add
      cancel/error/status keys, approve with Marcos, seed; `npm run i18n:check`
- [ ] 7.2 History on open, older pages on scroll up; local welcome with first
      name and suggestions
- [ ] 7.3 Badge when an answer ends with the panel closed
- [ ] 7.4 «Ask FilmAI» (Home, footer) opens the panel; retire
      `routes.askFilmAI`; update the 404 and tests that pointed to `/chat`
- [ ] 7.5 Playwright with a canned `text/event-stream`: send, stream, cards,
      cancel, keyboard-only flow, mobile bottom sheet
- [ ] 7.6 `vercel-quality` pass on the panel

## Phase 8: Closing (PR 8)

- [ ] 8.1 `chatbot/golden.yaml` (10–15 questions: simple, with tools,
      out-of-scope, Portuguese message, injection attempt, «para chicos»)
- [ ] 8.2 `manage.py chatear --golden` with thinking off and on; record times
      against RNF #6 and the verdict in `docs/decisiones.md`
- [ ] 8.3 Docs: 02 (CU-013/014 details), 03 (migration done), 04 (§3.1, «Ask
      FilmAI»), 05 (B-02…B-06 ✅), `PRODUCT.md`
- [ ] 8.4 Canonical specs `semantic-search`, `chat-api`, `chat-ui` into
      `openspec/specs/`; remove `openspec/changes/chatbot/`
- [ ] 8.5 `graphify update .`
