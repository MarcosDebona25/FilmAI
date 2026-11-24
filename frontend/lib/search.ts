/**
 * Estado de Buscar (C-06): vive en la URL para que recargar, compartir y
 * volver atrás conserven la búsqueda. Acá se traduce entre la URL (`/search?…`,
 * nombres en inglés como el `?type=` del Home) y la API (`explore/`).
 */

import type { ContentType } from "@/components/features/TypeSelector";
import { crearUltimaVista } from "@/lib/last-view";
import { routes } from "@/lib/routes";

/** Nota en la URL: `9`…`5` es «N o más»; `lt5`, «Menos de 5». */
export type Nota = "9" | "8" | "7" | "6" | "5" | "lt5";

/** «A estrenar» (14/10/2026): lo que estrena después de hoy, en vez de años futuros. */
export const A_ESTRENAR = "proximos";

/** Década antes de 1990, como `1980s` (14/10/2026). */
export type Decada = `${number}s`;

/** Rol de una persona en la filmografía que se filtra (`role=` en la URL, `rol` en la API). */
export type RolPersona = "director" | "actor";
const ROLES: RolPersona[] = ["director", "actor"];

/** Orden de los resultados (24/11/2026); `popular` es el de siempre y no viaja en la URL. */
export type Orden = "popular" | "newest" | "oldest" | "highest" | "lowest" | "most-voted";
export const ORDENES: Orden[] = ["popular", "newest", "oldest", "highest", "lowest", "most-voted"];
/** Valor de `orden=` en la API de `explore/` para cada orden. */
const ORDEN_API: Record<Orden, string> = {
  popular: "popular",
  newest: "fecha-desc",
  oldest: "fecha-asc",
  highest: "nota-desc",
  lowest: "nota-asc",
  "most-voted": "votos-desc",
};
/** Clave de `common.sort.*` con el nombre de cada orden. */
export const ETIQUETA_ORDEN = {
  popular: "popular",
  newest: "newest",
  oldest: "oldest",
  highest: "highestRating",
  lowest: "lowestRating",
  "most-voted": "mostVoted",
} as const;

export interface Busqueda {
  q: string;
  tipo: ContentType;
  genero: number | null;
  anio: number | typeof A_ESTRENAR | Decada | null;
  nota: Nota | null;
  /** Id de TMDB de la persona cuya filmografía se muestra (`person=`), o `null`. */
  persona: number | null;
  /** Qué hizo esa persona; `null` es cualquier cosa. Sin `persona` siempre es `null`. */
  rol: RolPersona | null;
  orden: Orden;
  pagina: number;
}

/** Mismo tope que valida el backend (`ExploreView.MAX_TEXTO`). */
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
  persona: null,
  rol: null,
  orden: "popular",
  pagina: 1,
};

/** `valor` si es una de las opciones; si no, `null`. */
export function de<T extends string>(valores: readonly T[], valor: string | null): T | null {
  return valores.includes(valor as T) ? (valor as T) : null;
}

function entero(valor: string | null) {
  const numero = Number(valor);
  return valor && Number.isInteger(numero) && numero > 0 ? numero : null;
}

export function busquedaDesdeUrl(params: URLSearchParams): Busqueda {
  const persona = entero(params.get("person"));
  return {
    q: (params.get("q") ?? "").slice(0, MAX_TEXTO),
    tipo: de(TIPOS, params.get("type")) ?? "all",
    genero: entero(params.get("genre")),
    anio: anioDesdeOpcion(params.get("year") ?? ""),
    nota: de(NOTAS, params.get("rating")),
    persona,
    // El rol solo tiene sentido con persona: un `role=` suelto se ignora.
    rol: persona === null ? null : de(ROLES, params.get("role")),
    orden: de(ORDENES, params.get("sort")) ?? "popular",
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
  if (busqueda.persona !== null) {
    params.set("person", String(busqueda.persona));
    if (busqueda.rol !== null) params.set("role", busqueda.rol);
  }
  if (busqueda.orden !== "popular") params.set("sort", busqueda.orden);
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
  if (busqueda.persona !== null) {
    params.set("persona", String(busqueda.persona));
    if (busqueda.rol !== null) params.set("rol", busqueda.rol);
  }
  if (busqueda.orden !== "popular") params.set("orden", ORDEN_API[busqueda.orden]);
  params.set("page", String(busqueda.pagina));
  return `/api/catalogo/explore/?${params}`;
}

/** Género, año, nota y persona: lo que cuenta el badge de «Filters» en celular (el orden no cuenta). */
export function filtrosActivos(busqueda: Busqueda) {
  return [busqueda.genero, busqueda.anio, busqueda.nota, busqueda.persona].filter(
    (valor) => valor !== null
  ).length;
}

/** Destino de la navbar al elegir una persona: su filmografía, sin filtros previos. */
export function urlDePersona(persona: number, rol: RolPersona) {
  return urlDeBusqueda({ ...BUSQUEDA_VACIA, persona, rol });
}

/** Destino de «Ver todos los resultados»: una búsqueda nueva con ese texto. */
export function urlDeTexto(q: string) {
  return urlDeBusqueda({ ...BUSQUEDA_VACIA, q: q.slice(0, MAX_TEXTO) });
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

/** Lo que usa `etiquetaNota` del `t` de `useTranslations()`. */
type TraductorNota = {
  (
    clave:
      | "common.filters.anyRating"
      | `common.filters.${(typeof ETIQUETA_NOTA)[Nota]}`
      | "search.filters.ratingShortBelowFive"
  ): string;
  (clave: "search.filters.ratingShort", valores: { value: string }): string;
};

/**
 * Nombre de una nota (`null` es «Cualquiera»). El corto («9+») es el de los
 * botones de las hojas de filtros, que llevan el largo como `aria-label`.
 */
export function etiquetaNota(t: TraductorNota, nota: Nota | null, corta = false) {
  if (nota === null) return t("common.filters.anyRating");
  if (!corta) return t(`common.filters.${ETIQUETA_NOTA[nota]}`);
  return nota === "lt5"
    ? t("search.filters.ratingShortBelowFive")
    : t("search.filters.ratingShort", { value: nota });
}

/** La miga «Search» de la ficha vuelve a la última búsqueda de esta pestaña (doc 04 §5b). */
export const { guardar: guardarUltimaBusqueda, leer: ultimaBusqueda } = crearUltimaVista(
  "filmai:ultima-busqueda",
  routes.search
);

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
