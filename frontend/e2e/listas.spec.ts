import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import es from "../messages/es/common.json";
import { prepararCuenta } from "./cuenta";

const viewports = [
  { name: "escritorio", width: 1440, height: 900, movil: false },
  { name: "celular", width: 390, height: 844, movil: true },
] as const;

type Lista = {
  id: number;
  nombre: string;
  clave: "favoritos" | "pendientes" | "vistas" | null;
  tipo: "predeterminada" | "personalizada";
  orden: number;
  items: Item[];
};
type Item = {
  item_id: number;
  id_tmdb: number;
  tipo: "movie" | "tv";
  titulo: string;
  anio: number | null;
  nota: number | null;
  agregado: string;
};

function item(n: number, extra: Partial<Item> = {}): Item {
  return {
    item_id: n,
    id_tmdb: 1000 + n,
    tipo: n % 3 === 0 ? "tv" : "movie",
    titulo: `Título ${String(n).padStart(2, "0")}`,
    anio: 2000 + n,
    nota: n % 4 === 0 ? null : 5 + (n % 5),
    agregado: `2026-10-${String(n).padStart(2, "0")}T10:00:00Z`,
    ...extra,
  };
}

function listasIniciales(personalizadas = ["Maratón", "Clásicos", "Terror"]): Lista[] {
  return [
    {
      id: 1,
      nombre: "Favorites",
      clave: "favoritos",
      tipo: "predeterminada",
      orden: 0,
      items: [item(1), item(2)],
    },
    {
      id: 2,
      nombre: "Watchlist",
      clave: "pendientes",
      tipo: "predeterminada",
      orden: 0,
      items: [],
    },
    {
      id: 3,
      nombre: "Watched",
      clave: "vistas",
      tipo: "predeterminada",
      orden: 0,
      items: [item(5), item(6)],
    },
    ...personalizadas.map((nombre, indice): Lista => ({
      id: 10 + indice,
      nombre,
      clave: null,
      tipo: "personalizada",
      orden: indice + 1,
      items: [],
    })),
  ];
}

const resumen = (lista: Lista) => ({
  id: lista.id,
  nombre: lista.nombre,
  clave: lista.clave,
  tipo: lista.tipo,
  cantidad_items: lista.items.length,
  cantidad_peliculas: lista.items.filter((i) => i.tipo === "movie").length,
  cantidad_series: lista.items.filter((i) => i.tipo === "tv").length,
  preview_posters: lista.items.slice(0, 5).map((i) => `/poster-${i.item_id}.jpg`),
});

