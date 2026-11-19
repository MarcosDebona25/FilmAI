import { expect, test, type Page } from "@playwright/test";

import { CREDITOS_INTERSTELLAR, INTERSTELLAR } from "../tests/title-fixtures";
import { auditar } from "./axe";

/**
 * Fila «More like {title}» de la ficha (canvas, sección 14). La API se simula:
 * no hace falta el backend.
 */

const viewports = [
  { name: "escritorio", width: 1440, height: 900, movil: false },
  { name: "celular", width: 375, height: 812, movil: true },
] as const;

const PARECIDOS = [
  "Blade Runner 2049",
  "Arrival",
  "The Odyssey",
  "Ex Machina",
  "Contact",
  "Runner",
  "Foundation",
  "Annihilation",
  "Moon",
  "Solaris",
  "Gattaca",
  "Sunshine",
  "Primer",
  "Coherence",
  "Silo",
  "Gravity",
  "The Martian",
  "Ad Astra",
  "Oblivion",
  "Tenet",
].map((titulo, indice) => ({
  id_tmdb: 7000 + indice,
  tipo: titulo === "Foundation" || titulo === "Silo" ? ("tv" as const) : ("movie" as const),
  titulo,
  poster: indice % 3 === 2 ? `/parecido-${indice}.jpg` : null,
  anio: 2000 + indice,
  calificacion_promedio: 7.6,
  origen: "catalogo" as const,
}));

/** Ficha sin sesión con `similar/` configurable; devuelve los pedidos de la fila. */
async function prepararFicha(page: Page, parecidos: "datos" | "vacio" | "error" = "datos") {
  const pedidos: string[] = [];
  const noEncontrado = { status: 404, json: { code: "not_found", params: {}, errors: [] } };
  await page.route("**/api/profile/", (route) =>
    route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
  );
  await page.route("https://image.tmdb.org/**", (route) =>
    route.fulfill({ path: "public/collage-posters/Opcion 1.jpg" })
  );
  await page.route("**/api/reviews/**", (route) =>
    route.fulfill({
      json: { total: 0, total_comunidad: 0, next: null, previous: null, results: [] },
    })
  );
  await page.route("**/api/catalogo/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/credits/")) return route.fulfill({ json: CREDITOS_INTERSTELLAR });
    if (path.endsWith("/similar/")) {
      pedidos.push(path);
      if (parecidos === "error")
        return route.fulfill({
          status: 502,
          json: { code: "upstream_error", params: {}, errors: [] },
        });
      return route.fulfill({ json: { results: parecidos === "datos" ? PARECIDOS : [] } });
    }
    if (path.endsWith("/providers/")) return route.fulfill(noEncontrado);
    return route.fulfill({ json: INTERSTELLAR });
  });
  return pedidos;
}

const fila = (page: Page) => page.getByRole("region", { name: "More like Interstellar" });
const resenas = (page: Page) => page.getByRole("heading", { name: /^From the community/ });

