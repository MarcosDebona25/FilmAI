/**
 * Sugerencias de la lupa de la navbar: pide `GET /api/catalogo/suggest/` y
 * deja la respuesta lista para pintar. El diseño está en
 * `openspec/changes/busqueda-navbar/design.md` (§1 y §2).
 */

import { apiFetch } from "@/lib/api";
import { normalizeTitle, tmdbImage, type MediaType, type TmdbItem } from "@/lib/catalog";
import type { RolPersona } from "@/lib/search";

/** Desde cuántos caracteres (sin espacios de los bordes) se piden sugerencias. */
export const MIN_CARACTERES = 2;
/** Espera después de la última tecla. Buscar espera 350 ms porque su pedido es una búsqueda completa. */
export const ESPERA_SUGERENCIAS_MS = 250;

/** `gender` de TMDB (1 mujer, 2 varón) como lo usa el catálogo de textos. */
export type GeneroPersona = "female" | "male" | "other";

export type Sugerencia =
  | {
      tipo: "person";
      id: number;
      nombre: string;
      rol: RolPersona;
      genero: GeneroPersona;
      /** Foto ya con la URL de TMDB, o `null`. */
      foto: string | null;
    }
  | {
      tipo: MediaType;
      id: number;
      titulo: string;
      anio: number | null;
      poster: string | null;
    };

/** Lo que manda `suggest/`: títulos con los nombres de campo de TMDB y personas con `rol`. */
interface ItemSugerido extends TmdbItem {
  rol?: RolPersona;
  gender?: number | null;
}

export function generoDe(gender: number | null | undefined): GeneroPersona {
  return gender === 1 ? "female" : gender === 2 ? "male" : "other";
}

/** Un item de la API → sugerencia; `null` si no es película, serie ni persona con rol. */
function aSugerencia(item: ItemSugerido): Sugerencia | null {
  if (item.media_type === "person") {
    if (item.rol !== "director" && item.rol !== "actor") return null;
    return {
      tipo: "person",
      id: item.id,
      nombre: item.name ?? "",
      rol: item.rol,
      genero: generoDe(item.gender),
      foto: tmdbImage(item.profile_path, "w92"),
    };
  }
  const titulo = normalizeTitle(item);
  if (!titulo) return null;
  return {
    tipo: titulo.tipo,
    id: titulo.id,
    titulo: titulo.titulo,
    anio: titulo.anio,
    poster: tmdbImage(item.poster_path, "w92"),
  };
}

/**
 * Respuestas ya recibidas en esta visita, por idioma y texto: volver a un
 * texto (borrando una letra, por ejemplo) muestra su lista al instante. La
 * clave lleva el idioma porque la API traduce los títulos según `Accept-Language`.
 */
const cache = new Map<string, Sugerencia[]>();
const clave = (idioma: string, texto: string) => `${idioma}|${texto}`;

export function limpiarCacheSugerencias() {
  cache.clear();
}

/** La lista que ya se conoce para ese texto, sin pedir nada. */
export function sugerenciasEnCache(idioma: string, texto: string) {
  return cache.get(clave(idioma, texto));
}

/** Pide las sugerencias de `texto` (ya recortado). `signal` cancela el pedido. */
export async function pedirSugerencias(texto: string, idioma: string, signal?: AbortSignal) {
  const { results } = await apiFetch<{ results: ItemSugerido[] }>(
    `/api/catalogo/suggest/?q=${encodeURIComponent(texto)}`,
    { signal }
  );
  const lista = results.flatMap((item) => aSugerencia(item) ?? []);
  cache.set(clave(idioma, texto), lista);
  return lista;
}

/**
 * ¿La tecla es el atajo «/» de la búsqueda? No lo es si se escribe en un campo
 * (ahí es una barra más), con un modificador, o con un diálogo abierto.
 */
export function esAtajoDeBusqueda(evento: KeyboardEvent) {
  if (evento.key !== "/" || evento.ctrlKey || evento.metaKey || evento.altKey) return false;
  if (document.querySelector("dialog[open]")) return false;
  const destino = evento.target;
  if (!(destino instanceof HTMLElement)) return true;
  return !destino.closest(
    "input, textarea, select, [contenteditable]:not([contenteditable=false])"
  );
}