/** Backend de `lists/` en memoria, con lo justo para las pantallas de Listas. */
async function backend(
  page: Page,
  { listas = listasIniciales(), porPagina = 20, calificados = [] as number[] } = {}
) {
  await prepararCuenta(page, "en");
  const estado = { listas: structuredClone(listas), escrituras: [] as string[] };
  await page.route("https://image.tmdb.org/**", (route) => route.fulfill({ status: 404 }));
  await page.route("**/api/reviews/mias/**", (route) => {
    const id = Number(new URL(route.request().url()).searchParams.get("id_tmdb"));
    return route.fulfill({
      json: calificados.includes(id)
        ? { id: 9, valor: 9, texto: "Una gran reseña", fecha: "2026-10-01" }
        : null,
    });
  });
  await page.route("**/api/lists/**", async (route) => {
    const pedido = route.request();
    const url = new URL(pedido.url());
    const metodo = pedido.method();
    const ruta = url.pathname.replace(/^.*\/api\/lists\//, "");
    const ordenadas = () => [
      ...estado.listas.filter((l) => l.tipo === "predeterminada"),
      ...estado.listas.filter((l) => l.tipo === "personalizada").sort((a, b) => a.orden - b.orden),
    ];
    const json = (cuerpo: unknown, status = 200) => route.fulfill({ status, json: cuerpo });
    const error = (status: number, code: string) =>
      json({ code, params: {}, errors: [{ field: null, code, params: {} }] }, status);
    if (metodo !== "GET") estado.escrituras.push(`${metodo} ${url.pathname}${url.search}`);

    if (ruta === "") {
      if (metodo === "GET") return json(ordenadas().map(resumen));
      const { nombre } = pedido.postDataJSON() as { nombre: string };
      if (estado.listas.some((l) => l.nombre.toLowerCase() === nombre.toLowerCase()))
        return error(409, "list_name_duplicated");
      const nueva: Lista = {
        id: 100 + estado.listas.length,
        nombre,
        clave: null,
        tipo: "personalizada",
        orden: 99 + estado.listas.length,
        items: [],
      };
      estado.listas.push(nueva);
      return json(resumen(nueva), 201);
    }
    if (ruta === "order/") {
      const { ids } = pedido.postDataJSON() as { ids: number[] };
      ids.forEach((id, indice) => {
        const lista = estado.listas.find((l) => l.id === id);
        if (lista) lista.orden = indice + 1;
      });
      return json(ordenadas().map(resumen));
    }
    const coincidencia = /^(\d+)\/(?:items\/(?:(\d+)\/)?)?$/.exec(ruta);
    const lista = estado.listas.find((l) => l.id === Number(coincidencia?.[1]));
    if (!coincidencia || !lista) return error(404, "not_found");
    const itemId = coincidencia[2] ? Number(coincidencia[2]) : null;

    if (ruta.includes("items/") && itemId === null) {
      const p = url.searchParams;
      const q = (p.get("q") ?? "").toLowerCase();
      const orden = p.get("orden") ?? "agregado-desc";
      const filtrados = lista.items
        .filter((i) => !q || i.titulo.toLowerCase().includes(q))
        .filter((i) => !p.get("clase") || i.tipo === p.get("clase"))
        .filter((i) => {
          const nota = p.get("nota");
          if (!nota) return true;
          if (i.nota === null) return false;
          return nota === "m5" ? i.nota < 5 : i.nota >= Number.parseInt(nota);
        })
        .sort((a, b) =>
          orden === "titulo-asc"
            ? a.titulo.localeCompare(b.titulo)
            : orden === "agregado-asc"
              ? a.agregado.localeCompare(b.agregado)
              : b.agregado.localeCompare(a.agregado)
        );
      const desde = Number(p.get("cursor") ?? 0);
      const sigue = desde + porPagina < filtrados.length;
      const next = new URL(url);
      next.searchParams.set("cursor", String(desde + porPagina));
      return json({
        total: filtrados.length,
        next: sigue ? `http://backend:8000${next.pathname}${next.search}` : null,
        previous: null,
        results: filtrados.slice(desde, desde + porPagina).map((i) => ({
          item_id: i.item_id,
          fecha_agregado: i.agregado,
          id_tmdb: i.id_tmdb,
          tipo: i.tipo,
          titulo: i.titulo,
          poster: null,
          anio: i.anio,
          calificacion_promedio: i.nota,
        })),
      });
    }
    if (itemId !== null) {
      const encontrado = lista.items.find((i) => i.item_id === itemId);
      if (!encontrado) return error(404, "not_found");
      if (
        lista.clave === "vistas" &&
        calificados.includes(encontrado.id_tmdb) &&
        url.searchParams.get("borrar_calificacion") !== "true"
      )
        return error(409, "rating_blocks_removal_from_watched");
      lista.items = lista.items.filter((i) => i.item_id !== itemId);
      return route.fulfill({ status: 204 });
    }
    if (metodo === "GET") return json(resumen(lista));
    if (lista.tipo === "predeterminada") return error(409, "default_list_protected");
    if (metodo === "PUT") {
      const { nombre } = pedido.postDataJSON() as { nombre: string };
      if (
        estado.listas.some(
          (l) => l.id !== lista.id && l.nombre.toLowerCase() === nombre.toLowerCase()
        )
      )
        return error(409, "list_name_duplicated");
      lista.nombre = nombre;
      return json(resumen(lista));
    }
    estado.listas = estado.listas.filter((l) => l.id !== lista.id);
    return route.fulfill({ status: 204 });
  });
  return estado;
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

const nombres = (page: Page) =>
  page.locator("main h2").evaluateAll((nodos) => nodos.map((n) => n.textContent));

/** Toque real con CDP: `puntos` son las posiciones sucesivas del dedo. */
async function gestoTactil(
  page: Page,
  puntos: { x: number; y: number }[],
  { esperaInicial = 0, pasoMs = 16 } = {}
) {
  const cdp = await page.context().newCDPSession(page);
  const [inicio, ...resto] = puntos;
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [inicio] });
  if (esperaInicial) await page.waitForTimeout(esperaInicial);
  for (const punto of resto) {
    await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [punto] });
    await page.waitForTimeout(pasoMs);
  }
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
}

