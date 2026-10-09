# Profile UI

## Purpose

Editing the authenticated user's own profile, selecting predefined avatars, confirming account deactivation, and managing their own ratings and reviews in `/my-reviews` (P-06). The reviews screen consumes `reviews-api`.

## Requirements

### Avatar selection

Editing MUST expose a visible keyboard-accessible “Cambiar avatar” overlay. It MUST open a modal containing every active avatar returned by the API. Selecting an avatar MUST only change the temporary selection within the modal. Its “Guardar” button MUST apply the choice to the profile draft and close the selector. Canceling or pressing Escape MUST discard the temporary selection; reopening MUST preselect the current draft avatar. Only saving the profile MUST persist the choice and update the navbar. The selector MUST show “Elegí un avatar” once, preserve page layout and scroll position on opening/closing, and expose a pointer cursor on the clickable overlay.

### Unsaved changes

Canceling or following a same-tab link or browser history traversal with a modified draft MUST open “¿Salir sin guardar?”. Continuing editing MUST preserve all fields and avatar. Confirming MUST discard the draft and complete the requested action. An unchanged or reverted draft MUST not prompt. Reloading or closing the tab MUST use the native browser warning. Modified-click links opening another tab MUST retain their native behavior.

### Username availability

Availability checks MUST ignore canceled responses. “Disponible” MUST be green, “No disponible” red, with readable contrast in both themes and a textual live announcement. Errors saving MUST preserve the draft.

### Deactivation warning

The confirmation MUST say: “Esta acción es irreversible. Se cerrarán todas tus sesiones y no podrás volver a iniciar sesión ni reactivar tu cuenta. Asegurate de querer dar de baja la cuenta antes de continuar.” Canceling MUST not call the API. A failed request MUST leave the dialog available to retry and the account active. The existing logical deactivation and internal retention policy remain unchanged.

### Button consistency

Buttons with the same variant MUST share foreground/background tokens across profile, selectors, review dialogs and preferences. Primary, secondary and destructive buttons MUST provide at least 4.5:1 text contrast in light/dark themes, including hover.

### Own reviews (Mis reseñas)

`/mis-resenas` MUST display each own rating with a poster, title, type, a yellow (#f5c518) decorative star beside its X/10 value, date and optional text. The star MUST precede the numeric rating on the same line. The date MUST appear separately in the top-right corner of the card, with no overlap at mobile widths. The rating MUST have an accessible label identifying it as a rating. Read-more/read-less controls MUST only appear when the text exceeds three visible lines at the current card width, recalculating after resizing or editing. Text that fits, including exactly three lines, and absent text MUST have no expansion control. An absent review MUST display “Todavía no escribiste una reseña.” as an informative empty state with icon, subtle background, dashed border and italic text, visually distinct from authored content. Poster dimensions MUST be reserved (80 × 120 desktop, 56 × 84 mobile); absent or failed images MUST have an accessible replacement. Titles MUST remain plain text until the detail route exists.

The UI MUST progressively load cursor pages and expose a keyboard-accessible load-more button. Duplicate IDs MUST not create duplicate cards. A page failure MUST preserve previously loaded cards and offer retry.

The edit dialog MUST be titled `Editar calificación y reseña de "{title}"`. Editing MUST initially focus the review text field without focusing any star, preserve the saved rating, and keep the rating group keyboard-accessible. Editing MUST preload the rating and text, enforce integer 1–10 and at most 1000 text characters, and MUST NOT send empty text to PUT. Text deletion MUST confirm preservation of rating and Vistas, leaving the card without text. Rating deletion MUST confirm the loss of rating, optional text and Vistas membership, removing the card on success only. Its success toast MUST name what was lost: "Calificación y reseña eliminadas." when the rating had text, "Calificación eliminada." otherwise (doc 04 §5d). Dialogs MUST contain keyboard focus, support Escape when idle and restore focus.

#### Scenario: A poster cannot load

- GIVEN an own rating with an unavailable poster
- WHEN its card renders
- THEN a same-size replacement appears without breaking the layout

#### Scenario: Deleting text from an own card

- WHEN the user confirms text deletion
- THEN the card keeps its rating and explains that no review text exists
- AND Vistas membership is unchanged


### Locale integration

Settings (`/settings`) is bilingual and contains the only signed-in language
control, between Appearance and Notifications, at anchor `t-idioma`. The account
locale is persisted before cookie/render change; a failed save preserves the
old locale. Profile (`/profile`) and reviews (`/my-reviews`) retain legacy copy
until their designs are implemented, while their validations, formats, errors
and enum labels use the shared locale helpers. Default-list labels come from
stable keys, not names stored in the database. Footer language links navigate
with a real anchor/Link and remain available on mobile.
