/**
 * Filtros de «Calificaciones y reseñas» (perfil según el canvas). Viven en la
 * URL, como los de Buscar, así recargar y volver desde la ficha conservan la
 * lista filtrada. Acá se traduce entre la URL (`/my-reviews?…`, nombres en
 * inglés como `?type=` y `?rating=` de Buscar) y la API (`reviews/mias/`).
 */

import { NOTAS, type Nota } from "@/lib/search";
import { routes } from "@/lib/routes";

export type Presencia = "with" | "without";
export type Clase = "movie" | "tv";
export type Orden = "newest" | "oldest" | "highest" | "lowest";

export interface FiltrosResenas {
  q: string;
  /** Con o sin texto de reseña; `null` es «Todas». */
  resena: Presencia | null;
  clase: Clase | null;
  nota: Nota | null;
  orden: Orden;
}

/** Mismo tope que valida el backend (`MisResenasQuerySerializer`). */
export const MAX_TEXTO = 100;
export const PRESENCIAS: Presencia[] = ["with", "without"];
export const CLASES: Clase[] = ["movie", "tv"];
export const ORDENES: Orden[] = ["newest", "oldest", "highest", "lowest"];

export const FILTROS_VACIOS: FiltrosResenas = {
  q: "",
  resena: null,
  clase: null,
  nota: null,
  orden: "newest",
};

const ORDEN_API: Record<Orden, string> = {
  newest: "fecha-desc",
  oldest: "fecha-asc",
  highest: "nota-desc",
  lowest: "nota-asc",
};

function de<T extends string>(valores: readonly T[], valor: string | null): T | null {
  return valores.includes(valor as T) ? (valor as T) : null;
}

export function filtrosDesdeUrl(params: URLSearchParams): FiltrosResenas {
  return {
    q: (params.get("q") ?? "").slice(0, MAX_TEXTO),
    resena: de(PRESENCIAS, params.get("review")),
    clase: de(CLASES, params.get("type")),
    nota: de(NOTAS, params.get("rating")),
    orden: de(ORDENES, params.get("sort")) ?? "newest",
  };
}

export function urlDeFiltros(filtros: FiltrosResenas) {
  const params = new URLSearchParams();
  if (filtros.q) params.set("q", filtros.q);
  if (filtros.resena) params.set("review", filtros.resena);
  if (filtros.clase) params.set("type", filtros.clase);
  if (filtros.nota) params.set("rating", filtros.nota);
  if (filtros.orden !== "newest") params.set("sort", filtros.orden);
  const consulta = params.toString();
  return consulta ? `${routes.myReviews}?${consulta}` : routes.myReviews;
}

export function consultaApi(filtros: FiltrosResenas) {
  const params = new URLSearchParams();
  const q = filtros.q.trim();
  if (q) params.set("q", q);
  if (filtros.resena) params.set("texto", filtros.resena === "with" ? "con" : "sin");
  if (filtros.clase) params.set("clase", filtros.clase);
  // «N o más» es una nota mínima; «Menos de 5», una máxima de 4 (las notas son enteras).
  if (filtros.nota === "lt5") params.set("nota_max", "4");
  else if (filtros.nota) params.set("nota_min", filtros.nota);
  if (filtros.orden !== "newest") params.set("orden", ORDEN_API[filtros.orden]);
  const consulta = params.toString();
  return consulta ? `/api/reviews/mias/?${consulta}` : "/api/reviews/mias/";
}

/** Reseña, tipo y nota: lo que cuenta el badge de «Filtros y orden» en celular. */
export function filtrosActivos(filtros: FiltrosResenas) {
  return [filtros.resena, filtros.clase, filtros.nota].filter((valor) => valor !== null).length;
}

/** ¿Hay algo que «Limpiar filtros» pueda sacar? El orden no cuenta. */
export function hayFiltros(filtros: FiltrosResenas) {
  return filtrosActivos(filtros) > 0 || filtros.q.trim() !== "";
}

const CLAVE_ULTIMA = "filmai:ultimas-resenas";

/**
 * La miga «Calificaciones y reseñas» de la ficha vuelve a esta lista con sus
 * filtros. Sin `sessionStorage` (modo privado, datos bloqueados) lleva a la
 * lista sin filtros.
 */
export function guardarUltimasResenas(url: string) {
  try {
    window.sessionStorage.setItem(CLAVE_ULTIMA, url);
  } catch {
    // Sin almacenamiento no hay vuelta a los filtros; no es un error.
  }
}

export function ultimasResenas() {
  try {
    const url = window.sessionStorage.getItem(CLAVE_ULTIMA);
    // Solo rutas de esta pantalla: lo guardado no puede llevar a otro lado.
    return url?.startsWith(`${routes.myReviews}?`) || url === routes.myReviews
      ? url
      : routes.myReviews;
  } catch {
    return routes.myReviews;
  }
}