/** Un punto de la tarjeta, ya a la vista: un toque fuera de ella no es de la tarjeta. */
async function centro(page: Page, nombre: string, { alinear = false } = {}) {
  const tarjeta = page
    .getByRole("heading", { level: 2, name: nombre })
    .locator("xpath=ancestor::li[1]");
  if (alinear) await tarjeta.evaluate((nodo) => nodo.scrollIntoView({ block: "start" }));
  await tarjeta.scrollIntoViewIfNeeded();
  const caja = await tarjeta.boundingBox();
  if (!caja) throw new Error(`Sin tarjeta para ${nombre}`);
  return { x: caja.x + caja.width / 2, y: caja.y + caja.height - 12 };
}

for (const viewport of viewports) {
  test.describe(`Listas en ${viewport.name}`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      hasTouch: viewport.movil,
      isMobile: viewport.movil,
    });

    test("muestra las predeterminadas fijas, las personalizadas y no desborda", async ({
      page,
    }) => {
      await backend(page);
      await page.goto("/lists");

      await expect(page.getByRole("heading", { level: 1, name: en.nav.main.lists })).toBeVisible();
      await expect(page.getByText("6 lists · 3 defaults")).toBeVisible();
      expect(await nombres(page)).toEqual([
        "Favorites",
        "Watchlist",
        "Watched",
        "Maratón",
        "Clásicos",
        "Terror",
      ]);
      await expect(page.getByText(en.common.lists.defaultBadge, { exact: true })).toHaveCount(3);
      await expect(page.getByRole("button", { name: /^Actions for the list/ })).toHaveCount(3);
      await expect(page.getByText("2 items · 2 movies · 0 TV shows").first()).toBeVisible();
      await sinDesborde(page);
    });

    test("crea, rechaza un duplicado, renombra y elimina", async ({ page }) => {
      const api = await backend(page);
      await page.goto("/lists");

      await page.getByRole("button", { name: en.lists.create.title }).click();
      const dialogo = page.getByRole("dialog", { name: en.lists.create.title });
      await dialogo.getByLabel(en.common.lists.nameLabel).fill("maratón");
      await dialogo.getByRole("button", { name: en.common.actions.create }).click();
      await expect(dialogo.getByRole("alert")).toHaveText(en.errors.codes.list_name_duplicated);

      await dialogo.getByLabel(en.common.lists.nameLabel).fill("Sunday marathon");
      await dialogo.getByRole("button", { name: en.common.actions.create }).click();
      await expect(page.getByText(en.lists.feedback.created)).toBeVisible();
      expect((await nombres(page)).at(-1)).toBe("Sunday marathon");
      await sinDesborde(page);

      await page.getByRole("button", { name: "Actions for the list Clásicos" }).click();
      await page
        .getByRole("menuitem", { name: en.common.lists.rename })
        .or(page.getByRole("button", { name: en.common.lists.rename }))
        .click();
      const renombrar = page.getByRole("dialog", { name: en.common.lists.renameTitle });
      await renombrar.getByLabel(en.common.lists.nameLabel).fill("Cine clásico");
      await renombrar.getByRole("button", { name: en.common.actions.save }).click();
      await expect(page.getByRole("heading", { level: 2, name: "Cine clásico" })).toBeVisible();

      await page.getByRole("button", { name: "Actions for the list Terror" }).click();
      await page
        .getByRole("menuitem", { name: en.common.actions.delete })
        .or(page.getByRole("button", { name: en.common.actions.delete }))
        .click();
      const aviso = page.getByRole("alertdialog", { name: "Delete “Terror”?" });
      await aviso.getByRole("button", { name: en.common.actions.delete }).click();
      await expect(page.getByRole("heading", { level: 2, name: "Terror" })).toHaveCount(0);
      expect(api.escrituras).toEqual([
        "POST /api/lists/",
        "POST /api/lists/",
        "PUT /api/lists/11/",
        "DELETE /api/lists/12/",
      ]);
    });

    test("el menú ⋯ mueve la lista: left/right en escritorio, up/down en celular", async ({
      page,
    }) => {
      const api = await backend(page);
      await page.goto("/lists");

      await page.getByRole("button", { name: "Actions for the list Clásicos" }).click();
      const subir = viewport.movil ? en.common.lists.moveUp : en.common.lists.moveLeft;
      const otro = viewport.movil ? en.common.lists.moveLeft : en.common.lists.moveUp;
      await expect(page.getByText(otro, { exact: true })).toHaveCount(0);
      await page.getByText(subir, { exact: true }).click();

      await expect
        .poll(async () => (await nombres(page)).slice(3))
        .toEqual(["Clásicos", "Maratón", "Terror"]);
      expect(api.escrituras).toEqual(["PUT /api/lists/order/"]);
      await page.reload();
      await expect(page.getByRole("heading", { level: 2, name: "Terror" })).toBeVisible();
      expect((await nombres(page)).slice(3)).toEqual(["Clásicos", "Maratón", "Terror"]);
    });

    test("cambia de idioma sin perder la lista y nombra las predeterminadas por su clave", async ({
      page,
    }) => {
      await backend(page);
      await page.goto("/lists");
      await expect(page.getByRole("heading", { level: 1, name: en.nav.main.lists })).toBeVisible();

      await page
        .context()
        .addCookies([{ name: "filmai_locale", value: "es", url: "http://127.0.0.1:3100" }]);
      await page.reload();

      await expect(page.getByRole("heading", { level: 1, name: es.nav.main.lists })).toBeVisible();
      expect((await nombres(page)).slice(0, 3)).toEqual([
        es.enums.defaultList.favoritos,
        es.enums.defaultList.pendientes,
        es.enums.defaultList.vistas,
      ]);
      await expect(page.getByText("6 listas · 3 predeterminadas")).toBeVisible();
      await sinDesborde(page);
    });
  });
}

