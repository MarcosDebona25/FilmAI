# Proposal: Recommendation chatbot (Module 5 — B-02 to B-06, CU-013, CU-014, CU-018)

## Intent

FilmAI's pitch is that recommendations come from **your own history** and that
a chatbot talks about it, anchored in real catalog titles (`PRODUCT.md`). Every
other module is built. Of Module 5 only two pieces exist:

1. **B-01** — `Chat` and `Mensaje`, one chat per user, created at sign-up.
2. **Half of B-06** — pgvector, `ProduccionEmbedding`, the canonical text, the
   Celery task and the backfill. `generar_vector()` still raises
   `NotImplementedError`, so every backfill ends in `failed`.

Meanwhile the interface already promises the assistant: «Ask FilmAI» in the
Home and the footer points to `/chat`, which answers 404 (Not Found), and the
404 page invites visitors to "get personalized picks from the FilmAI
assistant".

This change builds the rest: semantic search, the LLM orchestration with tools,
the streaming API, persistence, and the floating panel.

## What was already decided

The architecture was agreed in pair programming and is recorded in
`docs/decisiones.md`. This change does not reopen it; it turns it into a
contract and a task list.

| Date | Entry | What it fixes |
|---|---|---|
| 18/08/2026 | Retrieval architecture | Mandatory tool calling, BGE-M3 via Ollama, pgvector |
| 08/10/2026 | Chatbot architecture | DeepSeek through an OpenAI-compatible adapter, SSE over ASGI, text + cards, per-message SQL profile, limits |
| 09/10/2026 | Language, cards, errors, limits | Turn language vs. prose language, 3 cards, error codes, no queue, `/api/chat/messages/` |
| 28/10/2026 | Security: XSS | Untrusted model output: sanitized Markdown, links built from ids |
| 28/10/2026 | Semantic search, personal data, `/chat`, SDD | Ollama measured first; nothing personal to the LLM; no `/chat` page |
| 28/10/2026 | Latency test against DeepSeek | `deepseek-flash` with thinking off; tools drop «Vistas» before the model sees them |
| 28/10/2026 | bge-m3 measurement | Windows Ollama in development, reached through a `socat` bridge |

## Scope

### In Scope

- **B-06 — semantic search.** Real `generar_vector()` against Ollama
  (`/api/embed`, `bge-m3`, retries), `MODEL_VERSION = "bge-m3"`,
  `buscar_semantico()` over `ready` embeddings with SQL filters, the dev bridge
  service and the production `ollama` service in `docker-compose.yml`, and a
  backfill run.
- **B-02 — LLM service.** Provider adapter (`AsyncOpenAI` → DeepSeek) and a
  fake provider for tests; the eight tools; the system prompt; the async
  orchestrator (at most 4 tool rounds, ~25 s budget); `manage.py chatear` as
  the test bench without HTTP.
- **B-05 — personal context.** The profile built by SQL on every message, and
  the anonymizer.
- **B-03 — chat API.** ASGI (`daphne` in development); `POST
  /api/chat/messages/` as an async Django view streaming SSE; `GET
  /api/chat/messages/` (DRF, cursor) for the history; cancellation by
  disconnect; one request in flight per chat; 20 messages per hour; error
  codes in the contract.
- **B-04 — the panel.** `ChatProvider` in the root layout, FAB, drawer /
  bottom sheet, bubbles, up to 3 cards, the SSE reader, cancel, unread badge,
  sanitized Markdown, the copy in `traducciones/`, and «Ask FilmAI» opening
  the panel instead of navigating.
- **Persistence.** `Mensaje.tarjetas` (JSON) and `Chat.contexto.ya_recomendados`.
- **Docs.** 02 (CU-013/014 details), 03 (`Mensaje.tarjetas` migration), 04
  (§3.1, «Ask FilmAI»), 05 (B-02…B-06 status), 06 (new TMDB calls),
  `.env.example`, the canonical specs, and the golden set.

### Out of Scope

- **Several chats per user.** The model allows them; the MVP keeps the
  uniqueness constraint of B-01.
- **Clearing or deleting the conversation.** No use case asks for it.
- **A `/chat` page.** The chat is floating only (28/10/2026).
- **Where to watch from the chat.** The country and watch providers exist
  (18/10/2026), but a «dónde verla» tool is a later addition. The tool
  registry makes it a new entry, not a redesign.
- **Reusing «Recommended for you» (C-05) as a tool.** It stays algorithmic and
  LLM-free; the chatbot shares only its `vistos()` helper.
- **Production deployment** (uvicorn behind a proxy, CSP, a hosted Ollama).
  The design leaves them configurable; deploying is its own task.
- **Voice, images, or files in the chat.**

## Risks and rollback

| Risk | Mitigation | Rollback |
|---|---|---|
| Moving to ASGI breaks something that worked under WSGI | `daphne` only changes the dev server; DRF views stay sync and Django adapts them. `manage.py test` does not start a server (and the Playwright job mocks the API), so ASGI is exercised by tests that call `get_asgi_application()` directly: the SSE view (including a real `http.disconnect`) and existing DRF endpoints (a public read and an authenticated write with CSRF). Plus a manual check: `runserver` (daphne) and `curl -N`, and the e2e suite run locally against it. | Remove `daphne` from `INSTALLED_APPS`: `runserver` goes back to WSGI. The SSE view stops streaming; nothing else changes. |
| Ollama is down or slow | `buscar_semantico` failing is a tool error returned to the model, which falls back to the TMDB tools. The backfill marks rows `failed` and retries at 4 AM, as it does today. | The tool can be removed from the registry without touching the orchestrator. |
| DeepSeek is down, slow or out of credit | Timeout and error codes; nothing is persisted; the UI says «No podemos procesar tu solicitud». Provider and model come from `.env`. | Point `LLM_BASE_URL`/`LLM_MODEL` at another OpenAI-compatible provider. |
| Prompt injection through synopses, reviews or the user's message | Tool results are marked as data in the prompt; cards are validated server-side; the UI never renders model HTML or model URLs. | — |
| Cost | `deepseek-flash` without thinking, 20 messages/hour/user, last 10 messages as history, `max_tokens` on answers. The 28/10 test cost under one cent for 24 calls. | Lower the hourly limit from `.env`. |

Each PR in `tasks.md` names its own rollback boundary.
