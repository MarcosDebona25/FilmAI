import { readFileSync } from "node:fs";

import { expect, test, type Locator, type Page, type Route } from "@playwright/test";

import { botonFlotante, frame, prepararChat, sse } from "./chat-simulado";

/**
 * Calidad del chatbot (Q-01, Q-03 y Q-04, pendiente 4): axe-core, teclado y
 * foco, fallas forzadas y responsive, con la API simulada. La app es solo de
 * tema oscuro, así que no hay variante clara que revisar.
 */

type Infraccion = { id: string; impact: string; nodes: { target: string[] }[] };
type Axe = { run: (c: unknown, o: unknown) => Promise<{ violations: Infraccion[] }> };
const axeSource = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

/** Reglas WCAG 2.1 A y AA; falla con la lista de infracciones. */
async function auditar(page: Page) {
  if (!(await page.evaluate(() => "axe" in window)))
    await page.addScriptTag({ content: axeSource });
  const infracciones = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: Axe }).axe;
    const resultado = await axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
    });
    return resultado.violations.map((v) => ({
      regla: v.id,
      impacto: v.impact,
      nodos: v.nodes.slice(0, 3).map((n) => n.target.join(" ")),
    }));
  });
  expect(infracciones).toEqual([]);
}

const ANCHOS = [
  { nombre: "celular", width: 375, height: 812 },
  { nombre: "tablet", width: 768, height: 1024 },
  { nombre: "escritorio", width: 1440, height: 900 },
] as const;

const panelDe = (page: Page) => page.getByRole("dialog", { name: "FilmAI Assistant" });
const campoDe = (page: Page) => page.getByRole("textbox", { name: "Your message" });

async function abrirYPreguntar(page: Page, pregunta = "Space") {
  await page.goto("/home");
  await botonFlotante(page).click();
  await campoDe(page).fill(pregunta);
  await page.keyboard.press("Enter");
}

const error500 = (route: Route) =>
  route.fulfill({ status: 500, json: { code: "server_error", params: {}, errors: [] } });

for (const { nombre, width, height } of ANCHOS) {
  test.describe(`Q-01 y Q-04 · ${nombre} (${width} px)`, () => {
    test.use({ viewport: { width, height }, locale: "en-US" });

    test("axe: botón flotante y panel abierto", async ({ page }) => {
      await prepararChat(page, sse);
      await page.goto("/home");
      await expect(botonFlotante(page)).toBeVisible();
      await auditar(page);
      await botonFlotante(page).click();
      await expect(panelDe(page).getByRole("list", { name: "Suggestions" })).toBeVisible();
      await auditar(page);
    });

    test("axe: respuesta con tarjetas", async ({ page }) => {
      await prepararChat(page, sse);
      await abrirYPreguntar(page);
      await expect(panelDe(page).getByRole("link", { name: /Interstellar/ })).toBeVisible();
      await auditar(page);
    });

    test("axe: estado de error", async ({ page }) => {
      await prepararChat(page, error500);
      await abrirYPreguntar(page);
      await expect(panelDe(page).getByRole("alert")).toBeVisible();
      await auditar(page);
    });

    test("sin desbordes y con objetivos táctiles de 44 px", async ({ page }) => {
      await prepararChat(page, sse);
      await page.goto("/home");
      const fab = botonFlotante(page);
      await expect(fab).toBeVisible();
      await verificarMedidas(page, [fab]);

      await fab.click();
      const panel = panelDe(page);
      await expect(panel.getByRole("list", { name: "Suggestions" })).toBeVisible();
      await verificarMedidas(page, [panel.locator("button, a[href], textarea")]);

      await campoDe(page).fill("Space");
      await page.keyboard.press("Enter");
      await expect(panel.getByRole("link", { name: /Interstellar/ })).toBeVisible();
      await verificarMedidas(page, [panel.locator("button, a[href], textarea")]);
    });
  });
}

/** Ningún desborde horizontal y ningún objetivo visible por debajo de 44 px. */
async function verificarMedidas(page: Page, objetivos: Locator[]) {
  const desborde = await page.evaluate(() => {
    const raiz = document.documentElement;
    const dialogo = document.querySelector("dialog[open]");
    return {
      pagina: Math.max(0, raiz.scrollWidth - raiz.clientWidth),
      panel: dialogo ? dialogo.scrollWidth - dialogo.clientWidth : 0,
    };
  });
  expect(desborde).toEqual({ pagina: 0, panel: 0 });
  for (const objetivo of objetivos) {
    const chicos: string[] = [];
    for (const nodo of await objetivo.all()) {
      if (!(await nodo.isVisible())) continue;
      const caja = (await nodo.boundingBox())!;
      if (caja.width < 43.99 || caja.height < 43.99) {
        chicos.push(
          `${(await nodo.innerText()) || (await nodo.getAttribute("aria-label"))}: ${caja.width}x${caja.height}`
        );
      }
    }
    expect(chicos).toEqual([]);
  }
}

