# chat-ui Specification

## Purpose

The floating chat of the frontend (B-04, CU-013, CU-014; doc 04 §3.1 and canvas section 10): a FAB on every screen that opens a drawer on desktop and a bottom sheet on mobile, where the user talks to the assistant and sees up to three title cards per answer. There is no `/chat` page (28/10/2026).

## Requirements

### Requirement: One chat, available everywhere

The chat state MUST live in a provider in the root layout so it survives navigation. The FAB MUST be on every screen with the chat, disabled without a session, and its accessible name MUST be its visible text («Ask FilmAI»; WCAG 2.5.3, 06/11/2026). Choosing a card MUST close the panel so the title page is visible; the conversation stays. The footer's «Ask FilmAI» MUST open the panel for a user with a session and MUST be a link to `/login?next=<current page>` for a visitor; there is no `/chat` route (06/11/2026).

#### Scenario: Navigating with the panel open

- GIVEN the panel is open with a conversation
- WHEN the user navigates to another page
- THEN the conversation and any streaming answer are still there

#### Scenario: Without a session

- GIVEN a visitor without a session
- WHEN they look at the FAB
- THEN it is disabled and nothing is requested from the chat API

#### Scenario: Footer «Ask FilmAI»

- GIVEN a user with a session
- WHEN they activate «Ask FilmAI» in the footer
- THEN the panel opens
- AND a visitor sees it as a link to `/login?next=<current page>`

### Requirement: Streaming answer with cancel

While an answer streams the panel MUST show the status from `estado` codes, append `texto` deltas in order, render `tarjetas` when they arrive, and turn the send button into «Cancelar». The input MUST stay editable as a draft but MUST NOT send. Cancelling MUST abort the request, show «Solicitud cancelada» and re-enable sending. The panel MUST arbitrate by the order in which it processes events: a cancel processed before `fin` MUST discard the answer even if it was complete (CU-014 2.A); after `fin` is processed the turn is over and the button MUST be «Enviar» again. A discarded answer that the server had already saved MAY reappear in the history (CU-014, failure postcondition).

#### Scenario: Cancel

- GIVEN an answer is streaming
- WHEN the user presses «Cancelar»
- THEN the request is aborted
- AND the partial answer is removed and «Solicitud cancelada» is shown
- AND the question stays in the input to retry

#### Scenario: Cancel processed before `fin` (CU-014 2.A)

- GIVEN the last `texto` arrived and `fin` is in flight
- WHEN the panel processes the click on «Cancelar» first
- THEN the answer is discarded and «Solicitud cancelada» is shown
- AND if the server had saved it, it appears in the history the next time it loads

#### Scenario: `fin` processed first

- GIVEN the panel processed `fin`
- WHEN the user's click lands an instant later
- THEN the button already reads «Enviar», nothing is cancelled and the answer stays

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

Answers MUST be rendered as Markdown without raw HTML and sanitized. Links and images written by the model MUST be rendered as plain text: no clickable link and no image request. Card links MUST be built by the frontend from `id_tmdb` and `tipo`. A card shows the TMDB rating when the event carries `nota_tmdb` (optional; cards saved before it existed have none). `dangerouslySetInnerHTML` MUST NOT be used (28/10/2026).

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

### Requirement: The panel prepares the model

On every opening the panel MUST call `POST /api/chat/preparar/`, without waiting for it and without showing anything if it fails. A question asked right after opening is what this protects: a cold load can take more than the 20 s a chat query waits (05/11/2026).

#### Scenario: Opening the panel

- GIVEN a user with a session
- WHEN they open the panel
- THEN `POST /api/chat/preparar/` is sent with the CSRF header
- AND a failure of that request shows nothing

### Requirement: Welcome, history and unread badge

The panel MUST load the history the first time it opens in a session (newest page first) and MUST NOT request it again on later openings, except the opening that follows a cancel, which requests the newest page again because the server may have saved the discarded answer (CU-014). Older pages MUST load when the user scrolls to the top, using only the query of the `next` cursor (never an origin received from the network), without moving what the user was reading. A failed load MUST show the translated error with a retry button. Messages from the stream and from the history MUST be merged by id so none repeats. When the chat is empty the panel MUST show the local welcome with the user's first name and three suggestions (see «Rotating welcome suggestions»), without calling the model; choosing a suggestion MUST send it right away and MUST NOT touch the draft. An answer that finishes while the panel is closed MUST light the FAB badge (a dot plus text for screen readers) until the panel opens. Signing out MUST clear the conversation, the history and the badge (06/11/2026).

