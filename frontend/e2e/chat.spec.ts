import { expect, test, type Page, type Route } from "@playwright/test";

import { conSesion, simularCatalogo } from "./api-simulada";

/**
 * El panel del chat (PR 6) con la API simulada: el `POST` devuelve un
 * `text/event-stream` armado a mano con el contrato de `design.md`. El flujo
 * completo (historial, badge, «Ask FilmAI» del footer) es del PR 7.
 */

const frame = (evento: string, datos: unknown) =>
  `event: ${evento}\ndata: ${JSON.stringify(datos)}\n\n`;

const RESPUESTA =
  frame("estado", { code: "searching" }) +
  frame("texto", { delta: "Try **Moon** " }) +
  frame("texto", { delta: "![x](https://atacante.example/pixel?d=1)" }) +
  frame("tarjetas", {
    tarjetas: [
      {
        id_tmdb: 157336,
        tipo: "movie",
        titulo: "Interstellar",
        poster: null,
        anio: 2014,
        nota_tmdb: 8.4,
      },
    ],
  }) +
  frame("fin", { id: 2, id_pregunta: 1 });

async function prepararChat(page: Page, responder: (route: Route) => Promise<void> | void) {
  await conSesion(page);
  await simularCatalogo(page);
  const preparar: string[] = [];
  await page.route("**/api/chat/preparar/", (route) => {
    preparar.push(route.request().headers()["x-csrftoken"] ?? "");
    return route.fulfill({ status: 202, body: "" });
  });
  await page.route("**/api/chat/messages/", responder);
  return { preparar };
}

const sse = (route: Route) =>
  route.fulfill({
    status: 200,
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
    body: RESPUESTA,
  });

test.describe("chat en escritorio", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("pregunta, respuesta segura, tarjeta y cierre con Escape", async ({ page }) => {
    const { preparar } = await prepararChat(page, sse);
    const externos: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("atacante.example")) externos.push(request.url());
    });
    await page.goto("/home");
    const fab = page.getByRole("button", { name: "Ask FilmAI" });
    await fab.click();

    const panel = page.getByRole("dialog", { name: "FilmAI Assistant" });
    await expect(panel).toBeVisible();
    const caja = (await panel.boundingBox())!;
    expect(Math.round(caja.width)).toBe(440);
    // `scrollbar-gutter: stable` (globals.css) reserva el lugar de la barra de
    // scroll: lo fijo termina donde termina el body, igual que la navbar.
    const ancho = await page.evaluate(() => document.body.getBoundingClientRect().width);
    expect(Math.round(caja.x + caja.width)).toBe(Math.round(ancho));
    await expect(page.getByRole("textbox", { name: "Your message" })).toBeFocused();
    await expect.poll(() => preparar).toEqual(["test-csrf"]);

    await page.keyboard.type("Something like Interstellar");
    await page.keyboard.press("Enter");
    await expect(panel.getByText("Moon", { exact: true })).toBeVisible();
    await expect(panel.locator("img")).toHaveCount(0);
    expect(externos).toEqual([]);
    await expect(panel.getByRole("link", { name: /Interstellar/ })).toHaveAttribute(
      "href",
      "/movie/157336?from=chat"
    );
    await expect(panel.getByText("8.4", { exact: true })).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(panel).toBeHidden();
    await expect(fab).toBeFocused();
  });

  test("cancelar conserva la pregunta y avisa", async ({ page }) => {
    // El stream nunca contesta: la respuesta queda en curso hasta cancelar.
    await prepararChat(page, () => new Promise<void>(() => {}));
    await page.goto("/home");
    await page.getByRole("button", { name: "Ask FilmAI" }).click();
    const campo = page.getByRole("textbox", { name: "Your message" });
    await campo.fill("A TV show to binge");
    await campo.press("Enter");
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByText("Request canceled")).toBeVisible();
    await expect(campo).toHaveValue("A TV show to binge");
    await expect(page.getByRole("button", { name: "Send" })).toBeVisible();
  });

  test("elegir una tarjeta cierra el panel y la conversación sigue al volver", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    await page.getByRole("button", { name: "Ask FilmAI" }).click();
    await page.getByRole("textbox", { name: "Your message" }).fill("Space");
    await page.keyboard.press("Enter");
    await page.getByRole("link", { name: /Interstellar/ }).click();
    // `next dev` compila la ruta de la ficha en el primer pedido: puede tardar.
    await expect(page).toHaveURL(/\/movie\/157336\?from=chat$/, { timeout: 60_000 });
    const panel = page.getByRole("dialog", { name: "FilmAI Assistant" });
    await expect(panel).toBeHidden();
    await page.getByRole("button", { name: "Ask FilmAI" }).click();
    await expect(panel.getByText("Space", { exact: true })).toBeVisible();
  });
});

test.describe("chat en celular", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("se abre como hoja desde abajo", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    await page.getByRole("button", { name: "Ask FilmAI" }).click();
    const caja = (await page.getByRole("dialog", { name: "FilmAI Assistant" }).boundingBox())!;
    expect(Math.round(caja.y)).toBe(24);
    const ancho = await page.evaluate(() => document.body.getBoundingClientRect().width);
    expect(Math.round(caja.width)).toBe(Math.round(ancho));
    expect(Math.round(caja.y + caja.height)).toBe(844);
  });
});
