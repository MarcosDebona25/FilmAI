import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import { reacher, svu } from "../tests/catalog-fixtures";
import { simularCatalogo, sinSesion } from "./api-simulada";

/**
 * La lupa de la navbar (14/11/2026): se despliega, sugiere personas y títulos,
 * y elegir una persona lleva a Buscar con su chip. Con la API simulada.
 */
const ESCRITORIO = { width: 1280, height: 720 };
const CELULAR = { width: 390, height: 844 };

const NOLAN = {
  id: 525,
  name: "Christopher Nolan",
  rol: "director",
  gender: 2,
  profile_path: null,
};

async function preparar(page: Page) {
  await sinSesion(page);
  await simularCatalogo(page);
  // Se registran después que las de `simularCatalogo`: Playwright prueba primero la última.
  await page.route("**/api/catalogo/suggest/**", (route) =>
    route.fulfill({
      json: {
        results: [{ media_type: "person", ...NOLAN }, { ...reacher, media_type: "tv" }, svu],
      },
    })
  );
  await page.route("**/api/catalogo/browse/**", (route) =>
    route.fulfill({
      json: {
        page: 1,
        total_pages: 1,
        total_results: 2,
        results: [reacher, svu],
        persona: NOLAN,
      },
    })
  );
}

const lupa = (page: Page) => page.getByRole("button", { name: en.nav.search.openLabel });

test.describe("lupa de la navbar en escritorio", () => {
  // Textos en inglés: sin esto el navegador del CI pide español.
  test.use({ viewport: ESCRITORIO, locale: "en-US" });

  test("escribir, elegir una persona y quitar su chip en Buscar", async ({ page }) => {
    await preparar(page);
    await page.goto("/home");

    await lupa(page).click();
    const campo = page.getByRole("combobox");
    await expect(campo).toBeFocused();
    await campo.fill("nolan");
    const lista = page.getByRole("listbox");
    await expect(lista).toBeVisible({ timeout: 15_000 });
    await expect(lista.getByRole("option", { name: /Christopher Nolan/ })).toBeVisible();
    await expect(lista.getByRole("option", { name: /See all results for “nolan”/ })).toBeVisible();

    await lista.getByRole("option", { name: /Christopher Nolan/ }).click();
    await expect(page).toHaveURL(/\/search\?person=525&role=director$/);
    await expect(page.getByText("Christopher Nolan · Director")).toBeVisible();
    // En Buscar la navbar no tiene lupa: la página trae su propio campo.
    await expect(lupa(page)).toHaveCount(0);

    await page.getByRole("button", { name: "Remove filter Christopher Nolan" }).click();
    await expect(page.getByText("Christopher Nolan · Director")).toHaveCount(0);
    await expect(page).toHaveURL(/\/search$/);
  });

  test("Escape cierra la lista y después el campo, y el foco vuelve a la lupa", async ({
    page,
  }) => {
    await preparar(page);
    await page.goto("/home");

    await lupa(page).click();
    await page.getByRole("combobox").fill("nolan");
    await expect(page.getByRole("listbox")).toBeVisible({ timeout: 15_000 });
    await page.keyboard.press("Escape");
    await expect(page.getByRole("listbox")).toHaveCount(0);
    await page.keyboard.press("Escape");

    await expect(page.getByRole("combobox")).toHaveCount(0);
    await expect(lupa(page)).toBeFocused();
  });

  test("Enter busca el texto en Buscar y «/» abre la lupa", async ({ page }) => {
    await preparar(page);
    await page.goto("/home");

    await page.keyboard.press("/");
    await expect(page.getByRole("combobox")).toBeFocused();
    await page.getByRole("combobox").fill("dune");
    await page.keyboard.press("Enter");

    await expect(page).toHaveURL(/\/search\?q=dune$/);
  });
});

test.describe("lupa de la navbar en celular", () => {
  test.use({ viewport: CELULAR, locale: "en-US" });

  test("no hay lupa: Buscar sigue en la barra inferior", async ({ page }) => {
    await preparar(page);
    await page.goto("/home");

    await expect(
      page.getByRole("banner").getByRole("link", { name: en.nav.account.signUp })
    ).toBeVisible();
    await expect(lupa(page)).toBeHidden();
    await expect(
      page.getByRole("navigation", { name: en.nav.main.mainLabel }).getByRole("link", {
        name: en.nav.main.search,
      })
    ).toBeVisible();
  });
});