test.describe("Q-04 · con el teclado del celular abierto", () => {
  test.use({ viewport: { width: 375, height: 812 }, locale: "en-US" });

  test("el campo, el botón y el título siguen a la vista", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    await botonFlotante(page).click();
    await expect(campoDe(page)).toBeFocused();
    // El teclado ocupa más o menos la mitad de la pantalla: el área visible baja a 380 px.
    await page.setViewportSize({ width: 375, height: 380 });
    await campoDe(page).fill("Una pregunta larga ".repeat(20).slice(0, 300));
    const panel = panelDe(page);
    for (const objetivo of [
      campoDe(page),
      panel.getByRole("button", { name: "Send" }),
      panel.getByRole("button", { name: "Close the chat" }),
      panel.getByRole("heading", { name: "FilmAI Assistant" }),
    ]) {
      const caja = (await objetivo.boundingBox())!;
      expect(caja.y).toBeGreaterThanOrEqual(0);
      expect(caja.y + caja.height).toBeLessThanOrEqual(380 + 0.5);
    }
    // Con el campo en su alto máximo la conversación todavía tiene lugar.
    const log = (await panel.getByRole("log").boundingBox())!;
    expect(log.height).toBeGreaterThan(60);
  });
});

test.describe("Q-01 · teclado, foco y anuncios", () => {
  test.use({ viewport: { width: 1440, height: 900 }, locale: "en-US" });

  test("al abrir el foco va al campo y al cerrar vuelve al botón", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    const fab = botonFlotante(page);
    await fab.click();
    await expect(campoDe(page)).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(panelDe(page)).toBeHidden();
    await expect(fab).toBeFocused();

    await fab.click();
    await panelDe(page).getByRole("button", { name: "Close the chat" }).click();
    await expect(panelDe(page)).toBeHidden();
    await expect(fab).toBeFocused();
  });

  test("Tab da la vuelta dentro del panel y no sale a la página", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    await botonFlotante(page).click();
    const nombreEnFoco = () =>
      page.evaluate(() => {
        const el = document.activeElement as HTMLInputElement;
        return (
          el.getAttribute("aria-label") ??
          el.labels?.[0]?.textContent ??
          el.textContent?.trim() ??
          el.tagName
        );
      });
    const recorrido: (string | null)[] = [await nombreEnFoco()];
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press("Tab");
      recorrido.push(await nombreEnFoco());
    }
    // Campo → Enviar → Cerrar → tres sugerencias (orden del DOM) → campo.
    expect(recorrido.slice(0, 3)).toEqual(["Your message", "Send", "Close the chat"]);
    expect(recorrido.at(-1)).toBe("Your message");
    expect(await page.evaluate(() => !!document.activeElement?.closest("dialog"))).toBe(true);
    await page.keyboard.press("Shift+Tab");
    expect(await nombreEnFoco()).toBe(recorrido.at(-2));
  });

  test("la región de anuncios queda vacía durante la respuesta y lee solo la completa", async ({
    page,
  }) => {
    let soltar = () => {};
    const puedeTerminar = new Promise<void>((resolver) => (soltar = resolver));
    await prepararChat(page, async (route) => {
      await puedeTerminar;
      await sse(route);
    });
    await abrirYPreguntar(page);
    const panel = panelDe(page);
    const anuncios = panel.locator("p[aria-live='polite']");
    await expect(panel.getByRole("log")).toHaveAttribute("aria-live", "off");
    await expect(anuncios).toHaveText("");
    soltar();
    await expect(panel.getByRole("link", { name: /Interstellar/ })).toBeVisible();
    // Sin Markdown ni la URL de la imagen: queda el texto que se ve y se oiría.
    await expect(anuncios).toHaveText("Try Moon x");
  });
});

test("Q-01 · al elegir una sugerencia el foco queda en el campo", async ({ page }) => {
  await prepararChat(page, sse);
  await page.goto("/home");
  await botonFlotante(page).click();
  const panel = panelDe(page);
  await panel.getByRole("list", { name: "Suggestions" }).getByRole("button").first().click();
  await expect(panel.getByRole("link", { name: /Interstellar/ })).toBeVisible();
  await expect(campoDe(page)).toBeFocused();
});

