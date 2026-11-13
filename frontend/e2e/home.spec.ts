import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import {
  fall2,
  generosPeliculas,
  generosSeries,
  insidious,
  reacher,
  svu,
} from "../tests/catalog-fixtures";
import { prepararCuenta } from "./cuenta";

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 390, height: 844 },
] as const;

/** API del catálogo simulada con recortes reales de TMDB (13/10/2026). */
async function prepararCatalogo(page: Page) {
  const sinTipo = (item: object) => ({ ...item, media_type: undefined });
  const respuestas: Record<string, unknown> = {
    // 20 tarjetas, como una página real de TMDB: con pocas, un desborde
    // horizontal de la fila no se nota.
    "trending:all": {
      results: [
        insidious,
        reacher,
        ...Array.from({ length: 18 }, (_, i) => ({
          ...fall2,
          media_type: "movie",
          id: fall2.id + i + 1,
        })),
      ],
    },
    "trending:movie": { results: [insidious, { ...fall2, media_type: "movie" }] },
    "trending:tv": { results: [svu, reacher] },
    "now-playing": { results: [sinTipo(fall2), sinTipo(insidious)] },
    discover: { results: [sinTipo(reacher)] },
    recommended: {
      generos: ["Thriller", "Drama", "Crime"],
      results: [{ ...fall2, media_type: "movie" }],
    },
    "genres:movie": { genres: generosPeliculas },
    "genres:tv": { genres: generosSeries },
  };
  await page.route("**/api/catalogo/**", (route) => {
    const url = new URL(route.request().url());
    const [, , recurso] = url.pathname.split("/").filter(Boolean);
    const clave =
      recurso === "trending"
        ? `trending:${url.searchParams.get("media_type")}`
        : recurso === "genres"
          ? `genres:${url.searchParams.get("tipo")}`
          : recurso;
    return route.fulfill({ json: respuestas[clave] });
  });
  // Las imágenes de TMDB salen de un archivo local: el CI no depende de internet.
  await page.route("https://image.tmdb.org/**", (route) =>
    route.fulfill({ path: "public/collage-posters/Opcion 1.jpg" })
  );
}

/** Lista Pendientes del usuario (id 5) con los títulos dados, o vacía. */
async function prepararPendientes(page: Page, titulos: { id: number; titulo: string }[]) {
  await page.route("**/api/lists/**", (route) => {
    const { pathname } = new URL(route.request().url());
    if (pathname.endsWith("/items/"))
      return route.fulfill({
        json: {
          next: null,
          total: titulos.length,
          results: titulos.map(({ id, titulo }, indice) => ({
            item_id: indice + 1,
            fecha_agregado: "2026-11-10T12:00:00Z",
            id_tmdb: id,
            tipo: "movie",
            titulo,
            poster: "/alien.jpg",
            anio: 1979,
            calificacion_promedio: 8.1,
          })),
        },
      });
    return route.fulfill({
      json: [
        {
          id: 5,
          nombre: "Pendientes",
          clave: "pendientes",
          tipo: "predeterminada",
          cantidad_items: titulos.length,
          cantidad_peliculas: titulos.length,
          cantidad_series: 0,
          preview_posters: [],
        },
      ],
    });
  });
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

for (const viewport of viewports) {
  test.describe(`Home en ${viewport.name}`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      locale: "en-US",
      extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
    });

    test("sin sesión: Hero, filas públicas e invitación a registrarse", async ({ page }) => {
      await sinSesion(page);
      await prepararCatalogo(page);
      await page.goto("/home");

      await expect(page.getByRole("heading", { level: 1 })).toHaveText(insidious.title!);
      await expect(page.getByRole("region", { name: en.home.rows.trendingTitle })).toBeVisible();
      await expect(page.getByRole("region", { name: en.home.rows.newReleasesTitle })).toBeVisible();
      await expect(page.getByRole("region", { name: en.home.guest.title })).toBeVisible();
      await expect(page.getByRole("region", { name: en.home.rows.recommendedTitle })).toHaveCount(
        0
      );
      // El footer también enlaza «Ask FilmAI»; en <main> no queda ningún enlace con ese nombre.
      await expect(
        page.getByRole("main").getByRole("link", { name: en.footer.main.askFilmAI })
      ).toHaveCount(0);
      await sinDesborde(page);
    });

    test("con sesión: Recomendado, Ask FilmAI y selector en la URL", async ({ page }) => {
      await prepararCuenta(page);
      await prepararCatalogo(page);
      await prepararPendientes(page, [{ id: 348, titulo: "Alien" }]);
      await page.goto("/home");

      const recomendado = page.getByRole("region", { name: en.home.rows.recommendedTitle });
      await expect(recomendado).toBeVisible();
      await expect(
        recomendado.getByText("Based on your high ratings in Thriller, Drama, and Crime")
      ).toBeVisible();
      await expect(page.getByRole("region", { name: en.home.guest.title })).toHaveCount(0);
      // «Ask FilmAI» ya no es un enlace de la Home: es el FAB global del chat (PR 6).
      await expect(
        page.getByRole("main").getByRole("link", { name: en.footer.main.askFilmAI })
      ).toHaveCount(0);
      await expect(
        page.getByRole("button", { name: en.footer.main.askFilmAI }).first()
      ).toBeEnabled();

      // Pendientes va última, después de Novedades, con «See all» a la lista.
      const pendientes = page.getByRole("region", { name: en.enums.defaultList.pendientes });
      await expect(pendientes.getByRole("link", { name: "Alien" })).toHaveAttribute(
        "href",
        "/movie/348?from=list-5"
      );
      await expect(pendientes.getByRole("link", { name: en.home.rows.seeAll })).toHaveAttribute(
        "href",
        "/lists/5"
      );

      await page.getByRole("button", { name: en.common.content.tvShows }).click();
      await expect(page).toHaveURL(/\/home\?type=tv$/);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(svu.name!);
      await expect(page.getByText(en.home.hero.weeklyHighlight)).toBeVisible();
      await sinDesborde(page);
    });
  });
}

