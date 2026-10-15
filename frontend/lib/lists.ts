/**
 * Listas (L-02 y L-03, canvas «Lists» y «List detail»). Acá viven los tipos de
 * la API, los filtros del detalle (en la URL, como Buscar y «Calificaciones y
 * reseñas») y el orden de las personalizadas.
 */

import { tmdbImage, type Title } from "@/lib/catalog";
import { NOTAS, de, type Nota } from "@/lib/search";
import { routes } from "@/lib/routes";

export type ClaveLista = "favoritos" | "vistas" | "pendientes";

/** Un resumen de `GET /api/lists/` (L-01). */
export interface ResumenLista {
  id: number;
  nombre: string;
  clave: ClaveLista | null;
  tipo: "predeterminada" | "personalizada";
  cantidad_items: number;
  cantidad_peliculas: number;
  cantidad_series: number;
  /** Rutas de póster de TMDB, las más recientes primero. */
  preview_posters: string[];
}

/** Un ítem de `GET /api/lists/{id}/items/`. */
export interface ItemLista {
  item_id: number;
  fecha_agregado: string;
  id_tmdb: number;
  tipo: "movie" | "tv";
  titulo: string;
  poster: string | null;
  anio: number | null;
  /** Nota de TMDB; `null` si nadie votó. */
  calificacion_promedio: number | null;
}

export interface PaginaItems {
  next: string | null;
  total: number;
  results: ItemLista[];
}

/** Mismo tope que valida el backend (`NombreListaSerializer`). */
export const MAX_NOMBRE = 80;
/** Letras, números y espacios (de cualquier idioma), como el backend. */
const NOMBRE_VALIDO = /^[\p{L}\p{N} ]+$/u;

/** El error de un nombre antes de enviarlo; el resto (duplicado, reservado) lo dice el backend. */
export function errorDeNombre(nombre: string): "required" | "invalid" | null {
  const limpio = nombre.trim();
  if (!limpio) return "required";
  return NOMBRE_VALIDO.test(limpio) ? null : "invalid";
}

export const esPredeterminada = (lista: Pick<ResumenLista, "tipo">) =>
  lista.tipo === "predeterminada";

/** Las predeterminadas van fijas arriba; el orden entre las personalizadas es el de la API. */
export function personalizadas(listas: ResumenLista[]) {
  return listas.filter((lista) => !esPredeterminada(lista));
}

/** `ids` de las personalizadas con la de `desde` movida a la posición `hacia`. */
export function reordenar(listas: ResumenLista[], desde: number, hacia: number) {
  const ids = personalizadas(listas).map((lista) => lista.id);
  if (desde < 0 || desde >= ids.length || hacia < 0 || hacia >= ids.length) return ids;
  const [movida] = ids.splice(desde, 1);
  ids.splice(hacia, 0, movida);
  return ids;
}

/** Las listas con las personalizadas en el orden de `ids`; las predeterminadas quedan primero. */
export function aplicarOrden(listas: ResumenLista[], ids: number[]) {
  const porId = new Map(listas.map((lista) => [lista.id, lista]));
  const ordenadas = ids.flatMap((id) => porId.get(id) ?? []);
  return [...listas.filter(esPredeterminada), ...ordenadas];
}

/** La ficha de un ítem, con lo que `MediaCard` necesita. */
export function itemATitulo(item: ItemLista): Title {
  return {
    tipo: item.tipo,
    id: item.id_tmdb,
    titulo: item.titulo,
    sinopsis: "",
    anio: item.anio,
    nota: item.calificacion_promedio,
    poster: tmdbImage(item.poster, "w342"),
    backdrop: null,
    generoIds: [],
    tituloEnIngles: false,
    sinopsisEnIngles: false,
  };
}

/** Combina páginas por cursor sin repetir ítems. */
export function combinarItems(actuales: ItemLista[], nuevos: ItemLista[]) {
  const items = new Map(actuales.map((item) => [item.item_id, item]));
  for (const item of nuevos) if (!items.has(item.item_id)) items.set(item.item_id, item);
  return [...items.values()];
}

