import { expect, test, type Page } from "@playwright/test";

import { auditar } from "./axe";
import { conSesion } from "./api-simulada";

/**
 * Watching como lista (PR 4, canvas «Watching · list page» y «Lists»): el menú
 * ⋯ de cada tarjeta, el toast con Undo, el estado vacío y la grilla de /lists
 * en 4, 2 y 1 columnas. La API es simulada con memoria: `PUT
 * /api/lists/status/` mueve el título y las listas lo reflejan.
 */
type Item = { item_id: number; id_tmdb: number; tipo: "movie" | "tv"; titulo: string };
const TITULOS: Item[] = [
  { item_id: 1, id_tmdb: 101, tipo: "movie", titulo: "Lanterns" },
  { item_id: 2, id_tmdb: 102, tipo: "tv", titulo: "Harbor Lights" },
  { item_id: 3, id_tmdb: 103, tipo: "tv", titulo: "Night Shift" },
  { item_id: 4, id_tmdb: 104, tipo: "tv", titulo: "Paper Moon" },
];

async function prepararViendo(page: Page, { falla = false } = {}) {
  const sim = {
    viendo: structuredClone(TITULOS),
    vistas: [] as Item[],
    pedidos: [] as { estado: string | null; id_tmdb: number }[],
    falla,
    calificadas: [] as number[],
    siguienteItem: 500,
  };
  const resumen = (id: number, nombre: string, clave: string | null, items: Item[]) => ({
    id,
    nombre,
    clave,
    tipo: clave ? "predeterminada" : "personalizada",
    cantidad_items: items.length,
    cantidad_peliculas: items.filter((i) => i.tipo === "movie").length,
    cantidad_series: items.filter((i) => i.tipo === "tv").length,
    preview_posters: items.slice(0, 5).map((i) => `/poster-${i.item_id}.jpg`),
  });
  const todas = () => [
    resumen(1, "Favorites", "favoritos", []),
    resumen(2, "Watchlist", "pendientes", []),
    resumen(4, "Watching", "viendo", sim.viendo),
    resumen(3, "Watched", "vistas", sim.vistas),
    resumen(10, "Maratón", null, TITULOS),
    resumen(11, "Clásicos", null, []),
  ];
  await conSesion(page);
  await page.route("https://image.tmdb.org/**", (route) => route.fulfill({ status: 404 }));
  await page.route("**/api/reviews/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/reviews/mias/")
      return route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
    if (url.pathname === "/api/reviews/" && route.request().method() === "POST") {
      const { id_tmdb } = route.request().postDataJSON();
      sim.calificadas.push(id_tmdb);
      // Como el servidor: calificar mueve a Vistas.
      const hallado = sim.viendo.find((i) => i.id_tmdb === id_tmdb);
      if (hallado) {
        sim.viendo = sim.viendo.filter((i) => i !== hallado);
        sim.vistas.push(hallado);
      }
      return route.fulfill({
        status: 201,
        json: { id: 9, valor: 8, texto: null, fecha: "2026-11-17", moderada: false },
      });
    }
    return route.fallback();
  });
  await page.route("**/api/lists/**", (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const json = (cuerpo: unknown, status = 200) => route.fulfill({ status, json: cuerpo });
    if (url.pathname === "/api/lists/status/" && request.method() === "PUT") {
      const { id_tmdb, estado } = request.postDataJSON();
      sim.pedidos.push({ estado, id_tmdb });
      if (sim.falla) return json({ code: "server_error", params: {}, errors: [] }, 500);
      const previo = [...sim.viendo, ...sim.vistas].find((i) => i.id_tmdb === id_tmdb);
      const anterior = sim.viendo.some((i) => i.id_tmdb === id_tmdb)
        ? "viendo"
        : sim.vistas.some((i) => i.id_tmdb === id_tmdb)
          ? "vistas"
          : null;
      sim.viendo = sim.viendo.filter((i) => i.id_tmdb !== id_tmdb);
      sim.vistas = sim.vistas.filter((i) => i.id_tmdb !== id_tmdb);
      // Volver a anotarlo crea un ingreso nuevo, que el servidor ordena primero.
      if (previo && estado === "viendo")
        sim.viendo.unshift({ ...previo, item_id: sim.siguienteItem++ });
      if (previo && estado === "vistas") sim.vistas.push(previo);
      return json({
        estado,
        estado_anterior: anterior,
        listas: [
          { clave: "viendo", contiene: estado === "viendo", item_id: sim.siguienteItem - 1 },
        ],
      });
    }
    const items = url.pathname.match(/^\/api\/lists\/(\d+)\/items\/$/);
    if (items) {
      const lista = Number(items[1]) === 4 ? sim.viendo : Number(items[1]) === 3 ? sim.vistas : [];
      return json({
        total: lista.length,
        next: null,
        previous: null,
        results: lista.map((i) => ({
          item_id: i.item_id,
          fecha_agregado: "2026-11-10T10:00:00Z",
          id_tmdb: i.id_tmdb,
          tipo: i.tipo,
          titulo: i.titulo,
          poster: null,
          anio: 2025,
          calificacion_promedio: 7.4,
          disponible: true,
        })),
      });
    }
    const una = url.pathname.match(/^\/api\/lists\/(\d+)\/$/);
    if (una) return json(todas().find((l) => l.id === Number(una[1])));
    if (url.pathname === "/api/lists/") return json(todas());
    return json({ code: "not_found", params: {}, errors: [] }, 404);
  });
  return sim;
}