for (const viewport of viewports) {
  test.describe(`Parecidos en la ficha en ${viewport.name}`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      locale: "en-US",
      extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
    });

    test("la fila se pide al acercarse y es la del Inicio, entre los créditos y las reseñas", async ({
      page,
    }) => {
      const pedidos = await prepararFicha(page);
      await page.goto("/movie/157336?from=search");
      await expect(page.getByRole("heading", { name: "Director and cast" })).toBeVisible();
      await expect(resenas(page)).toBeVisible();

      await resenas(page).scrollIntoViewIfNeeded();
      const tarjetas = fila(page).getByRole("listitem");
      await expect(tarjetas).toHaveCount(20);
      expect(pedidos).toEqual(["/api/catalogo/movie/157336/similar/"]);
      await expect(fila(page).getByRole("heading", { level: 2 })).toHaveText(
        "More like Interstellar"
      );

      // Después de «Director and cast» y antes de las reseñas.
      const creditos = await page.getByRole("heading", { name: "Director and cast" }).boundingBox();
      const caja = await fila(page).boundingBox();
      const comunidad = await resenas(page).boundingBox();
      expect(caja!.y).toBeGreaterThan(creditos!.y);
      expect(caja!.y + caja!.height).toBeLessThanOrEqual(comunidad!.y);

      // Cada tarjeta dice su tipo y conserva el origen de la ficha.
      const serie = fila(page).getByRole("link", { name: /Foundation/ });
      await expect(serie).toContainText("TV show");
      await expect(serie).toHaveAttribute("href", "/tv/7006?from=search");

      const lista = fila(page).getByRole("list");
      const enVista = () =>
        tarjetas.evaluateAll((nodos) => {
          const marco = nodos[0].parentElement!.getBoundingClientRect();
          return nodos.filter((nodo) => {
            const caja = nodo.getBoundingClientRect();
            return caja.left >= marco.left - 1 && caja.right <= marco.right + 1;
          }).length;
        });
      if (viewport.movil) {
        // Celular: se desliza con el dedo, con la tarjeta siguiente asomando.
        expect(await lista.evaluate((nodo) => nodo.scrollWidth > nodo.clientWidth)).toBe(true);
        await expect(fila(page).getByRole("button")).toHaveCount(0);
        // De borde a borde, como en el Inicio.
        const borde = await lista.boundingBox();
        expect(Math.round(borde!.x)).toBe(0);
        // El ancho de `main` y no el del viewport: descuenta la barra de scroll.
        const principal = await page.getByRole("main").boundingBox();
        expect(Math.round(borde!.width)).toBe(Math.round(principal!.width));
      } else {
        // Escritorio: 7 tarjetas por vista y las flechas avanzan una página.
        expect(await enVista()).toBe(7);
        await lista.hover();
        await expect(
          fila(page).getByRole("button", { name: "Previous in More like Interstellar" })
        ).toHaveCount(0);
        await fila(page).getByRole("button", { name: "Next in More like Interstellar" }).click();
        await expect(fila(page).getByRole("link", { name: /Annihilation/ })).toBeInViewport({
          ratio: 1,
        });
        await expect(
          fila(page).getByRole("button", { name: "Previous in More like Interstellar" })
        ).toBeVisible();
      }

      // Sin desborde horizontal.
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
      ).toBe(true);
      await auditar(page);
    });

    test("sin bajar no se pide: la fila espera a estar a 400 px del viewport", async ({ page }) => {
      const pedidos = await prepararFicha(page);
      // Con los datos de prueba la ficha es corta y la fila ya queda a menos
      // de 400 px: se corre el contenido hacia abajo para dejarla lejos.
      await page.addInitScript(() => {
        document.addEventListener("DOMContentLoaded", () => {
          const estilo = document.createElement("style");
          estilo.textContent = "main#contenido { padding-top: 1000px; }";
          document.head.append(estilo);
        });
      });
      await page.goto("/movie/157336");
      await expect(page.getByRole("heading", { name: "Director and cast" })).toBeVisible();
      await expect(resenas(page)).toBeVisible();

      expect(pedidos).toEqual([]);
      await expect(fila(page)).toHaveCount(0);

      await resenas(page).scrollIntoViewIfNeeded();
      await expect(fila(page).getByRole("listitem")).toHaveCount(20);
      expect(pedidos).toHaveLength(1);
    });

    test("una tarjeta abre la ficha de ese título", async ({ page }) => {
      await prepararFicha(page);
      await page.goto("/movie/157336");
      await expect(resenas(page)).toBeVisible();
      await resenas(page).scrollIntoViewIfNeeded();

      await fila(page)
        .getByRole("link", { name: /Blade Runner 2049/ })
        .click();
      await expect(page).toHaveURL(/\/movie\/7000$/);
    });

    for (const caso of ["vacio", "error"] as const) {
      test(`sin parecidos (${caso}) la sección no se dibuja`, async ({ page }) => {
        const pedidos = await prepararFicha(page, caso);
        await page.goto("/movie/157336");
        await expect(resenas(page)).toBeVisible();
        await resenas(page).scrollIntoViewIfNeeded();

        await expect.poll(() => pedidos.length).toBe(1);
        await expect(page.getByRole("heading", { name: /^More like/ })).toHaveCount(0);
        await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
        // Las reseñas siguen a los créditos con la separación de siempre.
        await expect(resenas(page)).toBeVisible();
      });
    }
  });
}
