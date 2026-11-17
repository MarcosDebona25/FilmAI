import { expect, test, type Page } from "@playwright/test";

import { auditar } from "./axe";
import { conSesion, simularCatalogo } from "./api-simulada";

/**
 * El botón de estado de la ficha (PR 4, canvas «Watching · title page»): menú,
 * cambio optimista, toast con Undo, calificar que mueve a Watched y el error.
 * La API es simulada con memoria: `PUT /api/lists/status/` cambia el estado y
 * `GET /api/lists/?id_tmdb=` lo devuelve, como el backend real.
 */
type Estado = "pendientes" | "viendo" | "vistas" | null;

async function prepararEstado(page: Page, inicial: Estado = "pendientes") {
  const sim = { estado: inicial, falla: false, pedidos: [] as unknown[], mia: false };
  const listas = () =>
    (["favoritos", "pendientes", "viendo", "vistas"] as const).map((clave, i) => ({
      id: i + 1,
      nombre: clave,
      clave,
      tipo: "predeterminada",
      cantidad_items: 1,
      contiene: sim.estado === clave,
      item_id: sim.estado === clave ? 70 + i : null,
    }));
  await simularCatalogo(page);
  await page.route("**/api/reviews/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/reviews/mias/")
      return sim.mia
        ? route.fulfill({ json: { id: 9, valor: 8, texto: null, fecha: "2026-11-15" } })
        : route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
    if (url.pathname === "/api/reviews/" && route.request().method() === "POST") {
      // Como el servidor: calificar mueve a Vistas desde cualquier estado.
      sim.mia = true;
      sim.estado = "vistas";
      return route.fulfill({
        status: 201,
        json: { id: 9, valor: 8, texto: null, fecha: "2026-11-15" },
      });
    }
    return route.fallback();
  });
  await page.route("**/api/lists/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/api/lists/status/" && request.method() === "PUT") {
      const { estado } = request.postDataJSON();
      sim.pedidos.push(estado);
      if (sim.falla)
        return route.fulfill({
          status: 500,
          json: { code: "server_error", params: {}, errors: [] },
        });
      const anterior = sim.estado;
      sim.estado = estado;
      return route.fulfill({ json: { estado, estado_anterior: anterior, listas: listas() } });
    }
    if (url.pathname === "/api/lists/" && request.method() === "GET")
      return route.fulfill({ json: listas() });
    return route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
  });
  return sim;
}

const toast = (page: Page) => page.locator("[data-sonner-toast]");
const botonEstado = (page: Page) => page.getByRole("button", { name: /^Status/ });

const bloques = [
  { nombre: "escritorio 1440×900", width: 1440, height: 900, escritorio: true },
  { nombre: "celular 375×812", width: 375, height: 812, escritorio: false },
] as const;

