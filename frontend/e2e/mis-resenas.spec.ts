import { expect, test, type Page } from "@playwright/test";
import { prepararCuenta } from "./cuenta";

type Item = {
  id: number;
  id_tmdb: number;
  tipo: "movie" | "tv";
  titulo: string;
  poster: string;
  valor: number;
  fecha: string;
  texto: string | null;
};

const INICIALES: Item[] = [
  {
    id: 1,
    id_tmdb: 157336,
    tipo: "movie",
    titulo: "Interstellar",
    poster: "/interstellar.jpg",
    valor: 9,
    fecha: "2026-10-03",
    texto: "Una reseña extensa sobre el viaje y el regreso. ".repeat(12),
  },
  {
    id: 2,
    id_tmdb: 1433,
    tipo: "tv",
    titulo: "American Dad!",
    poster: "",
    valor: 7,
    fecha: "2026-09-28",
    texto: null,
  },
  {
    id: 3,
    id_tmdb: 1015,
    tipo: "movie",
    titulo: "Alpha",
    poster: "",
    valor: 4,
    fecha: "2026-09-20",
    texto: "Linda de ver, guion flojo.",
  },
];

/**
 * Backend de `reviews/` en memoria: filtra y ordena como `reviews/mias/`, y
 * pagina de a `porPagina` con un cursor que es el índice siguiente.
 */
