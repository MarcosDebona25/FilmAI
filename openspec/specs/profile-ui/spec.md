# Profile UI

## Purpose

Editing the authenticated user's own profile, selecting predefined avatars and confirming account deactivation.

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
