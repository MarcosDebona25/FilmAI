/** Mantiene Tab y Mayús+Tab dentro de un diálogo modal visible. */
export function mantenerFocoEnDialogo(event: KeyboardEvent, dialogo: HTMLElement | null) {
  if (event.key !== "Tab" || !dialogo) return;
  const controles = Array.from(
    dialogo.querySelectorAll<HTMLElement>(
      "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])"
    )
  ).filter((control) => {
    if (!(control instanceof HTMLInputElement) || control.type !== "radio") return true;
    const group = Array.from(
      dialogo.querySelectorAll<HTMLInputElement>('input[type="radio"]')
    ).filter((radio) => radio.name === control.name);
    return control === (group.find((radio) => radio.checked) ?? group[0]);
  });
  if (!controles.length) return;
  const primero = controles[0];
  const ultimo = controles[controles.length - 1];
  if (event.shiftKey && document.activeElement === primero) {
    event.preventDefault();
    ultimo.focus();
  } else if (!event.shiftKey && document.activeElement === ultimo) {
    event.preventDefault();
    primero.focus();
  }
}