test.describe("Listas: arrastrar en escritorio", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("la manija reordena y el resto de la tarjeta sigue siendo un enlace", async ({ page }) => {
    const api = await backend(page);
    await page.goto("/lists");

    const manija = page.getByRole("button", { name: en.common.lists.reorderLabel }).first();
    const origen = await manija.boundingBox();
    const destino = await page
      .getByRole("heading", { level: 2, name: "Terror" })
      .locator("xpath=ancestor::li[1]")
      .boundingBox();
    if (!origen || !destino) throw new Error("Sin cajas");
    await page.mouse.move(origen.x + origen.width / 2, origen.y + origen.height / 2);
    await page.mouse.down();
    await page.mouse.move(destino.x + destino.width / 2, destino.y + destino.height / 2, {
      steps: 12,
    });
    await page.mouse.up();

    await expect
      .poll(async () => (await nombres(page)).slice(3))
      .toEqual(["Clásicos", "Terror", "Maratón"]);
    expect(api.escrituras).toEqual(["PUT /api/lists/order/"]);

    // Arrastrar desde el nombre no reordena: solo la manija.
    const antes = api.escrituras.length;
    const titulo = await page.getByRole("heading", { level: 2, name: "Clásicos" }).boundingBox();
    if (!titulo) throw new Error("Sin título");
    await page.mouse.move(titulo.x + 10, titulo.y + 10);
    await page.mouse.down();
    await page.mouse.move(titulo.x + 10, titulo.y + 260, { steps: 10 });
    await page.mouse.up();
    expect(api.escrituras.length).toBe(antes);
  });

  test("con teclado: Espacio levanta, flechas mueven, Espacio suelta", async ({ page }) => {
    const api = await backend(page);
    await page.goto("/lists");

    const manija = page.getByRole("button", { name: en.common.lists.reorderLabel }).first();
    // El teclado solo levanta la tarjeta cuando la página ya hidrató: se
    // reintenta hasta que la manija queda «presionada».
    await expect(async () => {
      await manija.focus();
      await page.keyboard.press("Space");
      await expect(manija).toHaveAttribute("aria-pressed", "true", { timeout: 1000 });
    }).toPass({ timeout: 15_000 });
    await page.keyboard.press("ArrowRight");
    await page.waitForTimeout(250);
    await page.keyboard.press("Space");

    await expect
      .poll(async () => (await nombres(page)).slice(3))
      .toEqual(["Clásicos", "Maratón", "Terror"]);
    expect(api.escrituras).toEqual(["PUT /api/lists/order/"]);
  });
});

