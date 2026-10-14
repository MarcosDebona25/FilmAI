/**
 * Estado de Buscar (C-06): vive en la URL para que recargar, compartir y
 * volver atrás conserven la búsqueda. Acá se traduce entre la URL (`/search?…`,
 * nombres en inglés como el `?type=` del Home) y la API (`browse/`).
 */

import type { ContentType } from "@/components/features/TypeSelector";
import { routes } from "@/lib/routes";

/** Nota en la URL: `9`…`5` es «N o más»; `lt5`, «Menos de 5». */
export type Nota = "9" | "8" | "7" | "6" | "5" | "lt5";

/** «A estrenar» (14/10/2026): lo que estrena después de hoy, en vez de años futuros. */
export const A_ESTRENAR = "proximos";

/** Década antes de 1990, como `1980s` (14/10/2026). */
export type Decada = `${number}s`;

export interface Busqueda {
  q: string;
  tipo: ContentType;
  genero: number | null;
  anio: number | typeof A_ESTRENAR | Decada | null;
  nota: Nota | null;
  pagina: number;
}

/** Mismo tope que valida el backend (`BrowseView.MAX_TEXTO`). */
export const MAX_TEXTO = 50;
export const NOTAS: Nota[] = ["9", "8", "7", "6", "5", "lt5"];
const TIPOS: ContentType[] = ["all", "movie", "tv"];
const PRIMER_ANIO = 1900;
/** Desde acá los años van sueltos; antes, por década (14/10/2026). */
const PRIMER_ANIO_SUELTO = 1990;
/** Valor de «A estrenar» en la URL y en el selector de año. */
const OPCION_A_ESTRENAR = "upcoming";

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
    anio: anioDesdeOpcion(params.get("year") ?? ""),
    nota: NOTAS.includes(nota) ? nota : null,
    pagina: entero(params.get("page")) ?? 1,
  };
}

export function urlDeBusqueda(busqueda: Busqueda) {
  const params = new URLSearchParams();
  if (busqueda.q) params.set("q", busqueda.q);
  if (busqueda.tipo !== "all") params.set("type", busqueda.tipo);
  if (busqueda.genero !== null) params.set("genre", String(busqueda.genero));
  if (busqueda.anio !== null) params.set("year", opcionDeAnio(busqueda.anio));
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
  if (busqueda.anio === A_ESTRENAR) params.set("a_estrenar", "true");
  else if (typeof busqueda.anio === "string") params.set("decada", busqueda.anio.slice(0, 4));
  else if (busqueda.anio !== null) params.set("anio", String(busqueda.anio));
  if (busqueda.nota !== null)
    params.set("nota", busqueda.nota === "lt5" ? "m5" : `${busqueda.nota}+`);
  params.set("page", String(busqueda.pagina));
  return `/api/catalogo/browse/?${params}`;
}

/** Género, año y nota: lo que cuenta el badge de «Filters» en celular. */
export function filtrosActivos(busqueda: Busqueda) {
  return [busqueda.genero, busqueda.anio, busqueda.nota].filter((valor) => valor !== null).length;
}

/**
 * Opciones del selector de año (después de «Cualquiera» y «A estrenar»): años
 * sueltos del actual a 1990 y, antes, décadas hasta la de 1900. `decada` lleva
 * el año inicial para la etiqueta («Década de 1980»).
 */
export function opcionesDeAnio(actual: number) {
  const anios = Array.from({ length: actual - PRIMER_ANIO_SUELTO + 1 }, (_, i) => ({
    valor: String(actual - i),
    decada: null as number | null,
  }));
  const decadas = Array.from(
    { length: (PRIMER_ANIO_SUELTO - PRIMER_ANIO) / 10 },
    (_, i) => PRIMER_ANIO_SUELTO - 10 * (i + 1)
  ).map((decada) => ({ valor: `${decada}s`, decada: decada as number | null }));
  return [...anios, ...decadas];
}

/** Valor de un `<option>` del selector de año (o de `?year=`) → estado. */
export function anioDesdeOpcion(valor: string): Busqueda["anio"] {
  if (valor === OPCION_A_ESTRENAR) return A_ESTRENAR;
  const decada = /^(\d{4})s$/.exec(valor);
  if (decada) {
    const inicio = Number(decada[1]);
    const valida = inicio % 10 === 0 && inicio >= PRIMER_ANIO && inicio < PRIMER_ANIO_SUELTO;
    return valida ? (valor as Decada) : null;
  }
  return entero(valor);
}

/** Estado → valor del selector de año (y de `?year=`). */
export function opcionDeAnio(anio: Busqueda["anio"]) {
  if (anio === A_ESTRENAR) return OPCION_A_ESTRENAR;
  return anio === null ? "" : String(anio);
}

/** Clave de `common.filters.*` con el nombre largo de cada nota. */
export const ETIQUETA_NOTA = {
  "9": "ratingAtLeastNine",
  "8": "ratingAtLeastEight",
  "7": "ratingAtLeastSeven",
  "6": "ratingAtLeastSix",
  "5": "ratingAtLeastFive",
  lt5: "ratingBelowFive",
} as const;

const CLAVE_ULTIMA = "filmai:ultima-busqueda";

/**
 * La miga «Search» de la ficha vuelve a la última búsqueda de esta pestaña
 * (doc 04 §5b). `sessionStorage` puede no estar (modo privado, datos
 * bloqueados): sin él, la miga lleva a `/search` sin parámetros.
 */
export function guardarUltimaBusqueda(url: string) {
  try {
    window.sessionStorage.setItem(CLAVE_ULTIMA, url);
  } catch {
    // Sin almacenamiento no hay vuelta a la búsqueda; no es un error.
  }
}

export function ultimaBusqueda() {
  try {
    const url = window.sessionStorage.getItem(CLAVE_ULTIMA);
    // Solo rutas de Buscar: lo guardado no puede llevar a otro lado.
    return url?.startsWith(`${routes.search}?`) || url === routes.search ? url : routes.search;
  } catch {
    return routes.search;
  }
}

const CLAVE_SCROLL = "filmai:scroll-busqueda";

/**
 * Posición de la grilla al abrir una ficha, para devolverla al volver. La URL
 * cambia con `history.replaceState`, por fuera del router de Next, así que
 * Next no restaura ese scroll solo.
 */
export function guardarScrollBusqueda(url: string, y: number) {
  try {
    window.sessionStorage.setItem(CLAVE_SCROLL, JSON.stringify({ url, y }));
  } catch {
    // Sin almacenamiento se vuelve arriba de todo; no es un error.
  }
}

/** El scroll guardado si es de esta misma búsqueda (misma URL). */
export function scrollGuardado(url: string): number | null {
  try {
    const guardado = JSON.parse(window.sessionStorage.getItem(CLAVE_SCROLL) ?? "null");
    return guardado?.url === url && typeof guardado.y === "number" ? guardado.y : null;
  } catch {
    return null;
  }
}
