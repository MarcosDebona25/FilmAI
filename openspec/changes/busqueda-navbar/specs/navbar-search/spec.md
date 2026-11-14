# navbar-search Specification

## Purpose

The search of the desktop navbar (13/11/2026; variant changed on 14/11/2026 to a magnifier that unfolds into a field): the magnifier opens a field, typing shows up to 5 suggestions of titles and people from `GET /api/catalogo/suggest/` (`tmdb-endpoints`), and Enter opens the Search page (`search-ui`) with the text. Mobile keeps the «Search» tab of `MobileTabs`. Follows the canvas artboard «Navbar · desktop».

## ADDED Requirements

### Requirement: Placement

On desktop (from 768 px) the navbar MUST show, on the right and before the account menu or the «Log in · Sign up» links, a magnifier button, and MUST NOT show «Search» among the left links. The button MUST have an accessible name, `aria-expanded` (true while the field is unfolded) and `aria-controls` pointing to the field's container. Pressing it MUST unfold a search field in the same place and move the focus into it. The field MUST fold with Escape (when the list is closed), with its ✕ button, or when it loses the focus with no text; with Escape or ✕ the focus MUST return to the magnifier, and a field that loses the focus with text MUST stay unfolded. Below 768 px the navbar MUST NOT show the magnifier nor the field. On `/search` the navbar MUST NOT render them.

#### Scenario: Desktop home

- GIVEN a 1440 px viewport on `/home`
- THEN the navbar's left links are «Home» and «Lists» (with a session)
- AND the magnifier sits before the account menu, with `aria-expanded="false"`

#### Scenario: Unfolding and folding

- GIVEN the magnifier is pressed
- THEN the field unfolds in its place with the focus in it and `aria-expanded="true"`
- WHEN the user presses Escape with the list closed
- THEN the field folds, the magnifier has the focus and `aria-expanded="false"`

#### Scenario: Blur with and without text

- GIVEN the field is unfolded and empty
- WHEN it loses the focus
- THEN it folds
- BUT with the text «dune» it stays unfolded with the list closed

#### Scenario: On the Search page

- GIVEN `/search?q=dune` on desktop
- THEN the navbar has no magnifier nor field and the page's field has the focus

### Requirement: Suggestions

The field MUST ask for suggestions 250 ms after the last keystroke when the trimmed text has 2 characters or more, abort the previous request, show an answer only if its text is still the field's text, and keep answers per language and text for the visit. While a new answer loads, the previous list MUST stay. The list MUST show the suggestions in the order received and end with «See all results for “text”». A title MUST open its title page without `from`; a person MUST open `/search?person={id}&role={rol}`; Enter with no active option and «See all results» MUST open `/search?q={text}` with no other filter. After navigating, the field MUST be cleared and the list closed. An error MUST close the list without a message.

#### Scenario: Typing a name

- GIVEN the user types «nol» and then «nolan» within 250 ms
- THEN only `suggest/?q=nolan` is requested
- AND «Christopher Nolan · Director» is among the options

#### Scenario: Enter goes to Search

- GIVEN the field holds «dune» and no option is active
- WHEN the user presses Enter
- THEN the page becomes `/search?q=dune`

### Requirement: Accessible combobox

The field MUST follow the ARIA 1.2 combobox with list autocomplete and manual selection: `role="combobox"`, `aria-autocomplete="list"`, `aria-expanded`, `aria-controls` to a `role="listbox"`, and `aria-activedescendant` with the active option's id. Options MUST have `role="option"`, a stable id, `aria-selected` on the active one and an accessible name that includes the type and year, or the role. ↓ and ↑ MUST move the active option (past the last, back to the field); Enter MUST follow it; Escape MUST close the list and a second Escape clear and fold the field; Tab MUST close it without choosing; Alt+↓ MUST reopen the last list. Typing MUST NOT activate an option. A polite live region, present from the start, MUST announce how many suggestions arrived, or that there are none.

#### Scenario: Keyboard only

- GIVEN suggestions for «dune» are open
- WHEN the user presses ↓ twice and Enter
- THEN the second option's page opens
- AND while it was active, the field's `aria-activedescendant` pointed to it

#### Scenario: Count is announced

- GIVEN the user types «chihiro»
- WHEN 2 suggestions arrive
- THEN the live region reads «2 suggestions»

### Requirement: Shortcut

On desktop, `/` MUST unfold the magnifier and focus the field (on `/search`, the page's field) unless the focus is in an editable element or a dialog is open; then it MUST type normally. The unfolded field MUST show a «/» hint while empty and unfocused, and the magnifier MUST declare `aria-keyshortcuts="/"`.

#### Scenario: Typing a slash in a review

- GIVEN the focus is in the review text area
- WHEN the user types «/»
- THEN the character is typed and the focus stays there
