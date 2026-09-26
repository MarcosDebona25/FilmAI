import { expect, test } from "@playwright/test";

import { prepararCuenta } from "./cuenta";

test("el menú admite teclado y Mis reseñas explica su estado pendiente", async ({ page }) => {
  await prepararCuenta(page);
  await page.goto("/mis-resenas");
  await page.getByRole("button", { name: "Menú de usuario" }).click();
  await expect(page.getByRole("menuitem", { name: "Mi perfil" })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("menuitem", { name: "Mis reseñas" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/mis-resenas$/);
  await expect(page.getByText("Esta sección todavía no está implementada.")).toBeVisible();
});
