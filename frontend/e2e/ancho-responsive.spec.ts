import { expect, test, type Locator, type Page } from "@playwright/test";

import { conSesion, simularCatalogo, simularListas, sinSesion } from "./api-simulada";

/**
 * Maquetación por ancho (opción C): contenedor único, escala de la raíz desde
 * 1440 px y filas/grillas con `--cols` tarjetas enteras. Recorre del celular más
 * chico a una pantalla 2560 con la API simulada.
 */
const VIEWPORTS = [
  { width: 320, height: 568 },
  { width: 375, height: 667 },
  { width: 390, height: 844 },
  { width: 767, height: 1024 },
  { width: 768, height: 1024 },
  { width: 1024, height: 768 },
  { width: 1280, height: 800 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
] as const;

const MARCA = "FilmAI, go to Home";

/** Columnas esperadas (globals.css, `--cols`). */
function columnas(ancho: number) {
  if (ancho >= 1440) return 7;
  if (ancho >= 1280) return 6;
  if (ancho >= 1024) return 5;
  if (ancho >= 768) return 4;
  return 2;
}

/** Tamaño de la raíz esperado: 16 px hasta 1440, después 60 % + 0,4444vw con tope 130 %. */
function raizEsperada(ancho: number) {
  if (ancho < 1440) return 16;
  return Math.min(20.8, 9.6 + 0.004444 * ancho);
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

async function izquierda(locator: Locator) {
  const caja = await locator.boundingBox();
  expect(caja).not.toBeNull();
  return caja!.x;
}

/** Cuántas tarjetas entran enteras en la fila y cuál es la primera visible. */
async function visibles(fila: Locator) {
  return fila.evaluate((ul) => {
    const caja = ul.getBoundingClientRect();
    const items = [...ul.querySelectorAll(":scope > li")].map((li) => li.getBoundingClientRect());
    const enteras = items
      .map((r, indice) => ({ r, indice }))
      .filter(({ r }) => r.left >= caja.left - 1 && r.right <= caja.right + 1);
    return {
      cantidad: enteras.length,
      primera: enteras[0]?.indice ?? -1,
      ultimaDerecha: enteras.at(-1)?.r.right ?? 0,
      derecha: caja.right,
    };
  });
}

/** Columnas de una grilla: cuántos `li` comparten el renglón del primero. */
async function columnasDeGrilla(grilla: Locator) {
  return grilla.evaluate((ul) => {
    const items = [...ul.querySelectorAll(":scope > li")].map((li) => li.getBoundingClientRect());
    return items.filter((r) => Math.abs(r.top - items[0].top) < 1).length;
  });
}

test.use({
  locale: "en-US",
  extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
  // Las flechas se desplazan sin animación: el scroll queda donde termina.
  reducedMotion: "reduce",
});

for (const viewport of VIEWPORTS) {
  const cols = columnas(viewport.width);
  const escritorio = viewport.width >= 768;

  test.describe(`${viewport.width}×${viewport.height}`, () => {
    test.use({ viewport });

    test("sin sesión: Home, Buscar, ficha, Términos y 404", async ({ page }) => {
      test.setTimeout(90_000);
      await sinSesion(page);
      await simularCatalogo(page);

      // Home
      await page.goto("/home");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 30_000 });
      const filas = page.getByRole("list", { name: /swipe to see more/ });
      await expect(filas.first().getByRole("link").first()).toBeVisible();
      await sinDesborde(page);

      const raiz = await page.evaluate(() =>
        parseFloat(getComputedStyle(document.documentElement).fontSize)
      );
      expect(Math.abs(raiz - raizEsperada(viewport.width))).toBeLessThanOrEqual(
        viewport.width === 1920 ? 0.3 : 0.05
      );

      if (escritorio) {
        for (const fila of await filas.all()) {
          await expect(fila.getByRole("link").first()).toBeVisible();
          const v = await visibles(fila);
          expect(v.cantidad).toBe(cols);
          expect(v.primera).toBe(0);
          expect(v.ultimaDerecha).toBeLessThanOrEqual(v.derecha + 1);
        }

        // «Siguiente» avanza exactamente una página: la tarjeta cols + 1 queda primera.
        const tendencias = page.getByRole("region", { name: "Trending this week" });
        await tendencias.getByRole("button", { name: /^Next in/ }).click();
        const lista = tendencias.getByRole("list");
        await expect
          .poll(async () => (await visibles(lista)).primera, { timeout: 5_000 })
          .toBe(cols);
        expect((await visibles(lista)).cantidad).toBe(cols);

        // Logo de la barra, contenido y pie arrancan en el mismo borde.
        const logo = await izquierda(page.getByRole("banner").getByRole("link", { name: MARCA }));
        const contenido = await izquierda(
          tendencias.getByRole("heading", { name: "Trending this week" })
        );
        const pie = await izquierda(
          page.getByRole("contentinfo").getByRole("link", { name: MARCA })
        );
        expect(Math.abs(logo - contenido)).toBeLessThanOrEqual(1);
        expect(Math.abs(pie - contenido)).toBeLessThanOrEqual(1);
      } else {
        // Celular (opción B): el encabezado solo tiene Sign up; Home, Search y
        // Log in están en la barra inferior. Todos se tocan cómodos.
        const objetivos = [
          page.getByRole("banner").getByRole("link", { name: "Sign up", exact: true }),
          ...["Home", "Search", "Log in"].map((nombre) =>
            page
              .getByRole("navigation", { name: "Main" })
              .getByRole("link", { name: nombre, exact: true })
          ),
        ];
        for (const objetivo of objetivos) {
          const caja = await objetivo.boundingBox();
          expect(caja!.height).toBeGreaterThanOrEqual(44);
        }
      }

      // Buscar con resultados
      await page.goto("/search?q=dune");
      const resultados = page
        .getByRole("main")
        .getByRole("list")
        .filter({
          has: page.getByRole("link"),
        });
      await expect(resultados.getByRole("link").first()).toBeVisible({ timeout: 30_000 });
      await sinDesborde(page);
      expect(await columnasDeGrilla(resultados.first())).toBe(cols);
      if (escritorio) {
        const logo = await izquierda(page.getByRole("banner").getByRole("link", { name: MARCA }));
        expect(Math.abs(logo - (await izquierda(page.getByRole("searchbox"))))).toBeLessThanOrEqual(
          1
        );
      }

      // Ficha
      await page.goto("/movie/157336");
      await expect(page.getByRole("heading", { level: 1 })).toHaveText("Interstellar", {
        timeout: 30_000,
      });
      await sinDesborde(page);

      // Términos y 404
      await page.goto("/terms");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 30_000 });
      await sinDesborde(page);
      await page.goto("/no-existe");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 30_000 });
      await sinDesborde(page);
    });

    test("con sesión: Listas y detalle de una lista", async ({ page }) => {
      test.setTimeout(90_000);
      await conSesion(page);
      await simularCatalogo(page);
      await simularListas(page);

      await page.goto("/lists");
      await expect(page.getByText("Marathon").first()).toBeVisible({ timeout: 30_000 });
      await sinDesborde(page);
      if (!escritorio) {
        // La barra inferior: cada pestaña mide al menos 44 px.
        const pestanas = page.getByRole("navigation", { name: "Main" }).last().getByRole("link");
        await expect(pestanas).toHaveCount(4);
        for (const pestana of await pestanas.all()) {
          const caja = await pestana.boundingBox();
          expect(caja!.height).toBeGreaterThanOrEqual(44);
          expect(caja!.width).toBeGreaterThanOrEqual(44);
        }
      }

      await page.goto("/lists/1");
      const grilla = page
        .getByRole("main")
        .getByRole("list")
        .filter({ has: page.getByRole("link", { name: /Title 01/ }) });
      await expect(grilla.getByRole("link").first()).toBeVisible({ timeout: 30_000 });
      await sinDesborde(page);
      expect(await columnasDeGrilla(grilla)).toBe(cols);
    });
  });
}
