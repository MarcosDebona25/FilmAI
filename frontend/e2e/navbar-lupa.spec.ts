import { expect, test, type Locator, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import { reacher, svu } from "../tests/catalog-fixtures";
import { simularCatalogo, sinSesion } from "./api-simulada";
import { auditar } from "./axe";

/**
 * La lupa de la navbar (14/11/2026): se despliega, sugiere personas y títulos,
 * y elegir una persona lleva a Buscar con su chip. Con la API simulada.
 */
const ESCRITORIO = { width: 1440, height: 900 };
const CELULAR = { width: 375, height: 812 };

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
  await page.route("**/api/catalogo/explore/**", (route) =>
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

/** Despliega la lupa, escribe y espera la lista. */
async function sugerir(page: Page, texto: string) {
  await lupa(page).click();
  await page.getByRole("combobox").fill(texto);
  const lista = page.getByRole("listbox");
  await expect(lista).toBeVisible({ timeout: 15_000 });
  return lista;
}

const caja = async (elemento: Locator) => {
  const medidas = await elemento.boundingBox();
  if (!medidas) throw new Error("El elemento no está en pantalla");
  return medidas;
};

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

    // Una «/» pulsada antes de hidratar se pierde (todavía no hay listener): se reintenta hasta que abra la lupa.
    await expect(async () => {
      await page.keyboard.press("/");
      await expect(page.getByRole("combobox")).toBeFocused({ timeout: 1_000 });
    }).toPass({ timeout: 15_000 });
    await page.getByRole("combobox").fill("dune");
    await page.keyboard.press("Enter");

    await expect(page).toHaveURL(/\/search\?q=dune$/);
  });
});

test.describe("el desplegable rico de la lupa (canvas, sección 13)", () => {
  test.use({ viewport: ESCRITORIO, locale: "en-US" });

  test("a 1440 px el campo mide 20rem y la lista 26rem, alineada a su borde derecho", async ({
    page,
  }) => {
    await preparar(page);
    await page.goto("/home");
    const lista = await sugerir(page, "nolan");

    // Sin esto se mediría el campo a mitad de la animación con la que se despliega.
    const buscador = page.getByRole("search");
    await expect.poll(async () => (await caja(buscador)).width).toBe(320);
    const campo = await caja(buscador);
    const desplegable = await caja(lista);
    expect(desplegable.width).toBe(416);
    expect(desplegable.x + desplegable.width).toBeCloseTo(campo.x + campo.width, 0);
    // 8 px debajo del campo.
    expect(desplegable.y).toBeCloseTo(campo.y + campo.height + 8, 0);

    // El campo es una píldora de 44 px con la ✕ de 44 px adentro.
    const pildora = page.getByRole("combobox").locator("xpath=..");
    expect(campo.height).toBe(44);
    expect(
      parseFloat(await pildora.evaluate((el) => getComputedStyle(el).borderRadius))
    ).toBeGreaterThanOrEqual(22);
    const cerrar = await caja(page.getByRole("button", { name: en.nav.search.closeLabel }));
    expect([cerrar.width, cerrar.height]).toEqual([44, 44]);
  });

  test("filas de 84 px con póster de 48 × 72, nota con ★ y foto de persona de 48 px", async ({
    page,
  }) => {
    await preparar(page);
    await page.goto("/home");
    const lista = await sugerir(page, "nolan");

    const titulo = lista.getByRole("option", { name: /Reacher/ });
    expect((await caja(titulo)).height).toBe(84);
    const poster = await caja(titulo.locator("img"));
    expect([poster.width, poster.height]).toEqual([48, 72]);
    await expect(titulo).toContainText("TV show · 2022");
    await expect(titulo).toContainText("TMDB rating: 8.1 out of 10");

    const persona = lista.getByRole("option", { name: /Christopher Nolan/ });
    expect((await caja(persona)).height).toBe(84);
    // Nolan viene sin foto: en su lugar va el círculo con las iniciales.
    await expect(persona.locator("[aria-hidden=true]").first()).toHaveText("CN");
    const foto = await caja(persona.locator("[aria-hidden=true]").first());
    expect([foto.width, foto.height]).toEqual([48, 48]);

    const verTodo = lista.getByRole("option", { name: /See all results for “nolan”/ });
    expect((await caja(verTodo)).height).toBe(48);
  });

  test("la fila activa con el teclado se marca y la lista abierta pasa axe", async ({ page }) => {
    await preparar(page);
    await page.goto("/home");
    const lista = await sugerir(page, "nolan");

    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    const activa = lista.getByRole("option", { name: /Reacher/ });
    await expect(activa).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("combobox")).toHaveAttribute(
      "aria-activedescendant",
      `sug-tv-${reacher.id}`
    );
    await auditar(page);
  });

  for (const [ancho, esperado] of [
    [1024, 245.76],
    [768, 192],
  ] as const) {
    test(`a ${ancho} px el campo mide ${esperado} px: clamp(12rem, 24vw, 20rem)`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: ancho, height: 900 });
      await preparar(page);
      await page.goto("/home");
      await lupa(page).click();

      const buscador = page.getByRole("search");
      await expect.poll(async () => (await caja(buscador)).width).toBeCloseTo(esperado, 1);
    });
  }
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
        name: en.nav.main.explore,
      })
    ).toBeVisible();
    // «/» tampoco la despliega: en celular no hay campo en la barra.
    await page.keyboard.press("/");
    await expect(page.getByRole("combobox")).toHaveCount(0);
    await auditar(page);
  });
});