const toast = (page: Page) => page.locator("[data-sonner-toast]");
const masDe = (page: Page, titulo: string) =>
  page.getByRole("button", { name: `More for ${titulo}` });
const bloques = [
  { nombre: "escritorio 1440×900", width: 1440, height: 900, escritorio: true },
  { nombre: "celular 375×812", width: 375, height: 812, escritorio: false },
] as const;

for (const bloque of bloques) {
  test.describe(`Watching en ${bloque.nombre}`, () => {
    test.use({
      viewport: { width: bloque.width, height: bloque.height },
      hasTouch: !bloque.escritorio,
      isMobile: !bloque.escritorio,
      locale: "en-US",
      extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
    });

    test("página genérica: título con el conteo, ⋯ en cada tarjeta y sin ícono arriba del buscador", async ({
      page,
    }) => {
      await prepararViendo(page);
      await page.goto("/lists/4");

      const titulo = page.getByRole("heading", { level: 1, name: "Watching" });
      await expect(titulo).toBeVisible();
      const conteo = page.getByText(
        bloque.escritorio ? "4 items · 1 movie · 3 TV shows" : "4 items",
        {
          exact: true,
        }
      );
      await expect(conteo).toBeVisible();
      // El conteo está en la línea del título.
      const caja = (await titulo.boundingBox())!;
      const cajaConteo = (await conteo.boundingBox())!;
      expect(Math.abs(caja.y + caja.height - (cajaConteo.y + cajaConteo.height))).toBeLessThan(40);
      expect(cajaConteo.x).toBeGreaterThan(caja.x + caja.width - 1);
      await expect(page.getByRole("search")).toBeVisible();
      for (const { titulo: nombre } of TITULOS) await expect(masDe(page, nombre)).toBeVisible();

      // 36 px visibles; en celular el área táctil llega a 44 px.
      const boton = (await masDe(page, "Lanterns").boundingBox())!;
      expect(boton.width).toBeCloseTo(bloque.escritorio ? 36 : 44, 0);
      expect(boton.height).toBeCloseTo(bloque.escritorio ? 36 : 44, 0);
      const columnas = await page
        .locator("main ul")
        .first()
        .evaluate((ul) => getComputedStyle(ul).gridTemplateColumns.split(" ").length);
      expect(columnas).toBe(bloque.escritorio ? 7 : 2);
      await auditar(page);
    });

    test("el menú ⋯: ítems, Esc y clic afuera devuelven el foco, uno solo abierto", async ({
      page,
    }) => {
      await prepararViendo(page);
      await page.goto("/lists/4");
      await expect(masDe(page, "Lanterns")).toBeVisible();

      await masDe(page, "Lanterns").click();
      await expect(masDe(page, "Lanterns")).toHaveAttribute("aria-expanded", "true");
      const menu = page.getByRole("menu", { name: "More for Lanterns" });
      await expect(menu.getByRole("menuitem")).toHaveText([
        "Mark as finished",
        "Rate it…",
        "Remove from Watching",
      ]);
      if (!bloque.escritorio)
        await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
      await auditar(page);

      await page.keyboard.press("ArrowDown");
      await expect(menu.getByRole("menuitem", { name: "Rate it…" })).toBeFocused();
      await page.keyboard.press("Escape");
      await expect(menu).toHaveCount(0);
      await expect(masDe(page, "Lanterns")).toBeFocused();

      // Clic afuera (el fondo del diálogo modal).
      await masDe(page, "Harbor Lights").click();
      await expect(page.getByRole("menu")).toHaveCount(1);
      await page.mouse.click(5, bloque.height / 2);
      await expect(page.getByRole("menu")).toHaveCount(0);
      await expect(masDe(page, "Harbor Lights")).toBeFocused();
    });

    test("Mark as finished: sale de la grilla, avisa con Undo y Undo la devuelve a su lugar", async ({
      page,
    }) => {
      const sim = await prepararViendo(page);
      await page.goto("/lists/4");
      await masDe(page, "Harbor Lights").click();
      await page.getByRole("menuitem", { name: "Mark as finished" }).click();

      await expect(page.getByText("Harbor Lights moved to Watched", { exact: true })).toBeVisible();
      await expect(page.getByRole("link", { name: /Harbor Lights/ })).toHaveCount(0);
      await expect(
        page.getByText(bloque.escritorio ? "3 items · 1 movie · 2 TV shows" : "3 items", {
          exact: true,
        })
      ).toBeVisible();
      expect(sim.pedidos).toEqual([{ estado: "vistas", id_tmdb: 102 }]);
      await expect(page.getByRole("button", { name: "Rate it" })).toHaveCount(
        bloque.escritorio ? 1 : 0
      );

      // Ubicación del toast: arriba al centro en escritorio; abajo, 12 px sobre la barra, en celular.
      // Se espera a que termine de entrar (Sonner lo anima desde abajo).
      await expect
        .poll(async () => {
          const caja = (await toast(page).first().boundingBox())!;
          if (bloque.escritorio)
            return caja.y < 120 && Math.abs(caja.x + caja.width / 2 - bloque.width / 2) <= 8;
          const barra = (await page.getByRole("navigation", { name: "Main" }).boundingBox())!;
          const hueco = barra.y - (caja.y + caja.height);
          return (
            hueco >= 10 && hueco <= 14 && Math.abs(caja.x + caja.width / 2 - bloque.width / 2) <= 8
          );
        })
        .toBe(true);
      await auditar(page);

      await page.getByRole("button", { name: "Undo" }).click();
      await expect(page.getByRole("link", { name: /Harbor Lights/ })).toBeVisible();
      await expect(page.getByRole("button", { name: "Undo" })).toHaveCount(0);
      // Vuelve a su posición anterior (segunda), aunque el servidor lo anote primero.
      const orden = await page
        .locator("main ul li a")
        .evaluateAll((nodos) => nodos.map((n) => n.getAttribute("href")));
      expect(orden).toEqual([
        "/movie/101?from=list-4",
        "/tv/102?from=list-4",
        "/tv/103?from=list-4",
        "/tv/104?from=list-4",
      ]);
      expect(sim.pedidos.map((p) => p.estado)).toEqual(["vistas", "viendo"]);
    });

    test("Remove from Watching: toast con Undo y una acción nueva reemplaza al toast", async ({
      page,
    }) => {
      const sim = await prepararViendo(page);
      await page.goto("/lists/4");

      await masDe(page, "Lanterns").click();
      await page.getByRole("menuitem", { name: "Remove from Watching" }).click();
      await expect(page.getByText("Lanterns removed from Watching", { exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: "Rate it" })).toHaveCount(0);

      await masDe(page, "Night Shift").click();
      await page.getByRole("menuitem", { name: "Mark as finished" }).click();
      await expect(page.getByText("Night Shift moved to Watched", { exact: true })).toBeVisible();
      await expect(page.getByText("Lanterns removed from Watching")).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Undo" })).toHaveCount(1);
      expect(sim.pedidos.map((p) => p.estado)).toEqual([null, "vistas"]);
    });

    test("Rate it…: abre el diálogo de la ficha y calificar la pasa a Watched", async ({
      page,
    }) => {
      const sim = await prepararViendo(page);
      await page.goto("/lists/4");

      await masDe(page, "Lanterns").click();
      await page.getByRole("menuitem", { name: "Rate it…" }).click();
      const dialogo = page.getByRole("dialog", { name: "Rate Lanterns" });
      await dialogo.getByRole("radio", { name: "8 out of 10" }).click();
      await dialogo.getByRole("button", { name: "Post" }).click();

      await expect(page.getByText("Rated ★ 8 · Moved to Watched", { exact: true })).toBeVisible();
      await expect(page.getByRole("link", { name: /Lanterns/ })).toHaveCount(0);
      expect(sim.calificadas).toEqual([101]);
    });

    test("si falla, la tarjeta vuelve y el toast de error no trae Undo", async ({ page }) => {
      await prepararViendo(page, { falla: true });
      await page.goto("/lists/4");

      await masDe(page, "Lanterns").click();
      await page.getByRole("menuitem", { name: "Mark as finished" }).click();

      await expect(
        page.getByText("Couldn’t update the status. Try again.", { exact: true })
      ).toBeVisible();
      await expect(page.getByRole("link", { name: /Lanterns/ })).toBeVisible();
      await expect(page.getByRole("button", { name: "Undo" })).toHaveCount(0);
    });

    test("al sacar el último título aparece el estado vacío y «Open Watchlist» va a Pendientes", async ({
      page,
    }) => {
      const sim = await prepararViendo(page);
      sim.viendo = sim.viendo.slice(0, 1);
      await page.goto("/lists/4");
      await masDe(page, "Lanterns").click();
      await page.getByRole("menuitem", { name: "Mark as finished" }).click();

      await expect(page.getByRole("heading", { name: "Nothing in progress" })).toBeVisible();
      await expect(page.getByRole("link", { name: /Lanterns/ })).toHaveCount(0);
      await expect(page.getByRole("link", { name: "Open Watchlist" })).toHaveAttribute(
        "href",
        "/lists/2"
      );
      await auditar(page);
    });
  });
}

