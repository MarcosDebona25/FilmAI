import type { Page } from "@playwright/test";

import {
  fall2,
  generosPeliculas,
  generosSeries,
  insidious,
  reacher,
  svu,
} from "../tests/catalog-fixtures";
import { CREDITOS_INTERSTELLAR, INTERSTELLAR, PLATAFORMAS_AR } from "../tests/title-fixtures";
import { prepararCuenta } from "./cuenta";

/**
 * API simulada para recorrer las pantallas principales sin backend: catálogo
 * (Home, Buscar, ficha), listas y la sesión. La usan los specs de maquetación,
 * que miran tamaños y no el comportamiento de cada flujo.
 */

/** 20 títulos distintos, como una página real de TMDB. */
function pagina(base = fall2, desde = 1) {
  return Array.from({ length: 20 }, (_, i) => ({
    ...base,
    media_type: "movie",
    id: base.id + desde + i,
  }));
}

const sinTipo = (item: object) => ({ ...item, media_type: undefined });

export async function sinSesion(page: Page) {
  await page.route("**/api/profile/", (route) =>
    route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
  );
}

export async function conSesion(page: Page) {
  await prepararCuenta(page, "en");
}

export async function simularCatalogo(page: Page) {
  const filas = [insidious, reacher, ...pagina().slice(2)];
  await page.route("**/api/catalogo/**", (route) => {
    const url = new URL(route.request().url());
    const partes = url.pathname.split("/").filter(Boolean);
    const recurso = partes[2];
    if (recurso === "trending") {
      const tipo = url.searchParams.get("media_type");
      return route.fulfill({
        json: { results: tipo === "tv" ? [svu, reacher, ...filas.slice(2)] : filas },
      });
    }
    if (recurso === "now-playing") return route.fulfill({ json: { results: filas.map(sinTipo) } });
    if (recurso === "discover") return route.fulfill({ json: { results: filas.map(sinTipo) } });
    if (recurso === "recommended")
      return route.fulfill({
        json: { generos: ["Thriller", "Drama", "Crime"], results: filas },
      });
    if (recurso === "genres")
      return route.fulfill({
        json: {
          genres: url.searchParams.get("tipo") === "tv" ? generosSeries : generosPeliculas,
        },
      });
    if (recurso === "browse") {
      const pag = Number(url.searchParams.get("page") ?? 1);
      return route.fulfill({
        json: {
          page: pag,
          // Una sola página: el scroll infinito no cambia el alto entre corridas.
          total_pages: 1,
          total_results: 20,
          results: pagina(fall2, pag * 100),
        },
      });
    }
    if (url.pathname.endsWith("/credits/")) return route.fulfill({ json: CREDITOS_INTERSTELLAR });
    if (url.pathname.endsWith("/providers/"))
      return route.fulfill({ json: { ...PLATAFORMAS_AR, pais: "AR" } });
    return route.fulfill({ json: INTERSTELLAR });
  });
  await page.route("**/api/reviews/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/reviews/mias/")
      return route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
    return route.fulfill({
      json: { total: 0, total_comunidad: 0, next: null, previous: null, results: [] },
    });
  });
  // Las imágenes de TMDB salen de un archivo local: no depende de internet.
  await page.route("https://image.tmdb.org/**", (route) =>
    route.fulfill({ path: "public/collage-posters/Opcion 1.jpg" })
  );
}

const LISTAS = [
  { id: 1, nombre: "Favorites", clave: "favoritos", tipo: "predeterminada", items: 24 },
  { id: 2, nombre: "Watchlist", clave: "pendientes", tipo: "predeterminada", items: 0 },
  { id: 3, nombre: "Watched", clave: "vistas", tipo: "predeterminada", items: 3 },
  { id: 10, nombre: "Marathon", clave: null, tipo: "personalizada", items: 5 },
];

/** `lists/` de solo lectura: cuatro listas y la primera con 24 títulos. */
export async function simularListas(page: Page) {
  await page.route("**/api/lists/**", (route) => {
    const url = new URL(route.request().url());
    const ruta = url.pathname.replace(/^.*\/api\/lists\//, "");
    const resumen = (l: (typeof LISTAS)[number]) => ({
      id: l.id,
      nombre: l.nombre,
      clave: l.clave,
      tipo: l.tipo,
      cantidad_items: l.items,
      cantidad_peliculas: l.items,
      cantidad_series: 0,
      preview_posters: [],
    });
    if (ruta === "") return route.fulfill({ json: LISTAS.map(resumen) });
    const [id, items] = ruta.split("/");
    const lista = LISTAS.find((l) => l.id === Number(id));
    if (!lista)
      return route.fulfill({ status: 404, json: { code: "not_found", params: {}, errors: [] } });
    if (!items) return route.fulfill({ json: resumen(lista) });
    return route.fulfill({
      json: {
        total: lista.items,
        next: null,
        previous: null,
        results: Array.from({ length: lista.items }, (_, i) => ({
          item_id: i + 1,
          fecha_agregado: `2026-10-${String(i + 1).padStart(2, "0")}T10:00:00Z`,
          id_tmdb: 1000 + i,
          tipo: "movie",
          titulo: `Title ${String(i + 1).padStart(2, "0")}`,
          poster: null,
          anio: 2000 + i,
          calificacion_promedio: 7,
          disponible: true,
        })),
      },
    });
  });
}
