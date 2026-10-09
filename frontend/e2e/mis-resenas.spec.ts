import { expect, test, type Page } from "@playwright/test";
import { prepararCuenta } from "./cuenta";
const initial = {
  id: 1,
  id_tmdb: 10,
  tipo: "movie",
  titulo: "Interstellar",
  poster: "/test-poster.jpg",
  valor: 8,
  fecha: "2026-10-03",
  texto: "Una reseña extensa. ".repeat(40),
};
async function reviews(page: Page, empty = false) {
  await prepararCuenta(page);
  let items = empty ? [] : [{ ...initial }];
  let fail = false;
  let calls = 0;
  await page.route("https://image.tmdb.org/**", (route) => route.fulfill({ status: 404 }));
  await page.route("**/api/reviews/**", async (route) => {
    const request = route.request();
    calls++;
    if (fail) {
      fail = false;
      await route.fulfill({ status: 500, json: { code: "server_error", params: {}, errors: [] } });
      return;
    }
    if (request.method() === "GET")
      await route.fulfill({ json: { total: items.length, next: null, results: items } });
    else if (request.method() === "PUT") {
      items[0] = { ...items[0], ...request.postDataJSON() };
      await route.fulfill({ json: items[0] });
    } else {
      if (request.url().endsWith("/texto/"))
        items[0] = { ...items[0], texto: null as unknown as string };
      else items = [];
      await route.fulfill({ status: 204 });
    }
  });
  return {
    fail: () => {
      fail = true;
    },
    items: () => items,
    calls: () => calls,
  };
}
test("muestra póster de reemplazo, texto expandible y edición precargada", async ({ page }) => {
  const state = await reviews(page);
  await page.goto("/my-reviews");
  await expect(page.getByRole("img", { name: "Sin póster de Interstellar" })).toBeVisible();
  await expect(page.getByLabel("Calificación: 8 de 10").locator("svg")).toBeVisible();
  await expect(page.getByLabel("Calificación: 8 de 10").locator("svg")).toHaveCSS(
    "color",
    "rgb(245, 197, 24)"
  );
  await page.getByRole("button", { name: "Leer más" }).click();
  await expect(page.getByRole("button", { name: "Leer menos" })).toHaveAttribute(
    "aria-expanded",
    "true"
  );
  await page.getByRole("button", { name: "Editar", exact: true }).click();
  const dialog = page.getByRole("dialog", {
    name: 'Editar calificación y reseña de "Interstellar"',
  });
  await expect(dialog.getByRole("radio", { name: "8 de 10" })).toBeChecked();
  await expect(dialog.getByLabel("Reseña (opcional)")).toBeFocused();
  await expect(dialog.getByRole("radio", { name: "1 de 10" })).not.toBeFocused();
  await dialog.getByRole("radio", { name: "9 de 10" }).check();
  await dialog.getByLabel("Reseña (opcional)").fill("Nueva reseña");
  await dialog.getByRole("button", { name: "Actualizar" }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByText("9/10", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Calificación: 9 de 10").locator("svg")).toBeVisible();
  await expect(page.getByRole("button", { name: /Leer más|Leer menos/ })).toHaveCount(0);
  expect(state.items()[0].texto).toBe("Nueva reseña");
});
test("eliminar texto conserva la nota; quitar calificación elimina la tarjeta", async ({
  page,
}) => {
  const state = await reviews(page);
  await page.goto("/my-reviews");
  await page.getByRole("button", { name: "Eliminar reseña", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("Vistas se conservan");
  await page.getByRole("dialog").getByRole("button", { name: "Cancelar" }).click();
  expect(state.items()[0].texto).toBeTruthy();
  await page.getByRole("button", { name: "Eliminar reseña", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Eliminar reseña" }).click();
  await expect(page.getByRole("note")).toHaveText("Todavía no escribiste una reseña.");
  await expect(page.getByText("8/10", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Quitar calificación", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("dejará de estar en Vistas");
  await page.getByRole("dialog").getByRole("button", { name: "Quitar calificación" }).click();
  await expect(
    page.getByText("Todavía no calificaste ninguna producción ni escribiste reseñas.")
  ).toBeVisible();
  expect(state.items()).toHaveLength(0);
});
test("el fallo de escritura conserva datos y permite reintentar", async ({ page }) => {
  const state = await reviews(page);
  await page.goto("/my-reviews");
  await page.getByRole("button", { name: "Quitar calificación" }).click();
  state.fail();
  await page.getByRole("dialog").getByRole("button", { name: "Quitar calificación" }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText("Tus datos se mantienen");
  expect(state.items()).toHaveLength(1);
  await page.getByRole("dialog").getByRole("button", { name: "Quitar calificación" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
});
test("estado vacío permite regresar al perfil", async ({ page }) => {
  await reviews(page, true);
  await page.goto("/my-reviews");
  await page.getByRole("link", { name: "Volver a mi perfil" }).click();
  await expect(page).toHaveURL(/\/profile$/);
});
test("paginación por cursor deduplica y conserva tarjetas ante error", async ({ page }) => {
  await prepararCuenta(page);
  let fail = true;
  await page.route("https://image.tmdb.org/**", (route) => route.fulfill({ status: 404 }));
  await page.route("**/api/reviews/mias/**", async (route) => {
    if (new URL(route.request().url()).search) {
      if (fail) {
        fail = false;
        await route.fulfill({
          status: 500,
          json: { code: "server_error", params: {}, errors: [] },
        });
        return;
      }
      await route.fulfill({
        json: {
          next: null,
          results: [
            initial,
            { ...initial, id: 2, titulo: "Dark", tipo: "tv", poster: "", texto: null },
          ],
          total: 2,
        },
      });
    } else
      await route.fulfill({
        json: {
          next: "http://backend:8000/api/reviews/mias/?cursor=next",
          results: [initial],
          total: 2,
        },
      });
  });
  await page.goto("/my-reviews");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("No pudimos cargar");
  await expect(page.getByRole("article")).toHaveCount(1);
  await page.getByRole("button", { name: "Reintentar" }).click();
  await expect(page.getByRole("article")).toHaveCount(2);
  await expect(page.getByRole("heading", { name: "Dark", exact: true })).toBeVisible();
});
test("mobile: la tarjeta no desborda y el diálogo contiene el foco", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await reviews(page);
  await page.goto("/my-reviews");
  await page.getByRole("button", { name: "Editar", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Actualizar" }).focus();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("dialog").getByRole("radio", { name: "8 de 10" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Editar", exact: true })).toBeFocused();
});

test("póster cargado y composición responsive con texto limitado a 1000 caracteres", async ({
  page,
}, testInfo) => {
  await reviews(page);
  await page.route("https://image.tmdb.org/**", (route) =>
    route.fulfill({
      contentType: "image/png",
      body: Buffer.from(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=",
        "base64"
      ),
    })
  );
  await page.goto("/my-reviews");
  const poster = page.getByAltText("Póster de Interstellar");
  await expect(poster).toBeVisible();
  expect(await poster.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
  for (const width of [1440, 390, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    const box = await poster.boundingBox();
    expect(box?.width).toBe(width < 640 ? 56 : 80);
    expect(box?.height).toBe(width < 640 ? 84 : 120);
    const card = page.getByRole("article");
    const cardBox = (await card.boundingBox())!;
    const dateBox = (await card.locator("time").boundingBox())!;
    const rating = card.getByLabel("Calificación: 8 de 10");
    const iconBox = (await rating.locator("svg").boundingBox())!;
    const ratingBox = (await rating.boundingBox())!;
    expect(dateBox.x + dateBox.width).toBeCloseTo(cardBox.x + cardBox.width - 21, 0);
    expect(dateBox.y - cardBox.y).toBeLessThan(32);
    expect(dateBox.y + dateBox.height).toBeLessThan(iconBox.y);
    expect(ratingBox.height).toBeLessThan(32);
    expect(iconBox.x).toBeCloseTo(ratingBox.x, 0);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    ).toBe(true);
    if (width !== 1920)
      await page.screenshot({
        path: testInfo.outputPath(`mis-resenas-${width}.png`),
        fullPage: true,
      });
  }
  await page.getByRole("button", { name: "Editar", exact: true }).click();
  const text = page.getByLabel("Reseña (opcional)");
  await text.fill("a".repeat(1001));
  await expect(text).toHaveValue("a".repeat(1000));
  await expect(page.getByText("1000/1000")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
});
test("carga inicial fallida ofrece reintento y conserva un listado utilizable", async ({
  page,
}) => {
  const state = await reviews(page);
  state.fail();
  await page.goto("/my-reviews");
  await expect(page.getByRole("main").getByRole("alert")).toContainText("No pudimos cargar");
  await page.getByRole("button", { name: "Reintentar" }).click();
  await expect(page.getByRole("article")).toHaveCount(1);
});

test("Leer más sigue el recorte real al cambiar el ancho de la tarjeta", async ({ page }) => {
  const state = await reviews(page);
  state.items()[0].texto = "Una reseña que se adapta al ancho de pantalla. ".repeat(3);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/my-reviews");
  await expect(page.getByRole("article")).toBeVisible();
  await expect(page.getByRole("button", { name: "Leer más" })).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 900 });
  await expect(page.getByRole("button", { name: "Leer más" })).toBeVisible();
  await page.getByRole("button", { name: "Leer más" }).click();
  await expect(page.getByRole("button", { name: "Leer menos" })).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.getByRole("button", { name: /Leer más|Leer menos/ })).toHaveCount(0);
});
