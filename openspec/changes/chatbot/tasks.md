# Tasks: Recommendation chatbot (Module 5)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~3 000 (backend ~1 800, frontend ~1 200) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes — a contract PR (PR 0) and eight more, split in two fronts (below) |
| Delivery strategy | ask-on-risk |
| Chain strategy | Each PR from `main`, one worktree per PR in `~/FilmAI-worktrees/<branch>`; a PR that needs an unmerged PR **of the same front** stacks on it (merge commit, no rebase); one that needs the other front waits for the merge |
| Way of working | Split by fronts (04/11/2026): **Gonza → Motor, Marcos → Canal**; PR 0 together. Every async concept explained from zero as it appears |
| PR-Agent | At most 3 passes per PR; later findings go to the next PR that fits, or are dropped |

## Work split (04/11/2026)

This section is the reference for who does what. `docs/decisiones.md`
(entry of 04/11/2026) points here.

The whole chatbot goes through one function, `chatbot/orquestador.py ::
responder()`. Below it lives what **thinks** the answer (model, tools,
profile, anonymizer, semantic search): the **Motor**. Above it lives what
**carries and shows** it (SSE view, lock, save, history, panel): the
**Canal**. PR 0 fixes that seam (`chatbot/eventos.py`) and ships a fake
`responder()`, so neither front waits for the other.

```
                 PR 0 contract (together)
                   │
   Motor (Gonza)   ▼                       Canal (Marcos)
   PR1 semantic ──► PR2 tools ──► PR3 orchestrator      PR4 persistence + GET ──► PR6 panel (fake stream)
                                        │                       ──► PR5 ASGI/SSE (fake responder) ──► PR7 history/badge/copy
                                        └──── swap fake → real in the view (sync point 2) ────┘
                                                              PR8 closing (each front its half)
```

| | **Motor — Gonza** | **Canal — Marcos** |
|---|---|---|
| PRs, in order | 1 → 2 → 3, then golden set (8.1, 8.2) | 4 → 6 → 5 → 7 |
| Builds | Vectors and `buscar_semantico`, Q-09, TMDB methods, the 8 tools, profile, anonymizer, provider, prompt, orchestrator, `manage.py chatear` | `Mensaje.tarjetas`, `guardar_turno()`, history `GET`, ASGI/`daphne`, SSE view, lock, hourly limit, error codes, panel, history, badge, «Ask FilmAI», copy |
| Owns these files | `catalogo/services/semantica.py`, `catalogo/client.py`, `catalogo/tasks.py`, `chatbot/tools/`, `chatbot/{contexto,anonimizar,llm,prompts,orquestador}.py`, `chatbot/management/`, `docker-compose.yml`, `.env.example` | `chatbot/{models,servicio,serializers,views,urls}.py`, `chatbot/migrations/`, `filmai/asgi.py`, `filmai/test_asgi.py`, `filmai/errores/catalogo.py`, `contracts/`, `frontend/**`, `traducciones/` |
| Est. lines | ~1 300 | ~1 550 |

Canal goes 4 → 6 → 5 because the panel only needs the SSE contract (a
hand-made `text/event-stream`), and by the time PR5 starts PR3 is closer.

**Dependencies**

| PR | Can start with | Needs merged before merging |
|---|---|---|
| 0 | — | — |
| 1 | — | — |
| 2 | — (leave the `buscar_semantico` tool for last, or stack on PR1) | PR1; PR0 (`Tarjeta`) |
| 3 | PR2 (same front, may stack) | PR0, PR2 |
| Golden set | PR3 | — |
| 4 | — | — |
| 6 | — | — |
| 5 | PR0 (fake), PR4 (`guardar_turno`) | PR0, PR4 (not PR3) |
| 7 | PR4 (`GET`), PR6 (panel); Playwright mocks the API | PR4, PR6 |
| Swap fake → real | PR3 and PR5 | — |

PR1, PR2, PR4 and PR6 start with no wait at all, not even for PR 0. The only
cross-front waits are PR 0 (shared) and the final swap (Canal waits for PR3).

