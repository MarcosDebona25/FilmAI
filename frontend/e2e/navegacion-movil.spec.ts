import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import { fall2, insidious, reacher, svu } from "../tests/catalog-fixtures";
import { prepararCuenta } from "./cuenta";

/** Celulares chicos y grandes, y el borde justo antes de `md` (768 px). */
const celulares = [
  { width: 320, height: 568 },
  { width: 375, height: 667 },
  { width: 390, height: 844 },
  { width: 767, height: 1024 },
] as const;
const escritorios = [
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
] as const;

const idioma = {
  locale: "en-US",
  extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
};

/**
 * Catálogo simulado: una sola respuesta sirve para el Home y para el buscador
 * (`results` para filas y grilla, `genres` para los filtros). Con `q`, el
 * buscador devuelve solo dos títulos, así se distingue la búsqueda del listado.
 */
async function prepararCatalogo(page: Page) {
  await page.route("**/api/catalogo/**", (route) => {
    const params = new URL(route.request().url()).searchParams;
    const results = params.get("q")
      ? [svu, reacher]
      : [insidious, reacher, { ...fall2, media_type: "movie" }, svu];
    return route.fulfill({
      json: {
        page: 1,
        total_pages: 1,
        total_results: results.length,
        results,
        genres: [{ id: 18, name: "Drama" }],
        generos: [],
      },
    });
  });
  await page.route("https://image.tmdb.org/**", (route) =>
    route.fulfill({ path: "public/collage-posters/Opcion 1.jpg" })
  );
}

async function sinSesion(page: Page) {
  await page.route("**/api/profile/", (route) =>
    route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
  );
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

/** La barra inferior; en escritorio la navegación del encabezado lleva el mismo nombre. */
const barra = (page: Page) =>
  page.getByRole("navigation", { name: en.nav.main.mainLabel }).filter({
    has: page.getByRole("link", { name: en.nav.main.home }),
  });

for (const viewport of celulares) {
  test.describe(`navegación sin sesión a ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport, ...idioma });

    test("la barra inferior lleva al buscador y la búsqueda muestra resultados", async ({
      page,
    }) => {
      await sinSesion(page);
      await prepararCatalogo(page);
      await page.goto("/home");

      const nav = barra(page);
      await expect(nav).toBeVisible();
      const links = nav.getByRole("link");
      await expect(links).toHaveCount(3);
      expect(await links.evaluateAll((all) => all.map((a) => a.getAttribute("href")))).toEqual([
        "/home",
        "/search",
        "/login",
      ]);
      await expect(nav.getByRole("link", { name: en.nav.main.lists })).toHaveCount(0);
      await expect(nav.getByRole("link", { name: en.nav.main.profileShort })).toHaveCount(0);

      // Objetivos táctiles de al menos 44 × 44 px (WCAG 2.5.5).
      for (const caja of await links.evaluateAll((all) =>
        all.map((a) => a.getBoundingClientRect().toJSON() as DOMRect)
      )) {
        expect(caja.width).toBeGreaterThanOrEqual(44);
        expect(caja.height).toBeGreaterThanOrEqual(44);
      }

      // En el encabezado queda solo Sign up; Log in está en la barra.
      const encabezado = page.getByRole("banner");
      await expect(encabezado.getByRole("link", { name: en.nav.account.signUp })).toBeVisible();
      await expect(encabezado.getByRole("link", { name: en.nav.account.logIn })).toBeHidden();
      await sinDesborde(page);

      await nav.getByRole("link", { name: en.nav.main.search }).click();
      await expect(page).toHaveURL(/\/search$/);
      await expect(nav.getByRole("link", { name: en.nav.main.search })).toHaveAttribute(
        "aria-current",
        "page"
      );

      await page.getByRole("searchbox").fill("law");
      await expect(page.getByRole("main").getByRole("status")).toHaveText("2 results for “law”");
      await expect(
        page.getByRole("link", { name: /Law & Order: Special Victims Unit/ })
      ).toBeVisible();
      await sinDesborde(page);
    });

    test("Log in de la barra inferior lleva al ingreso", async ({ page }) => {
      await sinSesion(page);
      await prepararCatalogo(page);
      await page.goto("/search");

      await barra(page).getByRole("link", { name: en.nav.account.logIn }).click();
      await expect(page).toHaveURL(/\/login$/);
      await expect(
        page.getByRole("heading", { name: en.nav.account.logIn, level: 1 })
      ).toBeVisible();
      // En las pantallas de acceso la barra no se muestra.
      await expect(page.getByRole("link", { name: en.nav.main.search })).toHaveCount(0);
    });
  });
}

for (const viewport of escritorios) {
  test.describe(`navegación sin sesión a ${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport, ...idioma });

    test("sin barra inferior: Search y Log in están en el encabezado", async ({ page }) => {
      await sinSesion(page);
      await prepararCatalogo(page);
      await page.goto("/home");

      const encabezado = page.getByRole("banner");
      await expect(encabezado.getByRole("link", { name: en.nav.main.search })).toBeVisible();
      await expect(encabezado.getByRole("link", { name: en.nav.account.logIn })).toBeVisible();
      await expect(encabezado.getByRole("link", { name: en.nav.account.signUp })).toBeVisible();
      // La única navegación principal visible es la del encabezado.
      await expect(
        page.getByRole("navigation", { name: en.nav.main.mainLabel, includeHidden: false })
      ).toHaveCount(1);
      await expect(page.locator("nav.fixed")).toBeHidden();
      await sinDesborde(page);
    });
  });
}

test.describe("navegación con sesión a 390×844", () => {
  test.use({ viewport: { width: 390, height: 844 }, ...idioma });

  test("la barra inferior mantiene sus cuatro pestañas", async ({ page }) => {
    await prepararCuenta(page);
    await prepararCatalogo(page);
    await page.goto("/search");

    const nav = barra(page);
    await expect(nav).toBeVisible();
    await expect(nav.getByRole("link")).toHaveCount(4);
    expect(
      await nav.getByRole("link").evaluateAll((all) => all.map((a) => a.getAttribute("href")))
    ).toEqual(["/home", "/search", "/lists", "/profile"]);
    await expect(nav.getByRole("link", { name: en.nav.account.logIn })).toHaveCount(0);
    await sinDesborde(page);
  });
});
