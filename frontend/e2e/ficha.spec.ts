import { expect, test, type Page } from "@playwright/test";

import type { ListaFicha } from "../lib/title-lists";
import en from "../messages/en/common.json";
import {
  CREDITOS_INTERSTELLAR,
  INTERSTELLAR,
  PLATAFORMAS_AR,
  PLATAFORMAS_CN,
} from "../tests/title-fixtures";
import { auditar } from "./axe";
import { prepararCuenta } from "./cuenta";

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 390, height: 844 },
] as const;
const COMUNIDAD = [
  {
    nombre_usuario: "lucia.cine",
    avatar_id: 3,
    valor: 10,
    fecha: "2026-09-28",
    texto: "The docking scene is still one of the tensest I’ve seen.",
  },
  { nombre_usuario: "mfernandez", avatar_id: 5, valor: 8, fecha: "2026-09-21", texto: "Great." },
  {
    nombre_usuario: "nico",
    avatar_id: 7,
    valor: 4,
    fecha: "2026-09-10",
    texto: "Too long for me.",
  },
];

/**
 * API de la ficha simulada con memoria: calificar, borrar o agregar a una lista
 * cambia lo que responden los pedidos siguientes, como el backend real.
 */
async function prepararFicha(page: Page) {
  const estado = {
    mia: null as null | { id: number; valor: number; texto: string | null; fecha: string },
    listas: [
      {
        id: 1,
        nombre: "Favorites",
        clave: "favoritos",
        tipo: "predeterminada",
        cantidad_items: 0,
        contiene: false,
        item_id: null as number | null,
      },
      {
        id: 2,
        nombre: "Watched",
        clave: "vistas",
        tipo: "predeterminada",
        cantidad_items: 0,
        contiene: false,
        item_id: null as number | null,
      },
      {
        id: 3,
        nombre: "Watchlist",
        clave: "pendientes",
        tipo: "predeterminada",
        cantidad_items: 0,
        contiene: false,
        item_id: null as number | null,
      },
      {
        id: 4,
        nombre: "Watching",
        clave: "viendo",
        tipo: "predeterminada",
        cantidad_items: 0,
        contiene: false,
        item_id: null as number | null,
      },
    ] as ListaFicha[],
    consultas: [] as string[],
    /** Simula TMDB caído en `providers/`. */
    plataformasCaidas: false,
    /** El país del perfil: el backend lo toma de la cuenta, no de la URL. */
    pais: "AR",
    pedidosPlataformas: 0,
  };
  await page.route("**/api/catalogo/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/credits/")) return route.fulfill({ json: CREDITOS_INTERSTELLAR });
    if (path.endsWith("/providers/")) {
      if (estado.plataformasCaidas)
        return route.fulfill({
          status: 502,
          json: { code: "upstream_error", params: {}, errors: [] },
        });
      estado.pedidosPlataformas += 1;
      const pais = estado.pais;
      return route.fulfill({
        json:
          pais === "AR" || pais === "US"
            ? { ...PLATAFORMAS_AR, pais }
            : { ...PLATAFORMAS_CN, pais },
      });
    }
    return route.fulfill({ json: INTERSTELLAR });
  });
  await page.route("https://image.tmdb.org/**", (route) =>
    route.fulfill({ path: "public/collage-posters/Opcion 1.jpg" })
  );
  await page.route("**/api/reviews/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    if (url.pathname === "/api/reviews/mias/") {
      return estado.mia
        ? route.fulfill({ json: estado.mia })
        : route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
    }
    if (url.pathname === "/api/reviews/" && method === "GET") {
      estado.consultas.push(url.search);
      let items = [...COMUNIDAD];
      const min = url.searchParams.get("nota_min");
      if (min) items = items.filter((r) => r.valor >= Number(min));
      if (url.searchParams.get("orden") === "nota-desc") items.sort((a, b) => b.valor - a.valor);
      return route.fulfill({
        json: {
          total: items.length,
          total_comunidad: COMUNIDAD.length,
          next: null,
          previous: null,
          results: items,
        },
      });
    }
    if (url.pathname === "/api/reviews/" && method === "POST") {
      const body = request.postDataJSON();
      estado.mia = { id: 9, valor: body.valor, texto: body.texto ?? null, fecha: "2026-10-14" };
      estado.listas[1] = { ...estado.listas[1], contiene: true, item_id: 70, cantidad_items: 1 };
      return route.fulfill({ status: 201, json: estado.mia });
    }
    if (url.pathname === "/api/reviews/9/texto/") {
      estado.mia = estado.mia && { ...estado.mia, texto: null };
      return route.fulfill({ status: 204 });
    }
    return route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
  });
  await page.route("**/api/lists/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();
    if (url.pathname === "/api/lists/" && method === "GET")
      return route.fulfill({ json: estado.listas });
    if (url.pathname === "/api/lists/" && method === "POST") {
      const lista: ListaFicha = {
        id: 5,
        nombre: request.postDataJSON().nombre,
        clave: null,
        tipo: "personalizada",
        cantidad_items: 0,
        contiene: false,
        item_id: null,
      };
      estado.listas.push(lista);
      return route.fulfill({ status: 201, json: lista });
    }
    if (url.pathname === "/api/lists/5/items/")
      return route.fulfill({ status: 201, json: { item_id: 91 } });
    return route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
  });
  return estado;
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

