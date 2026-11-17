import { expect, test, type Page } from "@playwright/test";

import {
  fall2,
  generosPeliculas,
  generosSeries,
  insidious,
  reacher,
} from "../tests/catalog-fixtures";
import { auditar } from "./axe";
import { prepararCuenta } from "./cuenta";

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 390, height: 844 },
] as const;

async function simularCatalogo(page: Page) {
  await page.route("**/api/catalogo/**", (route) => {
    const url = new URL(route.request().url());
    const recurso = url.pathname.split("/").filter(Boolean)[2];
    if (recurso === "genres")
      return route.fulfill({
        json: { genres: url.searchParams.get("tipo") === "tv" ? generosSeries : generosPeliculas },
      });
    if (recurso === "recommended") return route.fulfill({ json: { generos: [], results: [] } });
    return route.fulfill({
      json: { page: 1, total_pages: 1, total_results: 3, results: [insidious, fall2, reacher] },
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

for (const viewport of viewports) {
  test.describe(`axe en ${viewport.name}`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      locale: "en-US",
      extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
    });

    test("Inicio sin sesión", async ({ page }) => {
      await sinSesion(page);
      await simularCatalogo(page);
      await page.goto("/home");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await auditar(page);
    });

    test("Registro", async ({ page }) => {
      await sinSesion(page);
      await page.goto("/register");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await auditar(page);
    });

    test("Buscar", async ({ page }) => {
      await sinSesion(page);
      await simularCatalogo(page);
      await page.goto("/search?q=law");
      await expect(page.getByRole("main").getByRole("status")).not.toBeEmpty();
      await auditar(page);
    });

    test("Perfil con sesión", async ({ page }) => {
      await prepararCuenta(page);
      await page.goto("/profile");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await auditar(page);
    });
  });
}