**Shared files**

| File | Rule |
|---|---|
| `chatbot/eventos.py` | Owned by both. A change goes in its own small PR, agreed first |
| `backend/filmai/settings.py` | Motor writes the provider block (`LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_THINKING`, `LLM_API_KEY`, `LLM_PROVEEDORES`, `OLLAMA_URL`, `OLLAMA_KEEP_ALIVE`); Canal the ASGI/`daphne` block plus `LLM_TIMEOUT_SECONDS` and `CHAT_MENSAJES_POR_HORA`, because the view owns the turn timeout and the lock. Separate blocks, each with a header comment |
| `backend/requirements.txt` | Motor adds `openai`, Canal adds `daphne`; on conflict keep both lines |
| `docs/decisiones.md` | Each adds its entry on top; on merge keep both |
| `graphify-out/` | Never resolved by hand: after the merge run `graphify update .` and commit |
| PR8 docs | Motor: doc 05 (B-02, B-05, B-06), doc 06, spec `semantic-search`. Canal: doc 02 (CU-013/014), doc 03, doc 04 (§3.1), specs `chat-api`, `chat-ui` |
| `PRODUCT.md`, removing `openspec/changes/chatbot/` | Whoever merges last |

**Sync points**

1. PR 0 (with the docs of 04/11) merged before PR2 or PR5 merge. PR1, PR4 and PR6 do not wait for it.
2. When PR3 merges: Canal swaps `OrquestadorFalso` for `orquestador.responder`
   in the view and runs one real turn with `curl -N` against DeepSeek.
3. Closing: Motor runs the golden set with `manage.py chatear --golden` (no HTTP, so it needs PR3, not PR5); docs split as above.
4. Copy (7.1): Marcos writes and approves it (09/10/2026).

Q-08 (emails through Celery, doc 05) is the filler task for whoever finishes
first or is blocked waiting on the other front. Worktree cautions: never run
two `manage.py test` at once on the same machine (shared `test_*` database);
real `npm ci` per worktree; one `.codegraph/` per worktree.

### Work Units

| PR | Front | Goal | Est. lines | Focused test command | Rollback boundary |
|----|-------|------|-----------:|----------------------|-------------------|
| 0 | Both | Contract of `responder()`: events, result, fake | ~150 | `test chatbot.tests_contrato` | Delete `eventos.py`, `orquestador_falso.py`; nothing uses them yet |
| 1 | Motor | B-06: real vectors, semantic query, Ollama profiles | ~350 | `test catalogo.tests_semantica` | Revert `generar_vector` to the stub; remove the profiles |
| 2 | Motor | Tools, profile, anonymizer (sync) | ~450 | `test chatbot.tests_tools chatbot.tests_contexto` | Delete `chatbot/tools/`, `contexto.py`, `anonimizar.py`; nothing calls them yet |
| 3 | Motor | Provider, prompt, async orchestrator, `chatear` | ~400 | `test chatbot.tests_orquestador` | Delete the modules; no endpoint uses them |
| 4 | Canal | Persistence and history `GET` | ~250 | `test chatbot.tests_historial` | Reverse migration; remove the route |
| 5 | Canal | ASGI and the SSE `POST` | ~400 | `test chatbot.tests_sse` | Remove the route and `daphne` |
| 6 | Canal | Panel: provider, FAB, stream, cancel | ~500 | `npm run test:unit -- chat` | Remove the provider from the layout |
| 7 | Canal | History, badge, «Ask FilmAI», copy, e2e | ~400 | `npx playwright test chat` | Restore the `/chat` links |
| 8 | Both | Golden set, RNF #6, docs | ~250 | manual | Docs only |

## Phase 0: Contract (PR 0) — together

- [x] 0.1 Explain: async generator, why the last item is a `Resultado`
      (an async generator cannot `return` a value), `Protocol`, why a fake
      lets both fronts work in parallel
- [x] 0.2 `chatbot/eventos.py`: `Estado`, `Texto`, `Tarjeta`, `Resultado`,
      `ErrorDelTurno`, `Responder` protocol `(chat, texto, idioma)`