for (const bloque of bloques) {
  test.describe(`estado de la ficha en ${bloque.nombre}`, () => {
    test.use({
      viewport: { width: bloque.width, height: bloque.height },
      locale: "en-US",
      extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
    });

    test("elegir un estado: cambia el botón, avisa con Undo y Undo lo revierte", async ({
      page,
    }) => {
      await conSesion(page);
      const sim = await prepararEstado(page);
      await page.goto("/movie/157336");
      await expect(botonEstado(page)).toHaveText(/Watchlist/);

      await botonEstado(page).click();
      const menu = page.getByRole("menu", { name: "Status for Interstellar" });
      await expect(menu.getByRole("menuitemradio", { name: /Watchlist/ })).toHaveAttribute(
        "aria-checked",
        "true"
      );
      await auditar(page);
      await menu.getByRole("menuitemradio", { name: /Watching/ }).click();

      await expect(botonEstado(page)).toHaveText(/Watching/);
      await expect(page.getByText("Moved to Watching", { exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: "Undo" })).toBeVisible();
      expect(sim.pedidos).toEqual(["viendo"]);
      await expect(botonEstado(page)).toBeFocused();
      await auditar(page);

      // Ubicación: arriba al centro en escritorio; abajo, 12 px sobre la barra, en celular.
      const caja = (await toast(page).first().boundingBox())!;
      const centro = caja.x + caja.width / 2;
      // Centrado, con hasta media barra de desplazamiento (15 px) de diferencia.
      expect(Math.abs(centro - bloque.width / 2)).toBeLessThanOrEqual(8);
      if (bloque.escritorio) {
        expect(caja.y).toBeLessThan(120);
      } else {
        const barra = (await page.getByRole("navigation", { name: "Main" }).boundingBox())!;
        expect(barra.y - (caja.y + caja.height)).toBeGreaterThanOrEqual(10);
        expect(barra.y - (caja.y + caja.height)).toBeLessThanOrEqual(14);
      }

      await page.getByRole("button", { name: "Undo" }).click();
      await expect(page.getByText("Back to Watchlist", { exact: true })).toBeVisible();
      await expect(botonEstado(page)).toHaveText(/Watchlist/);
      await expect(page.getByRole("button", { name: "Undo" })).toHaveCount(0);
      expect(sim.pedidos).toEqual(["viendo", "pendientes"]);
    });

    test("un segundo cambio reemplaza el toast y Undo vuelve solo un paso", async ({ page }) => {
      await conSesion(page);
      await prepararEstado(page);
      await page.goto("/movie/157336");

      for (const nombre of [/Watching/, /Watched/]) {
        await botonEstado(page).click();
        await page.getByRole("menuitemradio", { name: nombre }).click();
      }

      await expect(page.getByText("Moved to Watched", { exact: true })).toBeVisible();
      await expect(page.getByText("Moved to Watching", { exact: true })).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Undo" })).toHaveCount(1);
      await page.getByRole("button", { name: "Undo" }).click();
      await expect(botonEstado(page)).toHaveText(/Watching/);
    });

    test("quitar el estado: «Status removed» con Undo", async ({ page }) => {
      await conSesion(page);
      await prepararEstado(page);
      await page.goto("/movie/157336");

      await botonEstado(page).click();
      await page.getByRole("menuitem", { name: "Remove status" }).click();

      await expect(page.getByText("Status removed", { exact: true })).toBeVisible();
      await expect(botonEstado(page)).toHaveText(/Status/);
      await expect(botonEstado(page)).not.toHaveText(/Watch/);
      await page.getByRole("button", { name: "Undo" }).click();
      await expect(botonEstado(page)).toHaveText(/Watchlist/);
    });

    test("si falla, vuelve al estado anterior y el toast de error no trae Undo", async ({
      page,
    }) => {
      await conSesion(page);
      const sim = await prepararEstado(page);
      sim.falla = true;
      await page.goto("/movie/157336");

      await botonEstado(page).click();
      await page.getByRole("menuitemradio", { name: /Watching/ }).click();

      await expect(
        page.getByText("Couldn’t update the status. Try again.", { exact: true })
      ).toBeVisible();
      await expect(botonEstado(page)).toHaveText(/Watchlist/);
      await expect(page.getByRole("button", { name: "Undo" })).toHaveCount(0);
      await auditar(page);
    });

    test("calificar algo de Watchlist lo mueve a Watched y Undo lo restaura sin perder la nota", async ({
      page,
    }) => {
      await conSesion(page);
      const sim = await prepararEstado(page);
      await page.goto("/movie/157336");

      await page.getByRole("button", { name: "Rate" }).click();
      const dialogo = page.getByRole("dialog", { name: "Rate Interstellar" });
      await dialogo.getByRole("radio", { name: "8 out of 10" }).click();
      await dialogo.getByRole("button", { name: "Post" }).click();

      await expect(page.getByText("Rated ★ 8 · Moved to Watched", { exact: true })).toBeVisible();
      await expect(botonEstado(page)).toHaveText(/Watched/);
      await page.getByRole("button", { name: "Undo" }).click();

      await expect(botonEstado(page)).toHaveText(/Watchlist/);
      await expect(page.getByText("Back to Watchlist", { exact: true })).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Your rating: 8 out of 10. Edit" })
      ).toBeVisible();
      expect(sim.pedidos).toEqual(["pendientes"]);
    });

    test("calificar algo que ya está en Watched dice solo «Rated ★ 8», sin Undo", async ({
      page,
    }) => {
      await conSesion(page);
      await prepararEstado(page, "vistas");
      await page.goto("/movie/157336");

      await page.getByRole("button", { name: "Rate" }).click();
      const dialogo = page.getByRole("dialog", { name: "Rate Interstellar" });
      await dialogo.getByRole("radio", { name: "8 out of 10" }).click();
      await dialogo.getByRole("button", { name: "Post" }).click();

      await expect(page.getByText("Rated ★ 8", { exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: "Undo" })).toHaveCount(0);
    });

    test("el toast con Undo se va solo a los 6 segundos y el cambio queda", async ({ page }) => {
      await conSesion(page);
      await prepararEstado(page);
      await page.goto("/movie/157336");

      await botonEstado(page).click();
      await page.getByRole("menuitemradio", { name: /Watching/ }).click();
      await expect(page.getByText("Moved to Watching", { exact: true })).toBeVisible();

      await page.waitForTimeout(4500);
      await expect(page.getByText("Moved to Watching", { exact: true })).toBeVisible();
      await expect(page.getByText("Moved to Watching", { exact: true })).toBeHidden({
        timeout: 3500,
      });
      await expect(botonEstado(page)).toHaveText(/Watching/);
    });

    test("Escape cierra el menú y el foco vuelve al botón", async ({ page }) => {
      await conSesion(page);
      await prepararEstado(page);
      await page.goto("/movie/157336");

      await botonEstado(page).click();
      await expect(page.getByRole("menu")).toBeVisible();
      await page.keyboard.press("Escape");

      await expect(page.getByRole("menu")).toHaveCount(0);
      await expect(botonEstado(page)).toBeFocused();
    });
  });
}