// Las columnas de /lists, medidas en el navegador (el canvas: 4, 2 y 1).
const anchos = [
  { ancho: 1440, columnas: 4 },
  { ancho: 1180, columnas: 4 },
  { ancho: 1100, columnas: 2 },
  { ancho: 768, columnas: 2 },
  { ancho: 640, columnas: 2 },
  { ancho: 375, columnas: 1 },
] as const;

for (const { ancho, columnas } of anchos) {
  test.describe(`/lists a ${ancho} px`, () => {
    test.use({ viewport: { width: ancho, height: 900 }, locale: "en-US" });

    test(`tiene ${columnas} columna${columnas === 1 ? "" : "s"}, sin desborde`, async ({
      page,
    }) => {
      await prepararViendo(page);
      await page.goto("/lists");
      await expect(page.getByRole("heading", { level: 2, name: "Watching" })).toBeVisible();

      const lecturas = await page
        .locator("main ul")
        .first()
        .evaluate((ul) => ({
          columnas: getComputedStyle(ul).gridTemplateColumns.split(" ").length,
          desborde: document.documentElement.scrollWidth > window.innerWidth,
        }));
      expect(lecturas).toEqual({ columnas, desborde: false });
      // Las 4 predeterminadas, y después las propias.
      const nombres = await page.locator("main h2").allTextContents();
      expect(nombres).toEqual([
        "Favorites",
        "Watchlist",
        "Watching",
        "Watched",
        "Maratón",
        "Clásicos",
      ]);
      if (columnas === 4) {
        // La primera fila son las 4 predeterminadas.
        const ys = await Promise.all(
          ["Favorites", "Watchlist", "Watching", "Watched"].map(
            async (n) => (await page.getByRole("heading", { level: 2, name: n }).boundingBox())!.y
          )
        );
        expect(new Set(ys).size).toBe(1);
      }
      if (ancho === 1440 || ancho === 375) await auditar(page);
    });
  });
}
