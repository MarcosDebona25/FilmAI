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
  await expect(page.getByText("Todavía no calificaste ninguna película ni serie.")).toBeVisible();
});

test.describe("sesión", () => {
  test("con el access vencido renueva sola y no saca de la página", async ({ page }) => {
    await prepararCuenta(page);
    // Solo queda la cookie `refresh`: el `access` de 8 horas ya venció.
    await page.context().clearCookies({ name: "access" });
    await page
      .context()
      .addCookies([{ name: "refresh", value: "valida", url: "http://127.0.0.1:3100" }]);
    let renovada = false;
    await page.route("**/api/auth/token/refresh/", async (route) => {
      renovada = true;
      await route.fulfill({ status: 200, json: {} });
    });
    await page.route("**/api/profile/", async (route) =>
      renovada
        ? route.fallback()
        : route.fulfill({ status: 401, json: { code: "not_authenticated" } })
    );
    await page.goto("/profile");
    await expect(page.getByRole("heading", { level: 1, name: "Juan Pérez" })).toBeVisible();
    expect(renovada).toBe(true);
    await expect(page).toHaveURL(/\/profile$/);
  });

  test("si la sesión venció del todo, avisa el motivo y lleva al login", async ({ page }) => {
    await prepararCuenta(page);
    await page.route("**/api/auth/token/refresh/", (route) =>
      route.fulfill({ status: 401, json: { code: "token_not_valid" } })
    );
    await page.route("**/api/profile/", (route) =>
      route.fulfill({ status: 401, json: { code: "not_authenticated" } })
    );
    await page.goto("/profile");
    await expect(page).toHaveURL(/\/login\?next=%2Fprofile$/);
    await expect(page.getByText("Tu sesión venció. Iniciá sesión de nuevo.")).toBeVisible();
  });
});
