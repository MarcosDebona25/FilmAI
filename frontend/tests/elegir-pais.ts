import type userEvent from "@testing-library/user-event";
import { screen } from "@testing-library/react";

/**
 * Elige un país en `CountrySelect` como lo haría el usuario: abre la lista
 * desde el campo y hace clic en la opción (el selector ya no es un `<select>`
 * nativo, así que `selectOptions` no sirve).
 */
export async function elegirPais(
  user: ReturnType<typeof userEvent.setup>,
  campo: HTMLElement,
  nombre: string
) {
  await user.click(campo);
  await user.click(screen.getByRole("option", { name: nombre }));
}
