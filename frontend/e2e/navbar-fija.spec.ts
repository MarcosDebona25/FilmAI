import { expect, test, type Page } from "@playwright/test";

import { simularCatalogo, sinSesion } from "./api-simulada";

/**
 * Navbar fija en escritorio: la posición y el fondo dependen del scroll real,
 * así que no se pueden probar en jsdom.
 */
const ESCRITORIO = { width: 1280, height: 720 };
const CELULAR = { width: 390, height: 844 };

async function abrir(page: Page, ruta: string) {
  await sinSesion(page);
  await simularCatalogo(page);
  await page.goto(ruta);
  await expect(page.locator("header a[href='/register']")).toBeVisible({ timeout: 30_000 });
}

async function bajarHasta(page: Page, y: number) {
  await page.evaluate((top) => window.scrollTo({ top, behavior: "instant" }), y);
}

const barra = (page: Page) =>
  page.locator("header").evaluate((elemento) => {
    const estilo = getComputedStyle(elemento);
    return {
      top: elemento.getBoundingClientRect().top,
      alto: elemento.getBoundingClientRect().height,
      desenfoque: estilo.backdropFilter.includes("blur"),
      fondo: estilo.backgroundColor,
    };
  });

const TRANSPARENTE = "rgba(0, 0, 0, 0)";
const SOLIDO = "rgb(13, 13, 20)";

test.describe("navbar", () => {
  test.describe("en escritorio", () => {
    test.use({ viewport: ESCRITORIO });

    for (const [nombre, ruta] of [
      ["el Inicio", "/home"],
      ["la ficha", "/movie/157336"],
    ]) {
      test(`en ${nombre} cambia de fondo y no se va`, async ({ page }) => {
        await abrir(page, ruta);
        const imagen = page.locator("[data-imagen-bajo-navbar]");
        await expect(imagen).toBeVisible();
        expect((await barra(page)).fondo).toBe(TRANSPARENTE);

        await bajarHasta(page, 150);
        await expect.poll(async () => (await barra(page)).desenfoque).toBe(true);
        expect((await barra(page)).top).toBe(0);

        const caja = await imagen.boundingBox();
        await bajarHasta(page, 150 + caja!.y + caja!.height);
        await expect.poll(async () => (await barra(page)).fondo).toBe(SOLIDO);
        const final = await barra(page);
        expect(final.top).toBe(0);
        expect(final.desenfoque).toBe(false);

        await bajarHasta(page, 0);
        await expect.poll(async () => (await barra(page)).fondo).toBe(TRANSPARENTE);
      });
    }

    test("en una página sin imagen queda arriba con fondo sólido", async ({ page }) => {
      await abrir(page, "/terms");

      await bajarHasta(page, 500);

      await expect.poll(async () => (await barra(page)).fondo).toBe(SOLIDO);
      expect((await barra(page)).top).toBe(0);
    });

    test("el índice de Términos no queda debajo de la barra", async ({ page }) => {
      await abrir(page, "/terms");
      const indice = page.locator("main nav:visible").last();

      await bajarHasta(page, 800);

      await expect
        .poll(async () => (await indice.boundingBox())!.y)
        .toBeGreaterThanOrEqual((await barra(page)).alto);
    });
  });

  test.describe("al navegar en escritorio", () => {
    test.use({ viewport: ESCRITORIO });

    test("la página nueva arranca arriba aunque se haya bajado poco", async ({ page }) => {
      // Con menos scroll que el alto de la barra, el comienzo de la página nueva
      // sigue a la vista y Next no la movía: la barra fija la tapaba.
      await abrir(page, "/terms");
      await bajarHasta(page, 60);
      await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(60);

      await page.locator("header nav a[href='/search']").click();
      await page.waitForURL("**/search");

      await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
    });

    test("volver atrás devuelve el scroll de la página anterior", async ({ page }) => {
      await abrir(page, "/terms");
      await bajarHasta(page, 900);
      await page.locator("header nav a[href='/search']").click();
      await page.waitForURL("**/search");

      await page.goBack();
      await page.waitForURL("**/terms");

      await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(800);
    });

    test("en login no se reserva espacio arriba: ahí no hay barra", async ({ page }) => {
      await sinSesion(page);
      await page.goto("/login");
      // Login tiene su propio `header` (el selector de idioma): se busca la navbar.
      await expect(page.locator("header[data-navbar]")).toHaveCount(0);

      const padding = await page.evaluate(
        () => getComputedStyle(document.documentElement).scrollPaddingTop
      );
      expect(padding).toBe("auto");
    });
  });

  test.describe("en celular", () => {
    test.use({ viewport: CELULAR });

    test("se va con la página y no cambia de fondo", async ({ page }) => {
      await abrir(page, "/movie/157336");

      await bajarHasta(page, 300);

      await expect.poll(async () => (await barra(page)).top).toBeLessThan(0);
      expect((await barra(page)).fondo).toBe(TRANSPARENTE);
    });
  });
});
