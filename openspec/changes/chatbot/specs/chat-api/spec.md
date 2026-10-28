# chat-api Specification

## Purpose

The backend of the recommendation chatbot (CU-013, CU-014, CU-018; B-02, B-03, B-05): a streaming endpoint that answers one message with text and up to three cards anchored in real catalog titles, the conversation history, and the rules that keep the model grounded, private and bounded. Decisions of 08/10, 09/10 and 28/10/2026 in `docs/decisiones.md`.

## Requirements

### Requirement: Only an authenticated, active user chats

Both `POST` and `GET /api/chat/messages/` MUST require a session. Without one they MUST answer 401 (Unauthorized) with `code: "not_authenticated"`. The `POST` MUST enforce CSRF like every cookie-authenticated mutation and answer a failure with 403 (Forbidden) and `code: "permission_denied"` in the error envelope, never Django's HTML page.

#### Scenario: No session

- GIVEN no session cookies
- WHEN the client POSTs a message
- THEN the response is 401 with `code: "not_authenticated"`
- AND nothing is streamed or stored

#### Scenario: Missing CSRF header

- GIVEN a valid session cookie and no `X-CSRFToken`
- WHEN the client POSTs a message
- THEN the response is 403 with `code: "permission_denied"` as JSON

### Requirement: The message is validated before the stream opens

The text MUST be 1 to 500 characters after trimming. Otherwise the response MUST be 400 (Bad Request) with `code: "validation_error"` and `errors.texto`. Only one request MAY be in flight per chat: a second one MUST answer 409 (Conflict) with `code: "chat_request_in_progress"`. A user MUST NOT send more than `CHAT_MENSAJES_POR_HORA` (20) valid messages per hour: the next one MUST answer 429 (Too Many Requests) with `code: "throttled"` and `retry_after_seconds`.

#### Scenario: Too long

- GIVEN a text of 501 characters
- WHEN it is POSTed
- THEN the response is 400 with `errors.texto`
- AND the hourly counter does not move

#### Scenario: Second message while the first streams

- GIVEN an answer is still streaming for the user's chat
- WHEN the user POSTs another message
- THEN the response is 409 with `code: "chat_request_in_progress"`
- AND the first answer continues unaffected

#### Scenario: Lock released after a crash

- GIVEN a request that died without releasing the lock
- WHEN 30 seconds have passed
- THEN a new message is accepted

### Requirement: The answer streams as server-sent events

A valid `POST` MUST answer 200 with `Content-Type: text/event-stream` and a sequence of events named `estado`, `texto`, `tarjetas`, `fin` or `error`, each with one line of JSON as `data`. The stream MUST end with exactly one of `fin` or `error`. `estado` and `error` MUST carry codes, never text. The full contract is in `contracts/sse-chat.md`.

#### Scenario: A turn that uses a tool

- GIVEN the model asks for `similares_a` and then writes an answer
- WHEN the message is POSTed
- THEN the client receives `estado {code: "searching"}`, then one or more `texto {delta}`, then `tarjetas`, then `fin`
- AND concatenating the deltas gives the stored answer text

#### Scenario: Provider down

- GIVEN DeepSeek answers 503
- WHEN the message is POSTed
- THEN the stream ends with `error` carrying `code: "chat_unavailable"`
- AND no message is stored

### Requirement: The question and the answer are stored together, at the end

The user message and the bot answer MUST be saved in one transaction only after the last token, immediately before `fin`. A turn that fails, times out or is cancelled MUST leave no rows. `Mensaje.tarjetas` MUST store the cards exactly as streamed.

#### Scenario: Cancelled mid-answer (CU-014)

- GIVEN an answer is streaming
- WHEN the client closes the connection
- THEN the server stops the turn
- AND no `Mensaje` row is created for either side
- AND the lock is released

#### Scenario: Failure while saving

- GIVEN the database rejects the save
- WHEN the turn reaches its end
- THEN the stream ends with `error` and `code: "chat_unavailable"`, not `fin`

### Requirement: Cards come only from this turn's tools and never from «Vistas»

`mostrar_tarjetas` MUST keep only `(id_tmdb, tipo)` pairs returned by a tool earlier in the same turn, drop those in the user's «Vistas», drop duplicates, and keep at most 3. Dropped cards MUST NOT raise an error. Every search tool MUST remove «Vistas» from its results before the model sees them.

#### Scenario: Invented id

- GIVEN the model calls `mostrar_tarjetas` with an id no tool returned
- WHEN the card is validated
- THEN it is dropped silently and the rest are kept

#### Scenario: Watched title in the search results

- GIVEN *Moon* is in the user's «Vistas» and among TMDB's similar titles
- WHEN `similares_a` runs
- THEN *Moon* is not in what the model receives

### Requirement: Nothing that identifies the user reaches the provider

The profile, the review excerpts and the history MUST NOT contain the user's first name, last name, email or username; any occurrence MUST be replaced before sending (RNF #3, CU-018). The model MUST NOT be able to address data of another user: `mis_listas` MUST take no user argument and read only the authenticated user's lists.

#### Scenario: Name inside a review

- GIVEN the user, Juan Pérez (`@juanp`), wrote a review saying «Juan aprueba»
- WHEN the profile is built
- THEN the excerpt sent to the provider reads «[usuario] aprueba»

### Requirement: The profile is fresh on every message

The personal context MUST be read by SQL for each message: liked (rating ≥ 7, with an excerpt of the review), disliked (≤ 4), recently watched and favorites. A rating changed between two messages MUST be reflected in the second.

#### Scenario: Rating changed mid-conversation

- GIVEN the user rated *Dune* 8 and asked for a recommendation
- WHEN they change it to 3 and ask again
- THEN the second prompt lists *Dune* among the disliked

### Requirement: Language of the turn and of the prose

The view MUST resolve `idioma_efectivo(request, usuario)` once, before streaming, and every tool, card and status of the turn MUST use it. The system prompt MUST tell the model to write in the language of the user's message, falling back to the turn language. A language change during a request MUST apply from the next message.

#### Scenario: Interface in English, message in Spanish

- GIVEN a user whose account language is `en`
- WHEN they write «algo como Interstellar»
- THEN TMDB is queried in English and the cards show English titles
- AND the system prompt carries `en` as the fallback language

### Requirement: Bounded turn

A turn MUST stop after 4 tool rounds or `LLM_TIMEOUT_SECONDS` (25), ending with `error` and `code: "chat_unavailable"`. A tool failure (TMDB, Ollama, the TMDB budget) MUST be returned to the model as a tool result, not end the turn. The history sent to the model MUST be at most the last 10 messages.

#### Scenario: Ollama down during a turn

- GIVEN `buscar_semantico` raises `EmbeddingProviderError`
- WHEN the model called it
- THEN the model receives `{"error": "tool_failed"}` and the turn continues

#### Scenario: Endless tool calls

- GIVEN a model that asks for a tool on every round
- WHEN the fifth round would start
- THEN the stream ends with `error` and nothing is stored

### Requirement: History

`GET /api/chat/messages/` MUST return the authenticated user's messages, newest first, cursor-paginated by 20, each with `id`, `autor` (`usuario` | `chatbot`), `texto`, `tarjetas` and `fecha_hora`. Cards MUST be returned as stored, without translating them again.

#### Scenario: Another user's chat

- GIVEN two users with messages
- WHEN one of them reads the history
- THEN only their own messages are returned