- [x] 0.3 `chatbot/orquestador_falso.py`: `OrquestadorFalso(guion, demora,
      falla_en)` and `GUION_BASICO`
- [x] 0.4 `chatbot/tests_contrato.py`: order and single final `Resultado`,
      scripted failure, cancellation during a delay, recorded calls, card shape


## Phase 1: Semantic search (PR 1)

- [x] 1.1 RED `catalogo/tests_semantica.py`: `generar_vector` sends model
      `bge-m3`, `keep_alive` and the text to `OLLAMA_URL/api/embed`, and returns
      the vector (`httpx.MockTransport`)
- [x] 1.2 RED: backfill budget — 3 connection failures → 3 attempts and
      `EmbeddingProviderError`; chat budget — a hang → one attempt, 3 s, and
      `EmbeddingProviderError`; a 768-float vector → `EmbeddingProviderError`
- [x] 1.3 GREEN: `generar_vector` with `httpx`; backfill budget 10 s and 2
      retries, chat-query budget 3 s and no retry;
      `MODEL_VERSION = "bge-m3"`; `OLLAMA_URL` in settings
- [x] 1.4 RED: `buscar_semantico` returns the nearest `ready` rows in order,
      skips `pending`/`failed`, applies each filter, honours `excluir`, caps
      at 10 (vectors built by hand in the test DB, query vector faked)
- [x] 1.5 GREEN: `catalogo/services/semantica.py` with pgvector's
      `CosineDistance`, overfetch 50
- [x] 1.6 `docker-compose.yml`: profile `ollama-windows` (`ollama-puente`,
      `alpine/socat` pinned, `network_mode: host`, bind `172.17.0.1:11435`),
      profile `ollama` (pinned `ollama/ollama`, `mem_limit: 2g`, volume);
      `extra_hosts` on backend and worker; `.env.example` `OLLAMA_URL`
- [ ] 1.7 Manual: both developers bring up the bridge and run the backfill;
      record counts and time in `docs/decisiones.md`
- [x] 1.7b Q-09 (doc 05): RED/GREEN expiry of the `processing` claim, with the
      deadline taken from the real times of 1.7
- [x] 1.8 Explain: what an embedding is, cosine distance, why filters run after
      the vector, how the bridge works

## Phase 2: Tools, profile, anonymizer (PR 2)

- [x] 2.1 RED `catalogo` client: `get_recommendations(id, tipo)`,
      `search_person(nombre)` and `get_person_credits(id)` hit the right TMDB
      paths; `discover` accepts `duracion_max` (C-01 fake transport)
- [x] 2.2 GREEN: the three client methods and their cache wrappers; doc 06
- [x] 2.3 RED `chatbot/tests_tools.py`: each search tool returns
      `ProduccionResumen` items (≤ 10, synopsis ≤ 300) without «Vistas», and
      records the returned ids in the turn context
- [x] 2.4 RED: `mostrar_tarjetas` drops unseen ids, «Vistas» and duplicates,
      keeps 3, and returns the card dicts in the turn language
- [x] 2.5 RED: `mis_listas` reads only the context user's lists; without
      arguments it returns `{id, nombre}`; a custom list is read by `id`; the
      `id` of another user's list is not found; a list named with the user's
      name comes back anonymized
- [x] 2.6 RED: a tool that raises returns `{"error": "tool_failed"}`; the TMDB
      budget error too
- [x] 2.7 GREEN: `chatbot/tools/` (registry, schemas, functions), reusing
      `servicio_localizado`, `vistos()` and the TMDB budget
- [x] 2.8 RED `chatbot/tests_contexto.py`: liked/disliked/watched/favorites
      with their caps and excerpt length; a changed rating moves sections
- [x] 2.9 RED: `anonimizar`, case- and accent-insensitive, whole words only.
      Strict scope: name, last name and username → `[usuario]`. Conversation
      scope: name and last name together and username → `[usuario]`, a loose
      name stays («Mark Ruffalo» for the user Mark Debona, also with username
      `mark`). Both: every email
      address, the user's own included, → `[correo]`