test.describe("Q-03 · fallas forzadas", () => {
  test.use({ viewport: { width: 1440, height: 900 }, locale: "en-US" });

  test("sin red: mensaje traducido, la pregunta vuelve al campo y se puede reintentar", async ({
    page,
  }) => {
    let sinRed = true;
    await prepararChat(page, (route) => (sinRed ? route.abort("failed") : sse(route)));
    await abrirYPreguntar(page, "Space movies");
    const aviso = panelDe(page).getByRole("alert");
    await expect(aviso).toHaveText("We couldn’t connect. Check your connection and try again.");
    await expect(panelDe(page)).not.toContainText("Failed to fetch");
    await expect(campoDe(page)).toHaveValue("Space movies");
    sinRed = false;
    await page.keyboard.press("Enter");
    await expect(panelDe(page).getByRole("link", { name: /Interstellar/ })).toBeVisible();
    await expect(aviso).toHaveCount(0);
  });

  test("error del servidor (500, Internal Server Error)", async ({ page }) => {
    await prepararChat(page, error500);
    await abrirYPreguntar(page, "Space movies");
    await expect(panelDe(page).getByRole("alert")).toHaveText(
      "Something went wrong. Try again later."
    );
    await expect(campoDe(page)).toHaveValue("Space movies");
    await expect(panelDe(page).getByRole("button", { name: "Send" })).toBeVisible();
  });

  test("error del servidor sin cuerpo JSON (502, Bad Gateway)", async ({ page }) => {
    await prepararChat(page, (route) =>
      route.fulfill({ status: 502, contentType: "text/html", body: "<h1>Bad Gateway</h1>" })
    );
    await abrirYPreguntar(page, "Space movies");
    const aviso = panelDe(page).getByRole("alert");
    await expect(aviso).toBeVisible();
    await expect(aviso).not.toContainText(/Bad Gateway|<h1>|undefined|\[object/);
    await expect(campoDe(page)).toHaveValue("Space movies");
  });

  test("error dentro del stream: el servicio no está disponible", async ({ page }) => {
    await prepararChat(page, (route) =>
      route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
        body: frame("estado", { code: "searching" }) + frame("error", { code: "chat_unavailable" }),
      })
    );
    await abrirYPreguntar(page);
    await expect(panelDe(page).getByRole("alert")).toHaveText(
      "We can’t process your request right now. Try again later."
    );
    await expect(panelDe(page).getByRole("status")).toHaveCount(0);
  });

  test("429 (Too Many Requests) con espera: dice cuánto esperar", async ({ page }) => {
    await prepararChat(page, (route) =>
      route.fulfill({
        status: 429,
        headers: { "Retry-After": "30" },
        json: { code: "throttled", params: { retry_after_seconds: 30 }, errors: [] },
      })
    );
    await abrirYPreguntar(page, "Space movies");
    await expect(panelDe(page).getByRole("alert")).toHaveText(
      "There are too many requests. Try again in 30 seconds."
    );
    await expect(campoDe(page)).toHaveValue("Space movies");
  });

  test("respuesta lenta: muestra que trabaja, se puede cancelar y la respuesta llega", async ({
    page,
  }) => {
    let soltar = () => {};
    const puedeTerminar = new Promise<void>((resolver) => (soltar = resolver));
    await prepararChat(page, async (route) => {
      await puedeTerminar;
      await sse(route);
    });
    await abrirYPreguntar(page);
    const panel = panelDe(page);
    // Mientras espera: la pregunta a la vista, «Cancel» en lugar de «Send» y el campo editable.
    await expect(panel.getByText("Space", { exact: true })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Cancel" })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Send" })).toHaveCount(0);
    await expect(campoDe(page)).toBeEnabled();
    await page.waitForTimeout(1500);
    await expect(panel.getByRole("button", { name: "Cancel" })).toBeVisible();
    soltar();
    await expect(panel.getByRole("link", { name: /Interstellar/ })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Send" })).toBeVisible();
  });

  test("cancelación: avisa, conserva la pregunta y deja volver a enviar", async ({ page }) => {
    let intento = 0;
    await prepararChat(page, (route) =>
      ++intento === 1 ? new Promise<void>(() => {}) : sse(route)
    );
    await abrirYPreguntar(page, "A TV show");
    await panelDe(page).getByRole("button", { name: "Cancel" }).click();
    await expect(panelDe(page).getByRole("status")).toHaveText("Request canceled");
    await expect(campoDe(page)).toHaveValue("A TV show");
    // El botón «Cancel» se desmonta: el foco tiene que quedar en el campo, no en el `body`.
    await expect(campoDe(page)).toBeFocused();
    await expect(
      panelDe(page).getByRole("log").getByText("A TV show", { exact: true })
    ).toHaveCount(0);
    await page.keyboard.press("Enter");
    await expect(panelDe(page).getByRole("link", { name: /Interstellar/ })).toBeVisible();
    await expect(panelDe(page).getByText("Request canceled")).toHaveCount(0);
  });

  test("historial sin red: mensaje con «Retry» que vuelve a pedirlo", async ({ page }) => {
    let sinRed = true;
    await prepararChat(page, sse);
    await page.route(/\/api\/chat\/messages\/(\?.*)?$/, (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      return sinRed ? route.abort("failed") : route.fulfill({ json: { next: null, results: [] } });
    });
    await page.goto("/home");
    await botonFlotante(page).click();
    const panel = panelDe(page);
    await expect(panel.getByRole("alert")).toContainText("We couldn’t connect");
    sinRed = false;
    await panel.getByRole("button", { name: "Retry" }).click();
    await expect(panel.getByRole("alert")).toHaveCount(0);
    await expect(panel.getByRole("list", { name: "Suggestions" })).toBeVisible();
  });
});

