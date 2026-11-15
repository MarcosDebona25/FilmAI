import { expect, test, type Page } from "@playwright/test";

import { auditar } from "./axe";
import { prepararCuenta } from "./cuenta";

/**
 * Banda «Suggested for this list» del detalle de una lista (canvas, sección
 * 14). La API de `lists/` se simula en memoria: no hace falta el backend.
 */

const viewports = [
  { name: "escritorio", width: 1440, height: 900, movil: false },
  { name: "celular", width: 375, height: 812, movil: true },
] as const;

type Item = { item_id: number; id_tmdb: number; tipo: "movie" | "tv"; titulo: string };
type Lista = {
  id: number;
  nombre: string;
  clave: "favoritos" | "pendientes" | "vistas" | null;
  items: Item[];
};

const POR_PAGINA = 6;
const SUGERIDAS = [
  "The Odyssey",
  "Blade Runner 2049",
  "Arrival",
  "Runner",
  "Foundation",
  "Ex Machina",
  "Annihilation",
  "Moon",
  "Solaris",
  "Gattaca",
  "Sunshine",
  "Primer",
  "Coherence",
  "Contact",
  "Silo",
].map((titulo, indice) => ({
  id_tmdb: 5000 + indice,
  tipo: indice % 5 === 4 ? ("tv" as const) : ("movie" as const),
  titulo,
  poster: indice % 2 === 0 ? `/sugerida-${indice}.jpg` : null,
  anio: 2010 + indice,
  calificacion_promedio: 7.6,
  origen: "catalogo" as const,
}));

function listas(): Lista[] {
  const items = (desde: number, cantidad: number): Item[] =>
    Array.from({ length: cantidad }, (_, i) => ({
      item_id: desde + i,
      id_tmdb: 1000 + desde + i,
      tipo: "movie",
      titulo: `Title ${String(desde + i).padStart(2, "0")}`,
    }));
  return [
    { id: 1, nombre: "Favorites", clave: "favoritos", items: items(1, 2) },
    { id: 2, nombre: "Watchlist", clave: "pendientes", items: items(10, 2) },
    { id: 3, nombre: "Watched", clave: "vistas", items: items(20, 2) },
    { id: 10, nombre: "Sci Fi", clave: null, items: items(30, 3) },
  ];
}

/** `lists/` en memoria: resumen, ítems, sugerencias paginadas y alta de un ítem. */
async function backend(page: Page) {
  await prepararCuenta(page, "en");
  const estado = { listas: listas(), pedidos: [] as string[] };
  await page.route("https://image.tmdb.org/**", (route) =>
    route.fulfill({ path: "public/collage-posters/Opcion 1.jpg" })
  );
  await page.route("**/api/lists/**", (route) => {
    const pedido = route.request();
    const url = new URL(pedido.url());
    const ruta = url.pathname.replace(/^.*\/api\/lists\//, "");
    estado.pedidos.push(`${pedido.method()} ${ruta}${url.search}`);
    const [id, recurso] = ruta.split("/");
    const lista = estado.listas.find((l) => l.id === Number(id));
    if (!lista)
      return route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
    const comoItem = (i: Item) => ({
      item_id: i.item_id,
      fecha_agregado: "2026-11-01T10:00:00Z",
      id_tmdb: i.id_tmdb,
      tipo: i.tipo,
      titulo: i.titulo,
      poster: null,
      anio: 2020,
      calificacion_promedio: 7,
      disponible: true,
    });
    if (!recurso)
      return route.fulfill({
        json: {
          id: lista.id,
          nombre: lista.nombre,
          clave: lista.clave,
          tipo: lista.clave ? "predeterminada" : "personalizada",
          cantidad_items: lista.items.length,
          cantidad_peliculas: lista.items.filter((i) => i.tipo === "movie").length,
          cantidad_series: lista.items.filter((i) => i.tipo === "tv").length,
          preview_posters: [],
        },
      });
    if (recurso === "suggestions") {
      // Como el backend: Pendientes no tiene sugerencias.
      if (lista.clave === "pendientes")
        return route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
      const pagina = Number(url.searchParams.get("pagina") ?? 1);
      const enLista = new Set(lista.items.map((i) => i.id_tmdb));
      const pool = SUGERIDAS.filter((s) => !enLista.has(s.id_tmdb));
      return route.fulfill({
        json: {
          results: pool.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA),
          pagina,
          paginas: Math.ceil(pool.length / POR_PAGINA),
          nombre_usado: lista.clave === null,
        },
      });
    }
    if (pedido.method() === "POST") {
      const cuerpo = pedido.postDataJSON() as { id_tmdb: number; tipo: "movie" | "tv" };
      const sugerida = SUGERIDAS.find((s) => s.id_tmdb === cuerpo.id_tmdb);
      const nuevo: Item = {
        item_id: 900 + lista.items.length,
        id_tmdb: cuerpo.id_tmdb,
        tipo: cuerpo.tipo,
        titulo: sugerida?.titulo ?? "",
      };
      lista.items.unshift(nuevo);
      return route.fulfill({ status: 201, json: comoItem(nuevo) });
    }
    return route.fulfill({
      json: {
        total: lista.items.length,
        next: null,
        previous: null,
        results: lista.items.map(comoItem),
      },
    });
  });
  return estado;
}

const banda = (page: Page) => page.getByRole("region", { name: "Suggested for this list" });
const verMas = (page: Page) =>
  banda(page).getByRole("button", { name: "Show more suggestions" }).filter({ visible: true });