#### Scenario: First time

- GIVEN a user with no messages
- WHEN they open the panel
- THEN they see the welcome with their first name and three suggestions
- AND no request is sent to the model

#### Scenario: Suggestion

- GIVEN the welcome is showing and the input has a draft
- WHEN the user chooses a suggestion
- THEN that text is sent as the question
- AND the draft is unchanged

#### Scenario: History

- GIVEN a user with more than 20 saved messages
- WHEN they open the panel for the first time
- THEN the newest 20 are shown, ending at the last one
- AND scrolling to the top loads the previous page without moving the visible messages
- AND closing and reopening the panel does not request the history again

#### Scenario: Reopening after a cancel

- GIVEN the user cancelled an answer that the server had already saved
- WHEN they open the panel again
- THEN the newest page is requested again and the answer appears once

#### Scenario: Unread badge

- GIVEN a question is being answered and the user closes the panel
- WHEN the answer ends
- THEN the FAB shows the badge
- AND opening the panel turns it off

### Requirement: Rotating welcome suggestions (06/11/2026)

The three suggestions of the welcome MUST be drawn again every time the panel opens: one from the personal group (`similar`, `fromLists`, `different`, `unseenClassic`) and two different ones from the general group (`short`, `series`, `family`, `comedy`, `thriller`, `miniseries`, `popular`, `hiddenGem`, `acclaimed`, `animated`), 14 in all (`frontend/lib/chat-sugerencias.ts`). A suggestion MUST NOT name a production: a fixed title is foreign to whoever has not seen it, and the personal ones ask for something the model resolves with the profile it already receives (best-rated titles, lists). The first render MUST use a fixed set (`short`, `similar`, `series`) so the server and the client hydrate the same, and the draw MUST happen after the panel opens. Every suggestion MUST have a text in both languages.

#### Scenario: Different suggestions on each opening

- GIVEN the welcome is showing
- WHEN the user closes the panel and opens it again
- THEN three suggestions are drawn again
- AND exactly one is from the personal group and two from the general group, all different

#### Scenario: No production named

- GIVEN any suggestion in either language
- WHEN its text is read
- THEN it names no movie or TV show

### Requirement: A card without a title is a placeholder (#180)

A card from the history whose `titulo` is `null` MUST render as the compact `UnavailableCard` (grey thumbnail and «Title no longer available» / «Título no disponible», key `common.content.titleUnavailable`), without a link. Only the history accepts a null title: the stream guard `esTarjeta` still requires one.

#### Scenario: A trimmed card whose title is gone

- GIVEN a history card with `titulo: null`
- WHEN the panel renders it
- THEN it shows «Title no longer available» in a row with a grey thumbnail
- AND it has no link

### Requirement: The button looks clickable and focus never falls to the page (Q-01, Q-03, Q-04)

The FAB MUST show a hand cursor and a hover state (`bg-primary/80`, 2 px lift with a deeper shadow, 1 px down on press; with `prefers-reduced-motion` only the color changes), only while enabled, with text contrast of at least 4.5:1. A single base rule MUST give the hand cursor to buttons, `role="button|switch|menuitem|radio|tab"`, `summary`, `select` and checkboxes with their label, except disabled and `aria-disabled` ones, in a layer that `cursor-not-allowed`, `cursor-wait` and `cursor-grab` override. When the focused «Cancel» button unmounts, or a suggestion disappears after being chosen, focus MUST move to the input. At 375, 768 and 1440 px the panel and the FAB MUST NOT overflow and MUST have 44 px touch targets; axe-core WCAG 2.1 AA finds no violation in the FAB, the open panel, an answer with cards and the error (`frontend/e2e/chat-calidad.spec.ts`).

#### Scenario: Cancel while focused

- GIVEN a streaming answer and focus on «Cancel»
- WHEN the user cancels
- THEN focus moves to the input

### Requirement: Accessible panel

The panel MUST open and close with keyboard and pointer, trap focus while open, close with Escape and return focus to the FAB. A finished answer MUST be announced once through a polite live region, not delta by delta.

#### Scenario: Keyboard only

- GIVEN focus on the FAB
- WHEN the user presses Enter, types a message, sends it and presses Escape
- THEN the panel opened with focus on the input, the message was sent, and focus returned to the FAB
