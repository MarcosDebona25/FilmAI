/**
 * Filtros de «Calificaciones y reseñas» (perfil según el canvas). Viven en la
 * URL, como los de Buscar, así recargar y volver desde la ficha conservan la
 * lista filtrada. Acá se traduce entre la URL (`/my-reviews?…`, nombres en
 * inglés como `?type=` y `?rating=` de Buscar) y la API (`reviews/mias/`).
 */

import { crearUltimaVista } from "@/lib/last-view";
import { ORDENES, ORDEN_API, parametrosNota, type Orden } from "@/lib/review-filters";
import { NOTAS, de, type Nota } from "@/lib/search";
import { routes } from "@/lib/routes";

export type Presencia = "with" | "without";
export type Clase = "movie" | "tv";

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

export const FILTROS_VACIOS: FiltrosResenas = {
  q: "",
  resena: null,
  clase: null,
  nota: null,
  orden: "newest",
};

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
  if (filtros.nota)
    for (const [clave, valor] of Object.entries(parametrosNota(filtros.nota)))
      params.set(clave, valor);
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

/** La miga «Calificaciones y reseñas» de la ficha vuelve a esta lista con sus filtros. */
export const { guardar: guardarUltimasResenas, leer: ultimasResenas } = crearUltimaVista(
  "filmai:ultimas-resenas",
  routes.myReviews
);
