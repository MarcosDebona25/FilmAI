import { expect, test } from "@playwright/test";

import { simularCatalogo, sinSesion } from "./api-simulada";
import { botonFlotante, mensaje, prepararChat, sse } from "./chat-simulado";

test.describe("chat en escritorio", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("pregunta, respuesta segura, tarjeta y cierre con Escape", async ({ page }) => {
    const { preparar } = await prepararChat(page, sse);
    const externos: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("atacante.example")) externos.push(request.url());
    });
    await page.goto("/home");
    const fab = botonFlotante(page);
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
    await botonFlotante(page).click();
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
    await botonFlotante(page).click();
    await page.getByRole("textbox", { name: "Your message" }).fill("Space");
    await page.keyboard.press("Enter");
    await page.getByRole("link", { name: /Interstellar/ }).click();
    // `next dev` compila la ruta de la ficha en el primer pedido: puede tardar.
    await expect(page).toHaveURL(/\/movie\/157336\?from=chat$/, { timeout: 60_000 });
    const panel = page.getByRole("dialog", { name: "FilmAI Assistant" });
    await expect(panel).toBeHidden();
    await botonFlotante(page).click();
    await expect(panel.getByText("Space", { exact: true })).toBeVisible();
  });
});

test.describe("chat en celular", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("se abre como hoja desde abajo", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    await botonFlotante(page).click();
    const caja = (await page.getByRole("dialog", { name: "FilmAI Assistant" }).boundingBox())!;
    expect(Math.round(caja.y)).toBe(24);
    const ancho = await page.evaluate(() => document.body.getBoundingClientRect().width);
    expect(Math.round(caja.width)).toBe(Math.round(ancho));
    expect(Math.round(caja.y + caja.height)).toBe(844);
  });
});

test.describe("historial, bienvenida y badge", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("sin mensajes: bienvenida con el nombre y sugerencias que envían", async ({ page }) => {
    let enviado = "";
    await prepararChat(page, (route) => {
      enviado = JSON.parse(route.request().postData() ?? "{}").texto;
      return sse(route);
    });
    await page.goto("/home");
    await botonFlotante(page).click();
    const panel = page.getByRole("dialog", { name: "FilmAI Assistant" });
    await expect(panel.getByText(/Hi, Juan! Tell me what you feel like watching/)).toBeVisible();
    // Las sugerencias se sortean al abrir: son tres y se elige la primera, sea cual sea.
    const sugerencias = panel.getByRole("list", { name: "Suggestions" }).getByRole("button");
    await expect(sugerencias).toHaveCount(3);
    const texto = (await sugerencias.first().textContent()) ?? "";
    await sugerencias.first().click();
    await expect.poll(() => enviado).toBe(texto);
    await expect(panel.getByText("Moon", { exact: true })).toBeVisible();
    await expect(panel.getByRole("list", { name: "Suggestions" })).toHaveCount(0);
  });

  test("el historial se carga al abrir y al subir trae las páginas anteriores", async ({
    page,
  }) => {
    const largo = "texto largo ".repeat(12);
    const reciente = Array.from({ length: 20 }, (_, i) =>
      mensaje(40 - i, i % 2 ? "usuario" : "chatbot", `Reciente ${40 - i}. ${largo}`)
    );
    const { pedidosHistorial } = await prepararChat(page, sse, (cursor) =>
      cursor
        ? {
            next: null,
            results: [
              mensaje(2, "chatbot", "Respuesta antigua"),
              mensaje(1, "usuario", "Pregunta antigua"),
            ],
          }
        : { next: "http://localhost:8000/api/chat/messages/?cursor=pagina2", results: reciente }
    );
    await page.goto("/home");
    await botonFlotante(page).click();
    const panel = page.getByRole("dialog", { name: "FilmAI Assistant" });
    // Se abre al final de la conversación: lo último que se dijo. `toBeVisible`
    // no alcanza, porque no mira el recorte del scroll; se mide la posición.
    const conversacion = panel.getByRole("log");
    const distanciaAlFinal = () =>
      conversacion.evaluate((nodo) => nodo.scrollHeight - nodo.clientHeight - nodo.scrollTop);
    await expect(panel.getByText(/^Reciente 40\./)).toBeInViewport();
    await expect.poll(distanciaAlFinal).toBeLessThan(2);
    expect(pedidosHistorial).toEqual([null]);

    await conversacion.evaluate((nodo) => (nodo.scrollTop = 0));
    await expect(panel.getByText("Pregunta antigua")).toBeAttached();
    expect(pedidosHistorial).toEqual([null, "pagina2"]);
    // Lo que se estaba leyendo no salta: el panel no queda arriba del todo.
    await expect.poll(() => conversacion.evaluate((nodo) => nodo.scrollTop)).toBeGreaterThan(0);

    // Cerrar y volver a abrir no lo pide de nuevo, y vuelve a mostrar lo último.
    await page.keyboard.press("Escape");
    await botonFlotante(page).click();
    await expect(panel.getByText(/^Reciente 40\./)).toBeInViewport();
    await expect.poll(distanciaAlFinal).toBeLessThan(2);
    expect(pedidosHistorial).toEqual([null, "pagina2"]);
  });

  test("el badge se enciende si la respuesta termina con el panel cerrado", async ({ page }) => {
    let terminar = () => {};
    const puedeTerminar = new Promise<void>((resolver) => (terminar = resolver));
    await prepararChat(page, async (route) => {
      await puedeTerminar;
      await sse(route);
    });
    await page.goto("/home");
    const fab = botonFlotante(page);
    await fab.click();
    await page.keyboard.type("Space");
    await page.keyboard.press("Enter");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "FilmAI Assistant" })).toBeHidden();
    await expect(page.getByText("New answer waiting")).toHaveCount(0);

    terminar();
    await expect(page.getByText("New answer waiting")).toBeAttached();
    await fab.click();
    await expect(page.getByText("New answer waiting")).toHaveCount(0);
    await expect(
      page.getByRole("dialog", { name: "FilmAI Assistant" }).getByText("Moon", { exact: true })
    ).toBeVisible();
  });

  test("«Ask FilmAI» del pie abre el panel", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    await page.getByRole("contentinfo").getByRole("button", { name: "Ask FilmAI" }).click();
    await expect(page.getByRole("dialog", { name: "FilmAI Assistant" })).toBeVisible();
  });

  test("solo con teclado: abre, envía y Escape devuelve el foco al botón", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    const fab = botonFlotante(page);
    // Hasta que la página se hidrata el botón no responde: se reintenta el Enter.
    await expect(async () => {
      await fab.focus();
      await page.keyboard.press("Enter");
      await expect(page.getByRole("textbox", { name: "Your message" })).toBeFocused({
        timeout: 1500,
      });
    }).toPass();
    await page.keyboard.type("Something short");
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("dialog", { name: "FilmAI Assistant" }).getByText("Moon", { exact: true })
    ).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(fab).toBeFocused();
  });
});

test.describe("«Ask FilmAI» sin sesión", () => {
  test("el pie lleva al login y vuelve a la página", async ({ page }) => {
    await sinSesion(page);
    await simularCatalogo(page);
    await page.goto("/home");
    // Un visitante ve la interfaz en el idioma del navegador (es-AR en estas pruebas).
    const enlace = page.getByRole("contentinfo").getByRole("link", { name: "Preguntale a FilmAI" });
    await expect(enlace).toHaveAttribute("href", "/login?next=%2Fhome");
  });
});