test.describe("estado de la ficha con teclado (escritorio)", () => {
  test.use({
    viewport: { width: 1440, height: 900 },
    locale: "en-US",
    extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
  });

  test("Enter abre, las flechas mueven, Enter elige y el foco vuelve al botón", async ({
    page,
  }) => {
    await conSesion(page);
    await prepararEstado(page);
    await page.goto("/movie/157336");

    await botonEstado(page).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("menuitemradio", { name: /Watchlist/ })).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await expect(page.getByRole("menuitemradio", { name: /Watching/ })).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(botonEstado(page)).toHaveText(/Watching/);
    await expect(botonEstado(page)).toBeFocused();
    await expect(page.getByText("Moved to Watching", { exact: true })).toBeVisible();
    // Undo se alcanza con Tab y el aviso no le sacó el foco al botón.
    await expect(page.getByRole("button", { name: "Undo" })).toBeVisible();
  });
});

test.describe("estado de la ficha en celular: hoja inferior", () => {
  test.use({
    viewport: { width: 375, height: 812 },
    locale: "en-US",
    extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
  });

  test("la hoja sale desde abajo con filas de 60 px y tocar el fondo la cierra sin cambios", async ({
    page,
  }) => {
    await conSesion(page);
    const sim = await prepararEstado(page);
    await page.goto("/movie/157336");

    await botonEstado(page).click();
    const hoja = page.getByRole("dialog", { name: "Status for Interstellar" });
    await expect(hoja.getByRole("heading", { name: "Status for Interstellar" })).toBeVisible();
    const caja = (await hoja.boundingBox())!;
    expect(Math.round(caja.y + caja.height)).toBe(812);
    const fila = (await hoja.getByRole("menuitemradio").first().boundingBox())!;
    expect(fila.height).toBeGreaterThanOrEqual(60);

    await page.mouse.click(187, 40);

    await expect(hoja).toHaveCount(0);
    expect(sim.pedidos).toEqual([]);
    await expect(botonEstado(page)).toHaveText(/Watchlist/);
  });
});