- [x] 2.10 GREEN: `contexto.py`, `anonimizar.py`
- [x] 2.11 RED/GREEN: `modelo_cargado`, wait up to 20 s when the model is not
      loaded, `calentar_modelo`, `POST /api/chat/preparar/`, `OLLAMA_KEEP_ALIVE`

## Phase 3: Provider and orchestrator (PR 3) — first async code

- [x] 3.1 Explain from zero, before writing code: what blocks a server thread,
      event loop, `async def`/`await`, async generators, `sync_to_async`,
      why only one bridge
- [x] 3.2 `llm.py`: `ProveedorLLM` protocol; `ProveedorFalso` replaying a
      script of deltas, tool calls, errors and delays
- [x] 3.3 RED `chatbot/tests_orquestador.py` with `ProveedorFalso`: plain
      answer → `Texto…` and a final `Resultado` with no cards; `responder()`
      follows `chatbot/eventos.py` (PR 0) and saves nothing (the view saves)
- [x] 3.4 RED: tool round → `estado searching`, tool executed in the bridge,
      result fed back, answer streamed, cards validated; `mostrar_tarjetas`
      called in a middle round still ends up in the single final `Resultado`
      (after the last `Texto`), and there is no `Resultado` when the turn
      raises `ErrorDelTurno`
