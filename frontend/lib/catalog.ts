/**
 * Títulos del catálogo (C-05): la forma que usa la app a partir de un item de
 * TMDB, venga de `trending`, `discover`, `now-playing` o `recommended`.
 */

export type MediaType = "movie" | "tv";

/** Lo que el backend reenvía de TMDB, más la marca del respaldo en inglés. */
export interface TmdbItem {
  id: number;
  media_type?: string;
  title?: string;
  name?: string;
  overview?: string;
  poster_path?: string | null;
  backdrop_path?: string | null;
  profile_path?: string | null;
  release_date?: string;
  first_air_date?: string;
  vote_average?: number;
  genre_ids?: number[];
  campos_en_ingles?: string[];
}

export interface Title {
  tipo: MediaType;
  id: number;
  titulo: string;
  sinopsis: string;
  anio: number | null;
  /** Nota de TMDB; `null` si nadie votó (mostrar «★ 0,0» confundiría). */
  nota: number | null;
  poster: string | null;
  backdrop: string | null;
  generoIds: number[];
  tituloEnIngles: boolean;
  sinopsisEnIngles: boolean;
}

/** URL de una imagen de TMDB; solo acepta rutas de TMDB o URLs https de su CDN. */
export function tmdbImage(path: string | null | undefined, size: "w342" | "w1280") {
  if (!path) return null;
  if (path.startsWith("/") && !path.startsWith("//"))
    return `https://image.tmdb.org/t/p/${size}${path}`;
  try {
    const url = new URL(path);
    return url.protocol === "https:" && url.hostname === "image.tmdb.org" ? url.href : null;
  } catch {
    return null;
  }
}

function anio(fecha: string | undefined) {
  const valor = Number.parseInt(fecha?.slice(0, 4) ?? "", 10);
  return Number.isFinite(valor) ? valor : null;
}

/**
 * `discover` y `now-playing` no traen `media_type`: el tipo lo conoce quien
 * pidió. Devuelve `null` para lo que no es película ni serie (personas).
 */
export function normalizeTitle(item: TmdbItem, tipoPorDefecto?: MediaType): Title | null {
  const tipo = item.media_type ?? tipoPorDefecto;
  if (tipo !== "movie" && tipo !== "tv") return null;
  const enIngles = item.campos_en_ingles ?? [];
  return {
    tipo,
    id: item.id,
    titulo: (tipo === "movie" ? item.title : item.name) ?? "",
    sinopsis: item.overview ?? "",
    anio: anio(tipo === "movie" ? item.release_date : item.first_air_date),
    nota: item.vote_average ? item.vote_average : null,
    poster: tmdbImage(item.poster_path, "w342"),
    backdrop: tmdbImage(item.backdrop_path, "w1280"),
    generoIds: item.genre_ids ?? [],
    tituloEnIngles: enIngles.includes(tipo === "movie" ? "title" : "name"),
    sinopsisEnIngles: enIngles.includes("overview"),
  };
}

/** Normaliza una lista y descarta repetidos (mismo tipo e id), que TMDB a veces manda. */
export function normalizeTitles(items: TmdbItem[], tipoPorDefecto?: MediaType): Title[] {
  const vistos = new Set<string>();
  return items.flatMap((item) => {
    const titulo = normalizeTitle(item, tipoPorDefecto);
    if (!titulo || vistos.has(`${titulo.tipo}-${titulo.id}`)) return [];
    vistos.add(`${titulo.tipo}-${titulo.id}`);
    return [titulo];
  });
}