test.describe("Listas: arrastrar en celular", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

  const muchas = listasIniciales([
    "Uno",
    "Dos",
    "Tres",
    "Cuatro",
    "Cinco",
    "Seis",
    "Siete",
    "Ocho",
  ]);

  test("deslizar el dedo sobre una tarjeta hace scroll y no la arrastra", async ({ page }) => {
    const api = await backend(page, { listas: muchas });
    await page.goto("/lists");
    await expect(page.getByRole("heading", { level: 2, name: "Uno" })).toBeVisible();

    const inicio = await centro(page, "Uno", { alinear: true });
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
    const antes = await page.evaluate(() => window.scrollY);
    await gestoTactil(
      page,
      Array.from({ length: 12 }, (_, paso) => ({ x: inicio.x, y: inicio.y - paso * 25 })),
      { pasoMs: 12 }
    );

    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(antes + 50);
    expect(api.escrituras).toEqual([]);
    expect((await nombres(page)).slice(3, 6)).toEqual(["Uno", "Dos", "Tres"]);
    await expect(page).toHaveURL(/\/lists$/);
  });

  test("la pulsación larga levanta la tarjeta y soltarla guarda el orden", async ({ page }) => {
    const api = await backend(page, { listas: muchas });
    await page.goto("/lists");
    await expect(page.getByRole("heading", { level: 2, name: "Uno" })).toBeVisible();

    const desde = await centro(page, "Uno", { alinear: true });
    const hasta = await centro(page, "Tres");
    await gestoTactil(
      page,
      [
        desde,
        ...Array.from({ length: 10 }, (_, paso) => ({
          x: desde.x,
          y: desde.y + ((hasta.y - desde.y) * (paso + 1)) / 10,
        })),
      ],
      { esperaInicial: 450 }
    );

    await expect
      .poll(async () => (await nombres(page)).slice(3, 6))
      .toEqual(["Dos", "Tres", "Uno"]);
    expect(api.escrituras).toEqual(["PUT /api/lists/order/"]);
    await expect(page).toHaveURL(/\/lists$/);
  });

  test("mantener presionado no abre el menú ni la vista previa del sistema", async ({ page }) => {
    await backend(page, { listas: muchas });
    await page.goto("/lists");
    const enlace = page.getByRole("link", { name: "Uno" });
    await expect(enlace).toBeVisible();

    const resultado = await enlace.evaluate((nodo) => {
      const tarjeta = nodo.closest("li") as HTMLElement;
      const evento = new MouseEvent("contextmenu", { bubbles: true, cancelable: true });
      nodo.dispatchEvent(evento);
      return {
        cancelado: evento.defaultPrevented,
        seleccion: getComputedStyle(tarjeta).userSelect,
        arrastrable: nodo.getAttribute("draggable"),
      };
    });
    expect(resultado).toEqual({ cancelado: true, seleccion: "none", arrastrable: "false" });
  });
});