- [x] 3.5 RED: 5th tool round → `ErrorDelTurno`; provider exception →
      `ErrorDelTurno`; tool exception → turn continues (the 25 s timeout is
      the view's, task 5.6b)
- [x] 3.6 RED: the messages sent to the provider contain the anonymized
      profile, ≤ 10 history messages, `ya_recomendados`
      rendered as titles and years (no bare ids),
      the anonymized current message, and no full name/email/username
- [x] 3.7 RED: two tools of the same turn, each through the bridge, add to the
      **same** TMDB budget counter (the total accumulates; the 31st call fails)
- [x] 3.8 GREEN: `prompts.py`, `orquestador.py`, `ProveedorOpenAICompatible`
      (`openai` dependency; thinking off by default; `max_tokens` 800);
      `mis_listas` results go through `anonimizar`, TMDB results do not
- [x] 3.8b RED/GREEN: with `LLM_THINKING=true`, a tool round echoes
      `reasoning_content` in the assistant message (needed for 8.2)
- [x] 3.9 `manage.py chatear` (interactive, prints events); try it against
      DeepSeek with the `.env` key

## Phase 4: Persistence and history (PR 4)

- [x] 4.1 Migration: `Mensaje.tarjetas` (`JSONField`, default list); update
      `Chat.contexto` help text (it still describes the discarded precomputed
      profile)
- [x] 4.2 RED: `guardar_turno()` saves both messages atomically, appends the
      cards to `ya_recomendados` as `{id_tmdb, tipo, titulo, anio}` (cap 30),
      and leaves nothing when it fails
- [x] 4.3 RED `chatbot/tests_historial.py`: `GET /api/chat/messages/`
      newest first, cursor of 20, own messages only, cards as stored, 401
      without session
- [x] 4.4 GREEN: the service, serializer, cursor pagination (pattern of
      `pagination_reviews.py`), route, OpenAPI regenerated

## Phase 5: ASGI and the SSE endpoint (PR 5)

- [x] 5.1 Explain: WSGI vs ASGI, what `daphne` changes in `runserver`,
      `StreamingHttpResponse` with an async iterator, SSE framing, how a
      disconnect becomes a cancellation
- [x] 5.2 `daphne` in `INSTALLED_APPS` (first), `ASGI_APPLICATION`. The test
      runner does not start a server and the Playwright job mocks the API,
      so add `filmai/test_asgi.py`: through `get_asgi_application()`, a
      public DRF read and an authenticated DRF write with CSRF answer as
      under WSGI. Manual: `runserver` shows daphne, local e2e stays green
- [x] 5.3 Error codes `chat_request_in_progress`, `chat_unavailable` in the
      catalog; front translations; contract tests green
- [x] 5.4 RED `chatbot/tests_sse.py` (`AsyncClient`): 401, 403 CSRF as JSON,
      401 `session_revoked` for a deactivated account with a live cookie
      (same as the rest of the API, 06/11/2026), 400 length, 409 lock, 429
      with `retry_after_seconds`; a 409 does not move the hourly counter
- [x] 5.5 RED: a full turn yields the event sequence and stores the pair on
      `fin`; provider failure yields `error` and stores nothing. Until PR3
      merges, 5.4–5.6b drive the view with `OrquestadorFalso` (PR 0): its
      `demora` stands in for a slow turn and `falla_en` for a provider error
- [x] 5.6 RED: through `get_asgi_application()` with a fake ASGI `receive`
      that sends `http.disconnect` mid-stream (the `AsyncClient` does not
      simulate a disconnect): nothing is stored and the lock is freed; a
      disconnect during the save keeps the lock until the save ends; a save
      failure sends `error` and no `tarjetas`
- [x] 5.6b RED: lock with a per-request token — an expired request's late
      release leaves the next request's lock; a fake turn that sleeps past
      the budget hits the 25 s turn timeout and the lock is released; a save
      still running when the budget expires is not interrupted and ends in
      `fin`
- [x] 5.7 GREEN: `views.py :: MensajesView.post` (sync gate, async stream), lock, hourly counter,
      `idioma_efectivo` once, `contar_llamadas` inside the stream generator;
      the view saves with `guardar_turno()` (PR4) from the final `Resultado`.
      Once PR3 is in `main`, swap the fake for `orquestador.responder` (one
      line) — sync point 2
- [x] 5.8 `contracts/sse-chat.md`; OpenAPI entry for the `POST` with its
      pre-stream responses
- [x] 5.9 Manual: `curl -N` against the dev server shows events arriving one
      by one

## Phase 6: The panel (PR 6)

- [x] 6.1 Dependencies `react-markdown`, `rehype-sanitize` (rebuild + `up -d
      -V frontend`, `npm install` on the host)
- [x] 6.2 RED Vitest `lib/chat.ts`: frames split across chunks, unknown events
      ignored, missing `fin` → network error, pre-stream 409/429 → `ApiError`
- [x] 6.3 RED: Markdown renderer neutralizes `<script>`, `<img onerror>`,
      `javascript:` links and Markdown images (`![x](https://…)` → text, no
      `img`)
- [x] 6.3b Panel: `POST /api/chat/preparar/` on opening (05/11/2026)
- [x] 6.4 GREEN: `lib/chat.ts`, `ChatProvider`, `ChatFab`, `ChatPanel`,
      `ChatBubble`, `ChatTarjetas`, `ChatInput` following the canvas
- [x] 6.5 RED/GREEN: cancel keeps the draft and shows «Solicitud cancelada»;
      both orders of «Cancelar» vs `fin` (whichever is processed first
      wins); an `error` after some deltas removes
      the partial answer, shows the translated code and keeps the draft
- [x] 6.6 Explain: reading a stream in the browser, `AbortController`, why
      the provider sits in the layout

## Phase 7: History, badge, links, copy (PR 7)

- [ ] 7.1 Copy: curate the 22 `chatbot` rows of `traducciones/claves.csv`, add
      cancel/error/status keys, approve with Marcos, seed; `npm run i18n:check`
- [x] 7.2 History on open, older pages on scroll up; local welcome with first
      name and suggestions
- [x] 7.3 Badge when an answer ends with the panel closed
- [x] 7.4 «Ask FilmAI» (Home, footer) opens the panel; retire
      `routes.askFilmAI`; update the 404 and tests that pointed to `/chat`
- [x] 7.5 Playwright with a canned `text/event-stream`: send, stream, cards,
      cancel, keyboard-only flow, mobile bottom sheet
- [x] 7.6 `vercel-quality` pass on the panel

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