/** Solo reutilizamos el cursor: nunca enviamos cookies a un origen recibido de la API. */
export function rutaPaginaItems(listaId: number, next: string) {
  const url = new URL(next, "http://filmai.local");
  return `/api/lists/${listaId}/items/${url.search}`;
}

// --- Filtros del detalle ---------------------------------------------------

export type OrdenLista = "recent" | "first" | "title" | "highest" | "lowest";
export type Clase = "movie" | "tv";

export const ORDENES_LISTA: OrdenLista[] = ["recent", "first", "title", "highest", "lowest"];
export const CLASES: Clase[] = ["movie", "tv"];

const ORDEN_API: Record<OrdenLista, string> = {
  recent: "agregado-desc",
  first: "agregado-asc",
  title: "titulo-asc",
  highest: "nota-desc",
  lowest: "nota-asc",
};

/** Clave del texto de cada orden. */
export const ETIQUETA_ORDEN_LISTA = {
  recent: "lists.detail.sortRecentlyAdded",
  first: "lists.detail.sortFirstAdded",
  title: "lists.detail.sortTitleAscending",
  highest: "common.sort.highestRating",
  lowest: "common.sort.lowestRating",
} as const satisfies Record<OrdenLista, string>;

export const ETIQUETA_CLASE = { movie: "movies", tv: "tvShows" } as const;

export interface FiltrosLista {
  q: string;
  clase: Clase | null;
  nota: Nota | null;
  orden: OrdenLista;
}

/** Mismo tope que valida el backend (`ListaItemsQuerySerializer`). */
export const MAX_TEXTO = 100;

export const FILTROS_VACIOS: FiltrosLista = { q: "", clase: null, nota: null, orden: "recent" };

export function filtrosDesdeUrl(params: URLSearchParams): FiltrosLista {
  return {
    q: (params.get("q") ?? "").slice(0, MAX_TEXTO),
    clase: de(CLASES, params.get("type")),
    nota: de(NOTAS, params.get("rating")),
    orden: de(ORDENES_LISTA, params.get("sort")) ?? "recent",
  };
}

export function urlDeFiltros(listaId: number, filtros: FiltrosLista) {
  const params = new URLSearchParams();
  if (filtros.q) params.set("q", filtros.q);
  if (filtros.clase) params.set("type", filtros.clase);
  if (filtros.nota) params.set("rating", filtros.nota);
  if (filtros.orden !== "recent") params.set("sort", filtros.orden);
  const consulta = params.toString();
  const ruta = routes.list(listaId);
  return consulta ? `${ruta}?${consulta}` : ruta;
}

/** La consulta a `GET /api/lists/{id}/items/`; la nota de la UI es la de la API (`m5` es «menos de 5»). */
export function consultaItems(listaId: number, filtros: FiltrosLista) {
  const params = new URLSearchParams();
  const q = filtros.q.trim();
  if (q) params.set("q", q);
  if (filtros.clase) params.set("clase", filtros.clase);
  if (filtros.nota) params.set("nota", filtros.nota === "lt5" ? "m5" : `${filtros.nota}+`);
  if (filtros.orden !== "recent") params.set("orden", ORDEN_API[filtros.orden]);
  const consulta = params.toString();
  const ruta = `/api/lists/${listaId}/items/`;
  return consulta ? `${ruta}?${consulta}` : ruta;
}

/** Tipo y nota: lo que cuenta el badge de «Filtros» en celular. */
export function filtrosActivos(filtros: FiltrosLista) {
  return [filtros.clase, filtros.nota].filter((valor) => valor !== null).length;
}

/** ¿Hay algo que «Limpiar filtros» pueda sacar? El orden no cuenta. */
export function hayFiltros(filtros: FiltrosLista) {
  return filtrosActivos(filtros) > 0 || filtros.q.trim() !== "";
}