test.describe("Hero en escritorio", () => {
  test.use({
    viewport: { width: 1440, height: 900 },
    locale: "en-US",
    extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
  });

  test("en escritorio la barra va sobre la imagen del Hero", async ({ page }) => {
    await sinSesion(page);
    await prepararCatalogo(page);
    await page.goto("/home");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    const barra = await page.locator("header").first().boundingBox();
    const hero = await page.locator("section", { has: page.locator("h1") }).boundingBox();
    expect(barra?.y).toBe(0);
    expect(hero?.y).toBe(0);
  });

  test("un título largo no se sube encima del selector", async ({ page }) => {
    // «Law & Order: Special Victims Unit» a 152 px ocupa varios renglones.
    await sinSesion(page);
    await prepararCatalogo(page);
    await page.goto("/home?type=tv");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(svu.name!);

    const selector = await page
      .getByRole("group", { name: en.common.content.typeLabel })
      .boundingBox();
    const etiqueta = await page.getByText(en.home.hero.weeklyHighlight).boundingBox();
    // Además del orden, un mínimo de aire entre los dos (48 px en el código).
    expect(etiqueta!.y - (selector!.y + selector!.height)).toBeGreaterThanOrEqual(40);
    // La letra se achica según el largo: un título de 33 caracteres no pasa de dos renglones.
    const renglones = await page.getByRole("heading", { level: 1 }).evaluate((h1) => {
      const alto = h1.getBoundingClientRect().height;
      return Math.round(alto / parseFloat(getComputedStyle(h1).lineHeight));
    });
    expect(renglones).toBeLessThanOrEqual(2);
  });
});

test.describe("Flechas de las filas en escritorio", () => {
  test.use({
    viewport: { width: 1440, height: 900 },
    locale: "en-US",
    extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
  });

  test("aparecen al pasar el mouse, sin izquierda al principio, y quedan a la altura de los pósters", async ({
    page,
  }) => {
    await sinSesion(page);
    await prepararCatalogo(page);
    await page.goto("/home");

    const fila = page.getByRole("region", { name: en.home.rows.trendingTitle });
    const siguiente = fila.getByRole("button", { name: /^Next in/ });
    const anterior = fila.getByRole("button", { name: /^Previous in/ });
    await expect(fila.getByRole("link").first()).toBeVisible();
    await expect(siguiente).toHaveCount(1);
    await expect(anterior).toHaveCount(0);

    // Sin el mouse encima la banda es transparente; con él, visible.
    await expect(siguiente).toHaveCSS("opacity", "0");
    await fila.getByRole("link").first().hover();
    await expect(siguiente).toHaveCSS("opacity", "1");

    // Mide lo que el póster: el alto de la banda es el de la imagen, no el de la tarjeta con su texto.
    const banda = await siguiente.boundingBox();
    const poster = await fila.getByRole("link").first().locator("> span").first().boundingBox();
    expect(Math.abs(banda!.height - poster!.height)).toBeLessThanOrEqual(2);

    await siguiente.click();
    await expect(anterior).toHaveCount(1);
  });
});
