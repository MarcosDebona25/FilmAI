import { expect, test, type Page } from "@playwright/test";

import { reacher, svu } from "../tests/catalog-fixtures";
import { simularCatalogo, sinSesion } from "./api-simulada";
import { auditar } from "./axe";

/**
 * Los nombres de «Director and cast» de la ficha llevan a Buscar con la
 * persona como filtro (15/11/2026), igual que su fila en la lupa de la navbar.
 * Con la API simulada: los créditos son los de `CREDITOS_INTERSTELLAR`.
 */
const PERSONAS: Record<string, object> = {
  "525": { id: 525, name: "Christopher Nolan", rol: "director", gender: 2, profile_path: null },
  "1813": { id: 1813, name: "Anne Hathaway", rol: "actor", gender: 1, profile_path: null },
};

async function preparar(page: Page) {
  await sinSesion(page);
  await simularCatalogo(page);
  // Se registra después que las de `simularCatalogo`: Playwright prueba primero la última.
  await page.route("**/api/catalogo/explore/**", (route) => {
    const persona = new URL(route.request().url()).searchParams.get("persona") ?? "";
    return route.fulfill({
      json: {
        page: 1,
        total_pages: 1,
        total_results: 2,
        results: [reacher, svu],
        persona: PERSONAS[persona],
      },
    });
  });
  await page.goto("/movie/157336");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Interstellar");
}

test.describe("créditos de la ficha en escritorio", () => {
  test.use({ viewport: { width: 1440, height: 900 }, locale: "en-US" });

  test("el director lleva a Buscar con su chip", async ({ page }) => {
    await preparar(page);
    const creditos = page.getByRole("region", { name: "Director and cast" });
    const director = creditos.getByRole("link", { name: "Christopher Nolan" });
    await expect(director).toHaveAttribute("href", "/search?person=525&role=director");
    // El personaje no es parte del enlace del reparto.
    await expect(creditos.getByRole("link", { name: "Anne Hathaway", exact: true })).toBeVisible();
    await auditar(page);

    await director.click();
    await expect(page).toHaveURL(/\/search\?person=525&role=director$/);
    await expect(page.getByText("Christopher Nolan · Director")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Remove filter Christopher Nolan" })
    ).toBeVisible();
  });
});

test.describe("créditos de la ficha en celular", () => {
  test.use({ viewport: { width: 375, height: 812 }, locale: "en-US" });

  test("alguien del reparto lleva a Buscar con su chip, como actor", async ({ page }) => {
    await preparar(page);
    const actriz = page
      .getByRole("region", { name: "Director and cast" })
      .getByRole("link", { name: "Anne Hathaway", exact: true });
    await expect(actriz).toHaveAttribute("href", "/search?person=1813&role=actor");
    await auditar(page);

    await actriz.click();
    await expect(page).toHaveURL(/\/search\?person=1813&role=actor$/);
    await expect(page.getByText("Anne Hathaway · Actress")).toBeVisible();
    await expect(page.getByRole("button", { name: "Remove filter Anne Hathaway" })).toBeVisible();
    // Sin desborde horizontal con el chip puesto.
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    ).toBe(true);
  });
});
