import { expect, test, type Page } from "@playwright/test";

import { conSesion, simularCatalogo, simularListas } from "./api-simulada";

/**
 * Menú «Add to list» de la ficha. La rueda y la posición dependen del navegador
 * real (capa superior del `<dialog>`, scroll sobre su fondo), así que no se
 * pueden probar en jsdom.
 */
const ESCRITORIO = { width: 1280, height: 720 };
const CELULAR = { width: 390, height: 844 };

const boton = (page: Page) => page.getByRole("button", { name: /Add Interstellar to/ });
const panel = (page: Page) => page.locator("dialog[open]");
const scrollY = (page: Page) => page.evaluate(() => window.scrollY);

async function abrirFicha(page: Page) {
  await conSesion(page);
  await simularCatalogo(page);
  await simularListas(page);
  await page.goto("/movie/157336");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Interstellar", {
    timeout: 30_000,
  });
  await expect(boton(page)).toBeVisible();
}

/** Desplaza la página hasta dejar el borde superior del botón en `top`. */
async function llevarBotonA(page: Page, top: number) {
  await boton(page).evaluate((elemento, destino) => {
    const actual = elemento.getBoundingClientRect().top;
    window.scrollBy({ top: actual - destino, behavior: "instant" });
  }, top);
  const caja = await boton(page).boundingBox();
  expect(Math.abs(caja!.y - top)).toBeLessThan(2);
}

async function cajas(page: Page) {
  const [menu, disparador] = await Promise.all([
    panel(page).boundingBox(),
    boton(page).boundingBox(),
  ]);
  return { menu: menu!, disparador: disparador! };
}

test.describe("menú «Add to list»", () => {
  test.describe("en escritorio", () => {
    test.use({ viewport: ESCRITORIO });

    test("cerca del borde inferior se abre hacia arriba y entra entero", async ({ page }) => {
      // Ventana baja: sin desplazar, el botón ya queda cerca del borde inferior.
      await page.setViewportSize({ width: ESCRITORIO.width, height: 600 });
      await abrirFicha(page);

      await boton(page).click();

      const { menu, disparador } = await cajas(page);
      expect(disparador.y + disparador.height + menu.height).toBeGreaterThan(600);
      expect(menu.y + menu.height).toBeLessThanOrEqual(disparador.y);
      expect(menu.y).toBeGreaterThanOrEqual(0);
    });

    test("con lugar abajo se abre hacia abajo", async ({ page }) => {
      await abrirFicha(page);
      await llevarBotonA(page, 120);

      await boton(page).click();

      const { menu, disparador } = await cajas(page);
      expect(menu.y).toBeGreaterThanOrEqual(disparador.y + disparador.height);
      expect(menu.y + menu.height).toBeLessThanOrEqual(ESCRITORIO.height);
    });

    test("la rueda desplaza la página desde el fondo y el panel sigue al botón", async ({
      page,
    }) => {
      await abrirFicha(page);
      await llevarBotonA(page, 200);
      await boton(page).click();
      await expect(panel(page)).toBeVisible();
      const antes = await scrollY(page);

      await page.mouse.move(20, 400);
      await page.mouse.wheel(0, 60);

      await expect.poll(() => scrollY(page)).toBeGreaterThan(antes);
      await expect
        .poll(async () => {
          const { menu, disparador } = await cajas(page);
          return Math.round(menu.y - (disparador.y + disparador.height));
        })
        .toBe(8);
    });

    test("la rueda también desplaza la página con el puntero sobre el panel", async ({ page }) => {
      await abrirFicha(page);
      await llevarBotonA(page, 200);
      await boton(page).click();
      const { menu } = await cajas(page);
      const antes = await scrollY(page);

      await page.mouse.move(menu.x + menu.width / 2, menu.y + menu.height / 2);
      await page.mouse.wheel(0, 60);

      await expect.poll(() => scrollY(page)).toBeGreaterThan(antes);
    });
  });

  test.describe("con el menú abierto", () => {
    test.use({ viewport: ESCRITORIO });

    test("si el botón sale de la ventana, el panel sigue a la vista", async ({ page }) => {
      await abrirFicha(page);
      await llevarBotonA(page, 200);
      await boton(page).click();
      await expect(panel(page)).toBeVisible();

      await llevarBotonA(page, -150);

      await expect.poll(async () => (await panel(page).boundingBox())!.y).toBe(16);
    });

    test("cruzar el corte de 768 px cambia el bloqueo de la página", async ({ page }) => {
      const desborde = () => page.evaluate(() => document.body.style.overflow);
      await abrirFicha(page);
      await boton(page).click();
      await expect(panel(page)).toBeVisible();
      expect(await desborde()).toBe("");

      await page.setViewportSize(CELULAR);
      await expect.poll(desborde).toBe("hidden");

      await page.setViewportSize(ESCRITORIO);
      await expect.poll(desborde).toBe("");
    });
  });

  test.describe("en celular", () => {
    test.use({ viewport: CELULAR });

    test("la hoja deja la página quieta", async ({ page }) => {
      await abrirFicha(page);
      await boton(page).click();
      await expect(panel(page)).toBeVisible();
      const antes = await scrollY(page);

      await page.mouse.move(195, 100);
      await page.mouse.wheel(0, 200);
      await page.waitForTimeout(300);

      expect(await scrollY(page)).toBe(antes);
    });
  });
});
