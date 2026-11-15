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
      /** Nota de TMDB, o `null` si todavía no tiene votos. */
      nota: number | null;
    };

export type SugerenciaPersona = Extract<Sugerencia, { tipo: "person" }>;
export type SugerenciaTitulo = Exclude<Sugerencia, SugerenciaPersona>;

/** Una fila de la lista: una sugerencia o el «Ver todos los resultados» del final. */
export type Fila = { id: string; sugerencia: Sugerencia | null };

/** Id estable de una opción (`sug-person-525`): es el que apunta `aria-activedescendant`. */
export const idDe = (sugerencia: Sugerencia) => `sug-${sugerencia.tipo}-${sugerencia.id}`;
export const ID_VER_TODO = "sug-all";

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
    nota: titulo.nota,
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

/**
 * Las iniciales del círculo de una persona sin foto: la primera letra del
 * nombre y la del apellido («CN»), o una sola si el nombre es una palabra.
 */
export function inicialesDe(nombre: string) {
  const palabras = nombre.trim().split(/\s+/).filter(Boolean);
  const letras = palabras.length > 1 ? [palabras[0], palabras.at(-1)!] : palabras;
  // `Array.from` corta por carácter y no por unidad UTF-16 (un emoji no se parte).
  return letras.map((palabra) => Array.from(palabra)[0]).join("");
}

/** Separa la lista en los dos grupos que se pintan; el orden de cada grupo es el recibido. */
export function agruparSugerencias(sugerencias: Sugerencia[]) {
  return {
    personas: sugerencias.filter((s): s is SugerenciaPersona => s.tipo === "person"),
    titulos: sugerencias.filter((s): s is SugerenciaTitulo => s.tipo !== "person"),
  };
}

/** Las filas en el orden en que se recorren con el teclado: personas, títulos y, si se pide, «Ver todo». */
export function filasDeSugerencias(sugerencias: Sugerencia[], conVerTodo: boolean): Fila[] {
  const { personas, titulos } = agruparSugerencias(sugerencias);
  const filas: Fila[] = [...personas, ...titulos].map((sugerencia) => ({
    id: idDe(sugerencia),
    sugerencia,
  }));
  return conVerTodo ? [...filas, { id: ID_VER_TODO, sugerencia: null }] : filas;
}

/**
 * La opción activa después de apretar ↓ (`paso` 1) o ↑ (-1). Pasada la última
 * (o antes de la primera) se vuelve al campo: `null`, ninguna activa.
 */
export function moverActiva(filas: Fila[], activoId: string | null, paso: 1 | -1) {
  const actual = filas.findIndex((fila) => fila.id === activoId);
  let siguiente = actual + paso;
  if (actual === -1 && paso === -1) siguiente = filas.length - 1;
  return siguiente < 0 || siguiente >= filas.length ? null : filas[siguiente].id;
}

/** Minúsculas y sin acentos: «Penélope» y «penelope» son lo mismo para comparar. */
function sinAcentos(texto: string) {
  return texto
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/**
 * La primera persona de la lista cuyo nombre contiene todas las palabras del
 * texto (sin acentos ni mayúsculas), o `undefined`. Es lo que decide el aviso
 * «¿Buscabas a…?» de Buscar. En Java sería un `stream().filter(...).findFirst()`.
 */
export function personaQueCoincide(sugerencias: Sugerencia[], texto: string) {
  const palabras = sinAcentos(texto).split(/\s+/).filter(Boolean);
  if (palabras.length === 0) return undefined;
  return sugerencias.find(
    (s): s is SugerenciaPersona =>
      s.tipo === "person" && palabras.every((palabra) => sinAcentos(s.nombre).includes(palabra))
  );
}