for (const viewport of viewports) {
  test.describe(`Detalle de una lista en ${viewport.name}`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      hasTouch: viewport.movil,
      isMobile: viewport.movil,
    });

    const conItems = (n: number, extra: Partial<Lista> = {}) => {
      const listas = listasIniciales();
      listas[3].items = Array.from({ length: n }, (_, i) => item(i + 1));
      return listas.map((lista) => (lista.id === listas[3].id ? { ...lista, ...extra } : lista));
    };

    test("muestra la grilla, pagina al bajar y vuelve desde la ficha", async ({ page }) => {
      await backend(page, { listas: conItems(30), porPagina: 12 });
      await page.goto("/lists/10");

      await expect(page.getByRole("heading", { level: 1, name: "Maratón" })).toBeVisible();
      await expect(page.getByText(/^30 items · /)).toBeVisible();
      await expect(page.getByRole("link", { name: /Título 30/ })).toBeVisible();
      await page.getByRole("button", { name: en.lists.detail.loadMore }).scrollIntoViewIfNeeded();
      await expect(page.getByRole("link", { name: /Título 18/ })).toBeVisible();
      await sinDesborde(page);
      await expect(page.getByRole("link", { name: /Título 29/ })).toHaveAttribute(
        "href",
        "/movie/1029?from=list-10"
      );
    });

    test("filtra por tipo, nota y título, y los filtros viven en la URL", async ({ page }) => {
      await backend(page, { listas: conItems(12) });
      await page.goto("/lists/10");
      await expect(page.getByRole("link", { name: /Título 12/ })).toBeVisible();

      await page.getByRole("searchbox", { name: "Search in Maratón" }).fill("título 0");
      await expect(page).toHaveURL(/q=t%C3%ADtulo\+0|q=t%C3%ADtulo%200/);
      await expect(page.getByRole("link", { name: /Título 12/ })).toHaveCount(0);
      await expect(page.getByRole("link", { name: /Título 09/ })).toBeVisible();

      if (viewport.movil) {
        await page.getByRole("button", { name: /Filters and sort/ }).click();
        const hoja = page.getByRole("dialog", { name: en.lists.detail.filtersTitle });
        await hoja.getByRole("button", { name: en.common.content.tvShows }).click();
        await hoja.getByRole("radio", { name: en.lists.detail.sortTitleAscending }).click();
        await hoja.getByRole("button", { name: /^Show \d+ results?$/ }).click();
      } else {
        await page.getByLabel(en.common.content.typeShortLabel).selectOption("tv");
        await page
          .locator("label")
          .filter({ hasText: /^Sort/ })
          .locator("select")
          .selectOption("title");
      }
      await expect(page).toHaveURL(/type=tv/);
      await expect(page).toHaveURL(/sort=title/);
      await expect(page.getByRole("link", { name: /Título 09/ })).toBeVisible();
      await expect(page.getByRole("link", { name: /Título 03/ })).toBeVisible();
      await expect(page.getByRole("link", { name: /Título 06/ })).toBeVisible();
      await expect(page.getByText(/^Showing 3 of 12 items$/)).toBeVisible();

      await page.reload();
      await expect(page.getByRole("link", { name: /Título 09/ })).toBeVisible();
      await expect(page.getByRole("link", { name: /Título 01/ })).toHaveCount(0);

      await page.getByRole("searchbox").fill("zzz");
      await expect(page.getByText(en.lists.detail.filteredEmpty)).toBeVisible();
      await page.getByRole("button", { name: en.common.filters.clear }).last().click();
      // «Clear filters» deja el orden elegido.
      await expect(page).toHaveURL(/\/lists\/10(\?sort=title)?$/);
      await expect(page.getByRole("link", { name: /Título 12/ })).toBeVisible();
      await sinDesborde(page);
    });

    test("quita un ítem con confirmación", async ({ page }) => {
      const api = await backend(page, { listas: conItems(3) });
      await page.goto("/lists/10");

      await page.getByRole("button", { name: "Remove Título 02 from Maratón" }).click();
      await page
        .getByRole("alertdialog", { name: "Remove “Título 02” from Maratón?" })
        .getByRole("button", { name: en.common.actions.remove })
        .click();

      await expect(page.getByText(en.lists.feedback.itemRemoved)).toBeVisible();
      await expect(page.getByRole("link", { name: /Título 02/ })).toHaveCount(0);
      await expect(page.getByText(/^2 items · /)).toBeVisible();
      expect(api.escrituras).toEqual(["DELETE /api/lists/10/items/2/"]);
    });

    test("quitar de Watched un título calificado pide confirmar y borra la calificación", async ({
      page,
    }) => {
      const api = await backend(page, { calificados: [1005] });
      await page.goto("/lists/3");
      await expect(page.getByRole("heading", { level: 1, name: "Watched" })).toBeVisible();
      await expect(page.getByRole("button", { name: /^Actions for/ })).toHaveCount(0);

      await page.getByRole("button", { name: "Remove Título 05 from Watched" }).click();
      await page
        .getByRole("alertdialog")
        .getByRole("button", { name: en.common.actions.remove })
        .click();

      const confirmar = page.getByRole("alertdialog", {
        name: en.title.watched.removeConfirmTitle,
      });
      await expect(confirmar).toBeVisible();
      await expect(confirmar.getByText("Una gran reseña")).toBeVisible();
      await expect(page.getByRole("link", { name: /Título 05/ })).toBeVisible();
      await confirmar.getByRole("button", { name: en.title.watched.remove }).click();

      await expect(page.getByText(en.title.feedback.ratingReviewDeleted)).toBeVisible();
      await expect(page.getByRole("link", { name: /Título 05/ })).toHaveCount(0);
      expect(api.escrituras).toEqual([
        "DELETE /api/lists/3/items/5/",
        "DELETE /api/lists/3/items/5/?borrar_calificacion=true",
      ]);
    });

    test("una lista vacía invita a explorar y puede renombrarse o eliminarse", async ({ page }) => {
      const api = await backend(page);
      await page.goto("/lists/11");

      await expect(page.getByText(en.lists.detail.emptyTitle)).toBeVisible();
      await expect(page.getByRole("link", { name: en.common.actions.explore })).toHaveAttribute(
        "href",
        "/search"
      );
      await page.getByRole("button", { name: "Actions for Clásicos" }).click();
      await page
        .getByRole("menuitem", { name: en.common.lists.delete })
        .or(page.getByRole("button", { name: en.common.lists.delete }))
        .click();
      await page
        .getByRole("alertdialog")
        .getByRole("button", { name: en.common.actions.delete })
        .click();

      await expect(page).toHaveURL(/\/lists$/);
      expect(api.escrituras).toEqual(["DELETE /api/lists/11/"]);
    });

    test("una lista que no existe muestra el 404 (Not Found)", async ({ page }) => {
      await backend(page);
      await page.goto("/lists/999");

      await expect(page.getByText("404").first()).toBeVisible();
    });
  });
}
