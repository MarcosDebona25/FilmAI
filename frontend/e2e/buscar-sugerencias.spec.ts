import { expect, test, type Page } from "@playwright/test";

import { reacher, svu } from "../tests/catalog-fixtures";
import { simularCatalogo, sinSesion } from "./api-simulada";

/**
 * El campo de Buscar sugiere como la lupa y avisa «¿Buscabas a…?» (14/11/2026).
 * Con la API simulada: `suggest/` devuelve a Ryan Gosling y una película.
 */
const RYAN = {
  media_type: "person",
  id: 30614,
  name: "Ryan Gosling",
  rol: "actor",
  gender: 2,
  profile_path: null,
};

async function preparar(page: Page) {
  await sinSesion(page);
  await simularCatalogo(page);
  // Se registran después que las de `simularCatalogo`: Playwright prueba primero la última.
  await page.route("**/api/catalogo/suggest/**", (route) =>
    route.fulfill({ json: { results: [RYAN, { ...reacher, media_type: "tv" }] } })
  );
  await page.route("**/api/catalogo/browse/**", (route) =>
    route.fulfill({
      json: {
        page: 1,
        total_pages: 1,
        total_results: 2,
        results: [reacher, svu],
        persona: { ...RYAN, name: "Ryan Gosling" },
      },
    })
  );
}

const campo = (page: Page) => page.locator("#busqueda");

test.describe("campo de Buscar con sugerencias", () => {
  // Textos en inglés: sin esto el navegador del CI pide español.
  test.use({ viewport: { width: 1280, height: 720 }, locale: "en-US" });

  test("elegir una persona de la lista pone su filtro y vacía el campo", async ({ page }) => {
    await preparar(page);
    await page.goto("/search");

    await campo(page).fill("ryan");
    const lista = page.getByRole("listbox");
    await expect(lista).toBeVisible({ timeout: 15_000 });
    // Sin «See all results»: la página ya muestra todos.
    await expect(lista.getByRole("option")).toHaveCount(2);
    await lista.getByRole("option", { name: /Ryan Gosling/ }).click();

    await expect(page).toHaveURL(/\/search\?person=30614&role=actor$/);
    await expect(page.getByText("Ryan Gosling · Actor")).toBeVisible();
    await expect(campo(page)).toHaveValue("");
  });

  test("«¿Buscabas a…?» lleva a sus producciones y saca el texto", async ({ page }) => {
    await preparar(page);
    await page.goto("/search");

    await campo(page).fill("ryan gosling");
    const aviso = page.getByText(/Looking for Ryan Gosling\?/);
    await expect(aviso).toBeVisible({ timeout: 15_000 });
    // El campo sigue buscando el texto mientras se escribe, aviso aparte.
    await expect(page).toHaveURL(/\/search\?q=ryan\+gosling$/);

    await page.getByRole("button", { name: "See their titles" }).click();

    await expect(page).toHaveURL(/\/search\?person=30614&role=actor$/);
    await expect(aviso).toHaveCount(0);
    await expect(campo(page)).toHaveValue("");
  });
});
