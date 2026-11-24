import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import { fall2, insidious, reacher, svu } from "../tests/catalog-fixtures";

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 390, height: 844 },
] as const;

/** `explore/` simulado: responde datos reales de TMDB y anota cada consulta. */
async function prepararBuscar(page: Page) {
  const consultas: URLSearchParams[] = [];
  await page.route("**/api/profile/", (route) =>
    route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
  );
  await page.route("**/api/catalogo/genres/**", (route) =>
    route.fulfill({
      json: {
        genres: [
          { id: 18, name: "Drama" },
          { id: 878, name: "Science Fiction" },
        ],
      },
    })
  );
  await page.route("**/api/catalogo/suggest/**", (route) =>
    route.fulfill({ json: { results: [] } })
  );
  await page.route("**/api/catalogo/explore/**", (route) => {
    const params = new URL(route.request().url()).searchParams;
    consultas.push(params);
    const results = params.get("q")
      ? [svu, reacher]
      : [insidious, reacher, { ...fall2, media_type: "movie" }, svu];
    return route.fulfill({
      json: { page: 1, total_pages: 2, total_results: results.length * 2, results },
    });
  });
  await page.route("https://image.tmdb.org/**", (route) =>
    route.fulfill({ path: "public/collage-posters/Opcion 1.jpg" })
  );
  return consultas;
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

for (const viewport of viewports) {
  test.describe(`buscar en ${viewport.name}`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      locale: "en-US",
      extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
    });

    test("buscar por texto muestra el contador y las tarjetas llevan a la ficha", async ({
      page,
    }) => {
      const consultas = await prepararBuscar(page);
      await page.goto("/search");
      await expect(page.getByText("Insidious: Out of the Further")).toBeVisible();

      await page.locator("#busqueda").fill("law");

      await expect(page.getByRole("main").getByRole("status")).toHaveText("4 results for “law”");
      // Con pocos resultados la grilla no llena la pantalla: la página 2 se pide sola.
      await expect(page).toHaveURL(/\/search\?q=law(&page=\d+)?$/);
      expect(consultas.at(-1)?.get("q")).toBe("law");
      await expect(
        page.getByRole("link", { name: /Law & Order: Special Victims Unit/ })
      ).toHaveAttribute("href", "/tv/2734?from=search");
      await sinDesborde(page);
    });
  });
}

test.describe("buscar en escritorio", () => {
  test.use({
    viewport: { width: 1440, height: 900 },
    locale: "en-US",
    extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
  });

  test("los filtros viajan a la API y al bajar se pide la página siguiente", async ({ page }) => {
    const consultas = await prepararBuscar(page);
    await page.goto("/search?type=movie");

    await page
      .getByRole("combobox", { name: en.search.filters.genreLabel })
      .selectOption({ label: "Science Fiction" });
    await page.getByRole("combobox", { name: en.common.rating.label }).selectOption("8");
    await expect(page).toHaveURL(/rating=8$/);
    // Carga al bajar: llegar al final de la grilla pide la página siguiente.
    await page.mouse.wheel(0, 20000);

    await expect(page).toHaveURL(/\/search\?type=movie&genre=878&rating=8&page=2$/);
    await expect.poll(() => consultas.at(-1)?.get("page")).toBe("2");
    const ultima = consultas.at(-1)!;
    expect(Object.fromEntries(ultima)).toEqual({
      tipo: "movie",
      genero: "878",
      nota: "8+",
      page: "2",
    });
  });

  test("el menú de orden manda «Highest rated» a la API y «Clear filters» lo conserva", async ({
    page,
  }) => {
    const consultas = await prepararBuscar(page);
    await page.goto("/search?genre=18");

    await page.getByRole("button", { name: "Sort: Popular" }).click();
    await page.getByRole("menuitemradio", { name: en.common.sort.highestRating }).click();

    await expect(page).toHaveURL(/sort=highest/);
    await expect.poll(() => consultas.at(-1)?.get("orden")).toBe("nota-desc");
    // El botón nombra el orden elegido y el menú se cerró.
    await expect(page.getByRole("button", { name: "Sort: Highest rated" })).toBeVisible();
    await expect(page.getByRole("menu")).toBeHidden();

    await page.getByRole("button", { name: en.common.filters.clear }).click();
    // La grilla del mock es corta: el scroll infinito puede pedir ya la página 2.
    await expect(page).toHaveURL(/\/search\?sort=highest(&page=\d+)?$/);
    await expect.poll(() => consultas.at(-1)?.get("orden")).toBe("nota-desc");
    expect(consultas.at(-1)?.get("genero")).toBeNull();
    await sinDesborde(page);
  });

  test("a 1024 px el botón de orden es solo el ícono y la fila entra en una línea", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1024, height: 800 });
    await prepararBuscar(page);
    await page.goto("/search?sort=newest");

    const boton = page.getByRole("button", { name: "Sort: Newest" });
    await expect(boton).toBeVisible();
    await expect(boton.getByText("Newest")).toBeHidden();
    // El selector de tipo, las tres píldoras y el botón de orden, a la misma altura.
    const tops = await page
      .locator("main search")
      .locator("[role=group], label:has(select), button[aria-haspopup=menu]")
      .evaluateAll((nodos) => nodos.map((nodo) => Math.round(nodo.getBoundingClientRect().top)));
    expect(tops).toHaveLength(5);
    expect(new Set(tops).size).toBe(1);
    await sinDesborde(page);
  });
});

test.describe("buscar en celular", () => {
  test.use({
    viewport: { width: 390, height: 844 },
    locale: "en-US",
    extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
  });

  test("la hoja de filtros aplica la nota y el botón cuenta los activos", async ({ page }) => {
    const consultas = await prepararBuscar(page);
    await page.goto("/search");

    await page.getByRole("button", { name: "Filters" }).click();
    const hoja = page.getByRole("dialog", { name: en.reviews.filters.dialogTitle });
    await hoja.getByRole("button", { name: en.common.filters.ratingAtLeastSeven }).click();
    await hoja.getByRole("button", { name: en.search.filters.apply }).click();

    await expect(hoja).toBeHidden();
    await expect(page.getByRole("button", { name: "Filters, 1 active" })).toBeVisible();
    expect(consultas.at(-1)?.get("nota")).toBe("7+");
    await sinDesborde(page);
  });

  test("el orden se elige en la hoja, avisa bajo la fila y viaja a la API", async ({ page }) => {
    const consultas = await prepararBuscar(page);
    await page.goto("/search");

    await page.getByRole("button", { name: "Filters" }).click();
    const hoja = page.getByRole("dialog", { name: en.reviews.filters.dialogTitle });
    await hoja.getByRole("button", { name: en.common.sort.newest }).click();
    await expect(hoja.getByRole("button", { name: en.common.sort.newest })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    await hoja.getByRole("button", { name: en.search.filters.apply }).click();

    await expect(hoja).toBeHidden();
    await expect(page.getByText("Sorted by Newest")).toBeVisible();
    // El orden no suma al contador de «Filters».
    await expect(page.getByRole("button", { name: "Filters", exact: true })).toBeVisible();
    await expect.poll(() => consultas.at(-1)?.get("orden")).toBe("fecha-desc");
    await sinDesborde(page);
  });
});