test.describe("el botón flotante", () => {
  test.use({ viewport: { width: 1440, height: 900 }, locale: "en-US" });

  test("tiene mano y hover; deshabilitado no", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    const fab = botonFlotante(page);
    await expect(fab).toBeVisible();
    // El botón nace deshabilitado hasta que la sesión carga: medir antes daba
    // `not-allowed` (fallo intermitente en CI, 13/11/2026).
    await expect(fab).toBeEnabled();
    const estilo = () =>
      fab.evaluate((el) => {
        const s = getComputedStyle(el);
        return { cursor: s.cursor, fondo: s.backgroundColor, desplazamiento: s.translate };
      });
    const reposo = await estilo();
    expect(reposo.cursor).toBe("pointer");
    await fab.hover();
    await expect.poll(async () => (await estilo()).fondo).not.toBe(reposo.fondo);
    // Sube 2 px (`translate` de Tailwind 4, no `transform`).
    await expect.poll(async () => (await estilo()).desplazamiento).toBe("0px -2px");
    await expect(page.getByRole("contentinfo").getByRole("button")).toHaveCSS("cursor", "pointer");
  });

  test("con movimiento reducido cambia el color pero no se mueve", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await prepararChat(page, sse);
    await page.goto("/home");
    const fab = botonFlotante(page);
    await fab.hover();
    await expect(fab).toHaveCSS("translate", /^(none|0px)$/);
  });

  test("el texto sobre el amarillo del hover mantiene 4,5:1", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    const fab = botonFlotante(page);
    await fab.hover();
    await page.waitForTimeout(300);
    const razon = await fab.evaluate((el) => {
      // El navegador normaliza cualquier formato de color (oklch, color-mix…) a RGBA.
      const lienzo = document
        .createElement("canvas")
        .getContext("2d", { willReadFrequently: true })!;
      const rgba = (color: string) => {
        lienzo.clearRect(0, 0, 1, 1);
        lienzo.fillStyle = color;
        lienzo.fillRect(0, 0, 1, 1);
        return Array.from(lienzo.getImageData(0, 0, 1, 1).data);
      };
      const luz = ([r, g, b]: number[]) => {
        const f = (c: number) =>
          c / 255 <= 0.03928 ? c / 255 / 12.92 : ((c / 255 + 0.055) / 1.055) ** 2.4;
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
      };
      const estilo = getComputedStyle(el);
      const [r, g, b, alfa] = rgba(estilo.backgroundColor);
      // El fondo es translúcido: se compone contra el peor caso, negro puro.
      const sobreNegro = [r, g, b].map((c) => (c * alfa) / 255);
      const [claro, oscuro] = [luz(sobreNegro), luz(rgba(estilo.color))].sort((x, y) => y - x);
      return (claro + 0.05) / (oscuro + 0.05);
    });
    expect(razon).toBeGreaterThanOrEqual(4.5);
  });
});

test.describe("el cursor de mano en toda la app", () => {
  test.use({ viewport: { width: 1440, height: 900 }, locale: "en-US" });

  test("botones activos con mano; deshabilitados, textos y fondo sin ella", async ({ page }) => {
    await prepararChat(page, sse);
    await page.goto("/home");
    await botonFlotante(page).click();
    const panel = panelDe(page);
    await expect(panel.getByRole("button", { name: "Close the chat" })).toHaveCSS(
      "cursor",
      "pointer"
    );
    await expect(
      panel.getByRole("list", { name: "Suggestions" }).getByRole("button").first()
    ).toHaveCSS("cursor", "pointer");
    // «Send» sin texto está `aria-disabled`: cursor de prohibido, no de mano.
    await expect(panel.getByRole("button", { name: "Send" })).toHaveCSS("cursor", "not-allowed");
    await expect(panel.getByRole("heading", { name: "FilmAI Assistant" })).not.toHaveCSS(
      "cursor",
      "pointer"
    );
    await expect(panel.getByRole("log")).not.toHaveCSS("cursor", "pointer");
  });
});
