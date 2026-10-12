import { expect, test } from "@playwright/test";

import { prepararCuenta } from "./cuenta";

test("el menú admite teclado y Mis reseñas muestra el estado vacío", async ({ page }) => {
  await prepararCuenta(page);
  await page.route("**/api/reviews/mias/**", (route) =>
    route.fulfill({ json: { total: 0, next: null, results: [] } })
  );
  await page.goto("/my-reviews");
  await page.getByRole("button", { name: "Menú de Juan Pérez" }).click();
  await expect(page.getByRole("menuitem", { name: "Mi perfil" })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("menuitem", { name: "Calificaciones y reseñas" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/my-reviews$/);
  await expect(
    page.getByText("Todavía no calificaste ninguna producción ni escribiste reseñas.")
  ).toBeVisible();
});