/**
 * Sección 15 del canvas: la línea del hero abre un diálogo centrado en
 * escritorio y una hoja pegada al borde inferior en celular.
 */
async function dondeVerla(page: Page, celular: boolean) {
  await prepararCuenta(page);
  await prepararFicha(page);
  await page.goto("/movie/157336");

  const linea = page.getByRole("button", { name: /Stream or rent/ });
  await expect(linea).toContainText("3 options in Argentina");
  await expect(linea).toHaveAttribute("aria-expanded", "false");
  const generos = await page.getByRole("list", { name: "Genres" }).boundingBox();
  const lineaCaja = await linea.boundingBox();
  expect(lineaCaja!.y).toBeGreaterThan(generos!.y + generos!.height - 1);
  // Área de toque de 44 px.
  expect(lineaCaja!.height).toBeGreaterThanOrEqual(44);
  await sinDesborde(page);

  await linea.click();
  await expect(linea).toHaveAttribute("aria-expanded", "true");
  const panel = page.getByRole("dialog", { name: "Where to watch" });
  await expect(panel).toHaveAttribute("aria-modal", "true");
  await expect(panel.getByRole("heading", { level: 3 })).toHaveText(["Stream", "Rent", "Buy"]);
  await expect(panel.getByAltText("Netflix").first()).toHaveAttribute("title", "Netflix");
  const logo = await panel.getByAltText("Netflix").first().boundingBox();
  expect(Math.round(logo!.width)).toBe(40);
  await expect(panel.getByRole("link", { name: /See all options on TMDB/ })).toHaveAttribute(
    "href",
    PLATAFORMAS_AR.enlace
  );
  await expect(panel.getByRole("link", { name: "JustWatch" })).toHaveAttribute(
    "href",
    "https://www.justwatch.com"
  );
  const cerrar = panel.getByRole("button", { name: "Close" });
  const cerrarCaja = await cerrar.boundingBox();
  expect(Math.round(cerrarCaja!.width)).toBe(44);
  expect(Math.round(cerrarCaja!.height)).toBe(44);

  const caja = await panel.boundingBox();
  const ventana = page.viewportSize()!;
  // `scrollbar-gutter: stable` reserva la barra (15 px en Chromium de escritorio;
  // 0 en un celular real), y la capa del diálogo no la ocupa.
  const BARRA = 16;
  if (celular) {
    // Hoja inferior: de borde a borde y apoyada abajo.
    expect(Math.round(caja!.x)).toBe(0);
    expect(caja!.width).toBeGreaterThanOrEqual(ventana.width - BARRA);
    expect(Math.round(caja!.y + caja!.height)).toBe(ventana.height);
  } else {
    // Diálogo centrado de 520 px.
    expect(Math.round(caja!.width)).toBe(520);
    expect(Math.abs(caja!.x + caja!.width / 2 - ventana.width / 2)).toBeLessThanOrEqual(BARRA / 2);
    expect(caja!.y).toBeGreaterThan(0);
    expect(caja!.y + caja!.height).toBeLessThan(ventana.height);
  }
  await sinDesborde(page);
  await auditar(page);

  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await expect(linea).toBeFocused();

  // El botón de cerrar también devuelve el foco a la línea.
  await linea.click();
  await cerrar.click();
  await expect(panel).toHaveCount(0);
  await expect(linea).toBeFocused();
}