async function resenas(page: Page, { porPagina = 20, iniciales = INICIALES } = {}) {
  await prepararCuenta(page);
  let items = structuredClone(iniciales);
  let fallas = 0;
  let fallasCursor = 0;
  const lecturas: URLSearchParams[] = [];
  await page.route("https://image.tmdb.org/**", (route) => route.fulfill({ status: 404 }));
  await page.route("**/api/reviews/**", async (route) => {
    const pedido = route.request();
    const url = new URL(pedido.url());
    const conCursor = url.searchParams.has("cursor");
    if (fallas > 0 || (conCursor && fallasCursor > 0)) {
      if (conCursor && fallasCursor > 0) fallasCursor--;
      else fallas--;
      await route.fulfill({ status: 500, json: { code: "server_error", params: {}, errors: [] } });
      return;
    }
    const id = Number(/\/reviews\/(\d+)\//.exec(url.pathname)?.[1]);
    if (pedido.method() === "GET") {
      const p = url.searchParams;
      lecturas.push(p);
      const q = (p.get("q") ?? "").toLowerCase();
      const orden = p.get("orden") ?? "fecha-desc";
      const lista = items
        .filter((item) => !q || item.titulo.toLowerCase().includes(q))
        .filter((item) => !p.get("texto") || (p.get("texto") === "con") === Boolean(item.texto))
        .filter((item) => !p.get("clase") || item.tipo === p.get("clase"))
        .filter((item) => item.valor >= Number(p.get("nota_min") ?? 1))
        .filter((item) => item.valor <= Number(p.get("nota_max") ?? 10))
        .sort((a, b) =>
          orden === "nota-desc"
            ? b.valor - a.valor
            : orden === "nota-asc"
              ? a.valor - b.valor
              : orden === "fecha-asc"
                ? a.fecha.localeCompare(b.fecha)
                : b.fecha.localeCompare(a.fecha)
        );
      const desde = Number(p.get("cursor") ?? 0);
      const siguiente = desde + porPagina < lista.length ? desde + porPagina : null;
      const next = new URL(url);
      next.searchParams.set("cursor", String(siguiente));
      await route.fulfill({
        json: {
          total: lista.length,
          total_propias: items.length,
          next: siguiente === null ? null : `http://backend:8000${next.pathname}${next.search}`,
          previous: null,
          results: lista.slice(desde, desde + porPagina),
        },
      });
    } else if (pedido.method() === "PUT") {
      items = items.map((item) => (item.id === id ? { ...item, ...pedido.postDataJSON() } : item));
      await route.fulfill({ json: items.find((item) => item.id === id) });
    } else if (url.pathname.endsWith("/texto/")) {
      items = items.map((item) => (item.id === id ? { ...item, texto: null } : item));
      await route.fulfill({ status: 204 });
    } else {
      items = items.filter((item) => item.id !== id);
      await route.fulfill({ status: 204 });
    }
  });
  return {
    fallar: (veces = 1) => {
      fallas = veces;
    },
    /** La próxima página pedida con cursor falla. */
    fallarSiguiente: () => {
      fallasCursor = 1;
    },
    items: () => items,
    ultimaLectura: () => lecturas.at(-1),
  };
}

const sinDesborde = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

test.describe("escritorio", () => {
  test.use({ viewport: { width: 1440, height: 1000 } });

  test("filtra desde la URL y los selectores, y limpia conservando el orden", async ({ page }) => {
    const estado = await resenas(page);
    await page.goto("/my-reviews?sort=lowest");
    const filas = page.getByRole("main").getByRole("article");
    await expect(filas.getByRole("heading")).toHaveText(["Alpha", "American Dad!", "Interstellar"]);
    await expect(page.getByRole("link", { name: "Interstellar" })).toHaveAttribute(
      "href",
      "/movie/157336?from=reviews"
    );

    await page.getByRole("combobox", { name: /^Tipo/ }).selectOption("movie");
    await expect(page).toHaveURL(/\/my-reviews\?type=movie&sort=lowest$/);
    await expect(filas.getByRole("heading")).toHaveText(["Alpha", "Interstellar"]);
    await page.getByRole("combobox", { name: /^Calificación/ }).selectOption("lt5");
    await expect(filas.getByRole("heading")).toHaveText(["Alpha"]);
    expect(estado.ultimaLectura()?.get("nota_max")).toBe("4");

    await page.getByRole("searchbox", { name: "Buscar por título" }).fill("zzz");
    await expect(page.getByText("Ninguna calificación coincide con estos filtros.")).toBeVisible();
    await page.getByRole("button", { name: "Limpiar filtros" }).first().click();
    await expect(page).toHaveURL(/\/my-reviews\?sort=lowest$/);
    await expect(filas).toHaveCount(3);
    await expect(page.getByRole("searchbox", { name: "Buscar por título" })).toHaveValue("");
  });

  test("editar, borrar la reseña y quitar la calificación con los diálogos de la ficha", async ({
    page,
  }) => {
    const estado = await resenas(page);
    await page.goto("/my-reviews");
    await page.getByRole("button", { name: "Leer más" }).click();
    await expect(page.getByRole("button", { name: "Leer menos" })).toHaveAttribute(
      "aria-expanded",
      "true"
    );

    await page.getByRole("button", { name: "Editar", exact: true }).first().click();
    const editar = page.getByRole("dialog", { name: "Editar calificación" });
    await expect(editar.getByRole("radio", { name: "9 de 10" })).toBeChecked();
    await editar.getByRole("radio", { name: "10 de 10" }).click();
    await editar.getByLabel(/Reseña/).fill("Corta y nueva.");
    await editar.getByRole("button", { name: "Actualizar" }).click();
    await expect(editar).toBeHidden();
    await expect(page.getByLabel("Tu calificación: 10 de 10")).toBeVisible();
    await expect(page.getByText("Corta y nueva.")).toBeVisible();
    expect(estado.items()[0]).toMatchObject({ valor: 10, texto: "Corta y nueva." });

    const mas = page.getByRole("button", { name: "Más acciones para Interstellar" });
    await mas.click();
    await expect(page.getByRole("menuitem").first()).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await expect(page.getByRole("menuitem", { name: "Quitar calificación" })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(mas).toBeFocused();
    await mas.click();
    await page.getByRole("menuitem", { name: "Eliminar reseña" }).click();
    await page
      .getByRole("alertdialog", { name: "¿Eliminar reseña?" })
      .getByRole("button", { name: "Eliminar reseña" })
      .click();
    await expect(
      page.getByRole("link", { name: "Agregar una reseña a Interstellar" })
    ).toBeVisible();
    await expect(mas).toBeFocused();

    for (const titulo of ["Interstellar", "American Dad!", "Alpha"]) {
      await page.getByRole("button", { name: `Más acciones para ${titulo}` }).click();
      await page.getByRole("menuitem", { name: "Quitar calificación" }).click();
      await page
        .getByRole("alertdialog", { name: "¿Quitar tu calificación?" })
        .getByRole("button", { name: "Quitar calificación" })
        .click();
      await expect(page.getByRole("link", { name: titulo })).toHaveCount(0);
    }
    await expect(page.getByText("Todavía no calificaste ninguna película ni serie.")).toBeVisible();
    await expect(page.getByRole("link", { name: "Buscar qué calificar" })).toHaveAttribute(
      "href",
      "/search"
    );
  });

  test("un fallo al borrar deja el diálogo abierto con el error", async ({ page }) => {
    const estado = await resenas(page);
    await page.goto("/my-reviews");
    await page.getByRole("button", { name: "Más acciones para Alpha" }).click();
    await page.getByRole("menuitem", { name: "Quitar calificación" }).click();
    estado.fallar();
    const confirmar = page.getByRole("alertdialog", { name: "¿Quitar tu calificación?" });
    await confirmar.getByRole("button", { name: "Quitar calificación" }).click();
    await expect(confirmar.getByRole("alert")).toBeVisible();
    expect(estado.items()).toHaveLength(3);
    await confirmar.getByRole("button", { name: "Quitar calificación" }).click();
    await expect(confirmar).toBeHidden();
    expect(estado.items()).toHaveLength(2);
  });

  test("pagina por cursor con los filtros y se recupera de un error", async ({ page }) => {
    const estado = await resenas(page, { porPagina: 1 });
    estado.fallarSiguiente();
    await page.goto("/my-reviews?type=movie");
    const filas = page.getByRole("main").getByRole("article");
    // La segunda página se pide sola al llegar al final, y falla.
    await expect(page.getByRole("main").getByRole("alert")).toContainText("No pudimos cargar");
    await expect(filas).toHaveCount(1);
    await page.getByRole("button", { name: "Reintentar" }).click();
    await expect(filas.getByRole("heading")).toHaveText(["Interstellar", "Alpha"]);
    // El cursor conserva los filtros.
    expect(estado.ultimaLectura()?.get("clase")).toBe("movie");
    await expect(page.getByRole("button", { name: "Cargar más calificaciones" })).toHaveCount(0);
  });

  test("si la primera carga falla, ofrece reintentar", async ({ page }) => {
    const estado = await resenas(page);
    estado.fallar();
    await page.goto("/my-reviews");
    await expect(page.getByRole("main").getByRole("alert")).toContainText("No pudimos cargar");
    await page.getByRole("button", { name: "Reintentar" }).click();
    await expect(page.getByRole("main").getByRole("article")).toHaveCount(3);
  });
});

test.describe("celular", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("filtros en una hoja con chips y acciones en otra, sin desborde", async ({ page }) => {
    await resenas(page);
    await page.goto("/my-reviews");
    await expect(page.getByRole("link", { name: "Perfil" }).first()).toBeVisible();
    await expect(page.getByRole("main").getByRole("article")).toHaveCount(3);
    expect(await sinDesborde(page)).toBe(true);

    await page.getByRole("button", { name: "Filtros y orden" }).click();
    const hoja = page.getByRole("dialog", { name: "Filtros y orden" });
    await hoja.getByRole("button", { name: "Con reseña" }).click();
    await hoja.getByRole("radio", { name: "Mayor calificación" }).click();
    await hoja.getByRole("button", { name: "Ver 2 resultados" }).click();
    await expect(hoja).toBeHidden();
    await expect(page).toHaveURL(/review=with&sort=highest/);
    await expect(page.getByRole("button", { name: "Filtros y orden, 1 activo" })).toBeVisible();
    await expect(page.getByText("Orden: Mayor calificación")).toBeVisible();
    await page.getByRole("button", { name: "Quitar filtro Con reseña" }).click();
    await expect(page.getByRole("main").getByRole("article")).toHaveCount(3);

    await page.getByRole("button", { name: "Acciones para Alpha" }).click();
    const acciones = page.getByRole("dialog", { name: /Alpha/ });
    await acciones.getByRole("button", { name: "Editar calificación y reseña" }).click();
    const editar = page.getByRole("dialog", { name: "Editar calificación" });
    await expect(editar.getByRole("radio", { name: "4 de 10" })).toBeChecked();
    expect(await sinDesborde(page)).toBe(true);
    await page.keyboard.press("Escape");
    await expect(editar).toBeHidden();
    await expect(page.getByRole("button", { name: "Acciones para Alpha" })).toBeFocused();
  });
});
