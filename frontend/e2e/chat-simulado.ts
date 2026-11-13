import type { Page, Route } from "@playwright/test";

import { conSesion, simularCatalogo } from "./api-simulada";

/**
 * El panel del chat (PR 6) con la API simulada: el `POST` devuelve un
 * `text/event-stream` armado a mano con el contrato de `design.md`, y el `GET`
 * sirve páginas de historial con cursor como la API real (PR 4).
 */

export const frame = (evento: string, datos: unknown) =>
  `event: ${evento}\ndata: ${JSON.stringify(datos)}\n\n`;

export const RESPUESTA =
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

/** Una página del historial: de más nuevo a más viejo, como la manda la API. */
export const paginaVacia = { next: null, results: [] };
export const mensaje = (id: number, autor: "usuario" | "chatbot", texto: string) => ({
  id,
  autor,
  texto,
  tarjetas: [],
  fecha_hora: "2026-11-06T12:00:00Z",
});

export type Historial = (cursor: string | null) => unknown;

export async function prepararChat(
  page: Page,
  responder: (route: Route) => Promise<void> | void,
  historial: Historial = () => paginaVacia
) {
  await conSesion(page);
  await simularCatalogo(page);
  const preparar: string[] = [];
  await page.route("**/api/chat/preparar/", (route) => {
    preparar.push(route.request().headers()["x-csrftoken"] ?? "");
    return route.fulfill({ status: 202, body: "" });
  });
  const pedidosHistorial: (string | null)[] = [];
  await page.route(/\/api\/chat\/messages\//, (route) => {
    if (route.request().method() === "POST") return responder(route);
    const cursor = new URL(route.request().url()).searchParams.get("cursor");
    pedidosHistorial.push(cursor);
    return route.fulfill({ status: 200, json: historial(cursor) });
  });
  return { preparar, pedidosHistorial };
}

/**
 * El FAB flotante: el pie también tiene un botón «Ask FilmAI», pero sin
 * `aria-expanded`. Se pide además el nombre porque otras pantallas tienen
 * popups con `aria-expanded` (la ficha, «Stream or rent»).
 */
export const botonFlotante = (page: Page) =>
  page.getByRole("button", { name: /^Ask FilmAI/ }).and(page.locator("[aria-expanded]"));

export const sse = (route: Route) =>
  route.fulfill({
    status: 200,
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
    body: RESPUESTA,
  });