for (const viewport of viewports) {
  test.describe(`ficha en ${viewport.name}`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      locale: "en-US",
      extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
    });

    test("sin sesión: datos, créditos, reseñas públicas e invitación a ingresar", async ({
      page,
    }) => {
      await page.route("**/api/profile/", (route) =>
        route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
      );
      await prepararFicha(page);
      await page.goto("/movie/157336?from=home");

      await expect(page.getByRole("heading", { level: 1 })).toHaveText("Interstellar");
      await expect(page.getByText("Christopher Nolan")).toBeVisible();
      await expect(page.getByRole("heading", { name: "From the community (3)" })).toBeVisible();
      await expect(
        page.getByRole("link", { name: en.title.actions.signedOutPrompt })
      ).toHaveAttribute("href", "/login?next=%2Fmovie%2F157336");
      await sinDesborde(page);
    });

    test("dónde verla: línea bajo los géneros y diálogo con grupos, TMDB y JustWatch", async ({
      page,
    }) => {
      await dondeVerla(page, viewport.name === "celular");
    });

    test("dónde verla: país sin disponibilidad", async ({ page }) => {
      await prepararCuenta(page);
      await page.route("**/api/profile/", (route) =>
        route.fulfill({
          json: {
            pk: 1,
            nombre: "Li",
            apellido: "Wei",
            nombre_usuario: "liwei",
            pais: "CN",
            idioma: "en",
          },
        })
      );
      const estado = await prepararFicha(page);
      estado.pais = "CN";
      await page.goto("/movie/157336");

      await expect(
        page.getByText("Not available to stream, rent or buy in China yet.")
      ).toBeVisible();
      await expect(page.getByRole("button", { name: /Stream or rent/ })).toHaveCount(0);
    });

    test("dónde verla: sin sesión invita a ingresar y no pide plataformas", async ({ page }) => {
      await page.route("**/api/profile/", (route) =>
        route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
      );
      const estado = await prepararFicha(page);
      await page.goto("/movie/157336");

      // Issue #124: sin cuenta no hay un país confiable (`locale: en-US` daba EE. UU.).
      await expect(page.getByRole("link", { name: en.title.providers.signedOut })).toHaveAttribute(
        "href",
        "/login?next=%2Fmovie%2F157336"
      );
      await expect(page.getByText("Stream or rent")).toHaveCount(0);
      expect(estado.pedidosPlataformas).toBe(0);
    });

    test("dónde verla: si TMDB cae se oculta", async ({ page }) => {
      await prepararCuenta(page);
      const estado = await prepararFicha(page);
      estado.plataformasCaidas = true;
      await page.goto("/movie/157336");

      await expect(page.getByRole("heading", { level: 1 })).toHaveText("Interstellar");
      await expect(page.getByText("Stream or rent")).toHaveCount(0);
    });

    test("calificar con reseña, borrar el texto y conservar la nota", async ({ page }) => {
      await prepararCuenta(page);
      await prepararFicha(page);
      await page.goto("/movie/157336");

      await page.getByRole("button", { name: en.common.rating.rate }).click();
      const dialogo = page.getByRole("dialog", { name: "Rate Interstellar" });
      await dialogo.getByRole("radio", { name: "8 out of 10" }).click();
      await dialogo.getByRole("textbox").fill("A father who made a promise.");
      await dialogo.getByRole("button", { name: en.common.review.publish }).click();

      const tuya = page.getByRole("article", { name: en.title.reviews.yourReview });
      await expect(tuya).toContainText("A father who made a promise.");
      // Calificar mueve el título a Watched: el botón de estado lo muestra.
      await expect(page.getByRole("button", { name: "Status: Watched" })).toBeVisible();

      await tuya.getByRole("button", { name: en.common.review.delete }).click();
      await page
        .getByRole("alertdialog", { name: en.title.review.deleteConfirmTitle })
        .getByRole("button", { name: en.common.review.delete })
        .click();
      await expect(tuya).toHaveCount(0);
      await expect(
        page.getByRole("button", { name: "Your rating: 8 out of 10. Edit" })
      ).toBeVisible();
      await sinDesborde(page);
    });
  });
}

test.describe("ficha en escritorio con sesión", () => {
  test.use({
    viewport: { width: 1440, height: 900 },
    locale: "en-US",
    extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
  });

  test("ordenar y filtrar la comunidad, y crear una lista nueva", async ({ page }) => {
    await prepararCuenta(page);
    const estado = await prepararFicha(page);
    await page.goto("/movie/157336");

    await page.getByRole("combobox", { name: en.common.filters.sortLabel }).selectOption("highest");
    await page.getByRole("combobox", { name: en.common.rating.label }).selectOption("9");
    await expect(page.getByRole("heading", { name: "Showing 1 of 3" })).toBeVisible();
    expect(estado.consultas.at(-1)).toContain("orden=nota-desc");
    expect(estado.consultas.at(-1)).toContain("nota_min=9");

    await page.getByRole("button", { name: "Add Interstellar to a list" }).click();
    await page.getByRole("button", { name: en.title.lists.newAction }).click();
    await page.getByRole("textbox", { name: en.title.lists.newNameLabel }).fill("Sci Fi");
    await page.getByRole("button", { name: en.title.lists.createAndAdd }).click();
    await expect(page.getByText("You created “Sci Fi” and added Interstellar.")).toBeVisible();
  });
});

test.describe("dónde verla en 375 × 812", () => {
  test.use({
    viewport: { width: 375, height: 812 },
    locale: "en-US",
    extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
  });

  test("la línea abre una hoja inferior con el contenido del diálogo", async ({ page }) => {
    await dondeVerla(page, true);
  });
});
