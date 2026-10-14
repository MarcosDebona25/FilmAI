/**
 * Estado de Buscar (C-06): vive en la URL para que recargar, compartir y
 * volver atrás conserven la búsqueda. Acá se traduce entre la URL (`/search?…`,
 * nombres en inglés como el `?type=` del Home) y la API (`browse/`).
 */

import type { ContentType } from "@/components/features/TypeSelector";
import { routes } from "@/lib/routes";

/** Nota en la URL: `9`…`5` es «N o más»; `lt5`, «Menos de 5». */
export type Nota = "9" | "8" | "7" | "6" | "5" | "lt5";

export interface Busqueda {
  q: string;
  tipo: ContentType;
  genero: number | null;
  anio: number | null;
  nota: Nota | null;
  pagina: number;
}

/** Mismo tope que valida el backend (`BrowseView.MAX_TEXTO`). */
export const MAX_TEXTO = 50;
export const NOTAS: Nota[] = ["9", "8", "7", "6", "5", "lt5"];
const TIPOS: ContentType[] = ["all", "movie", "tv"];
const PRIMER_ANIO = 1900;

export const BUSQUEDA_VACIA: Busqueda = {
  q: "",
  tipo: "all",
  genero: null,
  anio: null,
  nota: null,
  pagina: 1,
};

function entero(valor: string | null) {
  const numero = Number(valor);
  return valor && Number.isInteger(numero) && numero > 0 ? numero : null;
}

export function busquedaDesdeUrl(params: URLSearchParams): Busqueda {
  const tipo = params.get("type") as ContentType;
  const nota = params.get("rating") as Nota;
  return {
    q: (params.get("q") ?? "").slice(0, MAX_TEXTO),
    tipo: TIPOS.includes(tipo) ? tipo : "all",
    genero: entero(params.get("genre")),
    anio: entero(params.get("year")),
    nota: NOTAS.includes(nota) ? nota : null,
    pagina: entero(params.get("page")) ?? 1,
  };
}

export function urlDeBusqueda(busqueda: Busqueda) {
  const params = new URLSearchParams();
  if (busqueda.q) params.set("q", busqueda.q);
  if (busqueda.tipo !== "all") params.set("type", busqueda.tipo);
  if (busqueda.genero !== null) params.set("genre", String(busqueda.genero));
  if (busqueda.anio !== null) params.set("year", String(busqueda.anio));
  if (busqueda.nota !== null) params.set("rating", busqueda.nota);
  if (busqueda.pagina > 1) params.set("page", String(busqueda.pagina));
  const consulta = params.toString();
  return consulta ? `${routes.search}?${consulta}` : routes.search;
}

export function consultaApi(busqueda: Busqueda) {
  const params = new URLSearchParams();
  const q = busqueda.q.trim();
  if (q) params.set("q", q);
  params.set("tipo", busqueda.tipo);
  if (busqueda.genero !== null) params.set("genero", String(busqueda.genero));
  if (busqueda.anio !== null) params.set("anio", String(busqueda.anio));
  if (busqueda.nota !== null)
    params.set("nota", busqueda.nota === "lt5" ? "m5" : `${busqueda.nota}+`);
  params.set("page", String(busqueda.pagina));
  return `/api/catalogo/browse/?${params}`;
}

/** Género, año y nota: lo que cuenta el badge de «Filters» en celular. */
export function filtrosActivos(busqueda: Busqueda) {
  return [busqueda.genero, busqueda.anio, busqueda.nota].filter((valor) => valor !== null).length;
}

/** Opciones del selector de año, del actual a 1900. */
export function aniosDisponibles(actual: number) {
  return Array.from({ length: actual - PRIMER_ANIO + 1 }, (_, i) => actual - i);
}