for (const viewport of viewports) {
  test.describe(`Sugerencias de una lista en ${viewport.name}`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      locale: "en-US",
      extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
    });

    test("la banda cierra la lista con las medidas del canvas y pasa axe", async ({ page }) => {
      await backend(page);
      await page.goto("/lists/10");

      await expect(banda(page)).toBeVisible();
      await expect(
        banda(page).getByText(
          "Based on its 3 titles and its name, without what you already watched."
        )
      ).toBeVisible();
      const filas = banda(page).getByRole("listitem");
      await expect(filas).toHaveCount(6);

      // Va después de la grilla de la lista.
      const ultimaTarjeta = await page.getByRole("link", { name: /Title 32/ }).boundingBox();
      const caja = await banda(page).boundingBox();
      expect(caja!.y).toBeGreaterThan(ultimaTarjeta!.y + ultimaTarjeta!.height);

      // Escritorio: tres columnas y todo un 15 % más grande que en celular.
      const poster = await filas.first().getByRole("link").first().boundingBox();
      expect(Math.round(poster!.width)).toBe(viewport.movil ? 64 : 74);
      expect(Math.round(poster!.height)).toBe(viewport.movil ? 96 : 111);
      const agregar = filas.first().getByRole("button", { name: "Add The Odyssey to Sci Fi" });
      expect(Math.round((await agregar.boundingBox())!.height)).toBe(viewport.movil ? 30 : 34);
      // El área táctil llega a 44 px con un pseudo-elemento.
      const tactil = await agregar.evaluate((boton) => {
        const estilo = getComputedStyle(boton, "::after");
        return boton.getBoundingClientRect().height - 2 * Number.parseFloat(estilo.top);
      });
      expect(Math.round(tactil)).toBe(44);
      const posiciones = await filas.evaluateAll((nodos) =>
        nodos.map((nodo) => Math.round(nodo.getBoundingClientRect().left))
      );
      expect(new Set(posiciones).size).toBe(viewport.movil ? 1 : 3);

      // «Show more» va arriba a la derecha en escritorio y debajo en celular.
      const boton = await verMas(page).boundingBox();
      const primera = await filas.first().boundingBox();
      const ultima = await filas.last().boundingBox();
      if (viewport.movil) expect(boton!.y).toBeGreaterThan(ultima!.y + ultima!.height - 1);
      else expect(boton!.y + boton!.height).toBeLessThanOrEqual(primera!.y);

      // Sin desborde horizontal.
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
      ).toBe(true);
      await auditar(page);
    });

    test("«Show more suggestions» agrega debajo y se oculta en la última página", async ({
      page,
    }) => {
      const estado = await backend(page);
      await page.goto("/lists/10");
      const filas = banda(page).getByRole("listitem");
      await expect(filas).toHaveCount(6);

      await verMas(page).click();
      await expect(filas).toHaveCount(12);
      await expect(filas.first()).toContainText("The Odyssey");
      await expect(filas.nth(6)).toContainText("Annihilation");
      await expect(verMas(page)).toBeVisible();

      await verMas(page).click();
      await expect(filas).toHaveCount(15);
      await expect(verMas(page)).toHaveCount(0);
      // El botón se fue: el foco queda en lo primero que se agregó.
      await expect(banda(page).getByRole("link", { name: "Coherence", exact: true })).toBeFocused();
      expect(estado.pedidos.filter((p) => p.includes("suggestions"))).toEqual([
        "GET 10/suggestions/?pagina=1",
        "GET 10/suggestions/?pagina=2",
        "GET 10/suggestions/?pagina=3",
      ]);
    });

    test("«+ Add» con teclado pasa el título de la banda a la lista", async ({ page }) => {
      const estado = await backend(page);
      await page.goto("/lists/10");
      await expect(banda(page).getByRole("listitem")).toHaveCount(6);

      await banda(page).getByRole("link", { name: "The Odyssey", exact: true }).focus();
      await page.keyboard.press("Tab");
      await expect(
        banda(page).getByRole("button", { name: "Add The Odyssey to Sci Fi" })
      ).toBeFocused();
      await page.keyboard.press("Enter");

      await expect(page.getByText("You added The Odyssey to “Sci Fi”.")).toBeVisible();
      await expect(banda(page).getByRole("listitem")).toHaveCount(5);
      await expect(banda(page).getByRole("link", { name: "The Odyssey", exact: true })).toHaveCount(
        0
      );
      await expect(
        page.getByRole("button", { name: "Remove The Odyssey from Sci Fi" })
      ).toBeAttached();
      await expect(page.getByText("4 items · 4 movies · 0 TV shows")).toBeVisible();
      await expect(
        banda(page).getByText(
          "Based on its 4 titles and its name, without what you already watched."
        )
      ).toBeVisible();
      // El foco sigue en la banda, en el «+ Add» que quedó primero.
      await expect(
        banda(page).getByRole("button", { name: "Add Blade Runner 2049 to Sci Fi" })
      ).toBeFocused();
      expect(estado.pedidos).toContain("POST 10/items/");
    });

    test("está en Favorites y en Watched, y no en Watchlist", async ({ page }) => {
      const estado = await backend(page);

      await page.goto("/lists/1");
      await expect(banda(page)).toBeVisible();
      await expect(
        banda(page).getByText("Based on its 2 titles, without what you already watched.")
      ).toBeVisible();

      await page.goto("/lists/3");
      await expect(banda(page)).toBeVisible();
      await expect(
        banda(page).getByRole("button", { name: "Add The Odyssey to Watched" })
      ).toBeVisible();

      await page.goto("/lists/2");
      await expect(page.getByRole("link", { name: /Title 10/ })).toBeVisible();
      await expect(banda(page)).toHaveCount(0);
      expect(estado.pedidos.filter((p) => p.includes("2/suggestions"))).toEqual([]);
    });
  });
}
