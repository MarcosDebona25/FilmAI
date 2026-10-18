/** La ficha de una película o serie (C-07): datos, origen y edición de la nota. */
import { tmdbImage, type MediaType } from "@/lib/catalog";

/** Lo que el backend reenvía de `movie/{id}` o `tv/{id}` de TMDB. */
export interface TmdbDetalle {
  id: number;
  title?: string;
  name?: string;
  tagline?: string;
  overview?: string;
  poster_path?: string | null;
  backdrop_path?: string | null;
  release_date?: string;
  first_air_date?: string;
  runtime?: number | null;
  number_of_seasons?: number | null;
  number_of_episodes?: number | null;
  vote_average?: number;
  vote_count?: number;
  genres?: { id: number; name: string }[];
  campos_en_ingles?: string[];
}

export interface Ficha {
  tipo: MediaType;
  id: number;
  titulo: string;
  lema: string;
  sinopsis: string;
  anio: number | null;
  /** Minutos, solo películas. */
  duracion: number | null;
  temporadas: number | null;
  episodios: number | null;
  nota: number | null;
  votos: number;
  generos: string[];
  poster: string | null;
  backdrop: string | null;
  tituloEnIngles: boolean;
  sinopsisEnIngles: boolean;
}

export interface Creditos {
  directores: string[];
  reparto: { nombre: string; personaje: string }[];
}

export interface Plataforma {
  id: number;
  nombre: string;
  /** Ruta de TMDB (`/abc.jpg`); se sirve con `tmdbImage(logo, "w92")`. */
  logo: string | null;
}

/** `GET /api/catalogo/{tipo}/{id}/providers/?pais=AR`: dónde verla en un país. */
export interface Plataformas {
  pais: string;
  /** Página de TMDB con los enlaces reales (JustWatch); `null` si el país no tiene datos. */
  enlace: string | null;
  suscripcion: Plataforma[];
  gratis: Plataforma[];
  alquiler: Plataforma[];
  compra: Plataforma[];
}

/** La calificación propia (`GET /api/reviews/mias/?id_tmdb=&tipo=`, C-08). */
export interface MiCalificacion {
  id: number;
  valor: number;
  texto: string | null;
  fecha: string;
}

export function normalizarFicha(raw: TmdbDetalle, tipo: MediaType): Ficha {
  const enIngles = raw.campos_en_ingles ?? [];
  const fecha = tipo === "movie" ? raw.release_date : raw.first_air_date;
  const anio = Number.parseInt(fecha?.slice(0, 4) ?? "", 10);
  return {
    tipo,
    id: raw.id,
    titulo: (tipo === "movie" ? raw.title : raw.name) ?? "",
    lema: raw.tagline ?? "",
    sinopsis: raw.overview ?? "",
    anio: Number.isFinite(anio) ? anio : null,
    duracion: tipo === "movie" && raw.runtime ? raw.runtime : null,
    temporadas: tipo === "tv" ? (raw.number_of_seasons ?? null) : null,
    episodios: tipo === "tv" ? (raw.number_of_episodes ?? null) : null,
    nota: raw.vote_average ? raw.vote_average : null,
    votos: raw.vote_count ?? 0,
    generos: (raw.genres ?? []).map((genero) => genero.name),
    poster: tmdbImage(raw.poster_path, "w500"),
    backdrop: tmdbImage(raw.backdrop_path, "w1280"),
    tituloEnIngles: enIngles.includes(tipo === "movie" ? "title" : "name"),
    sinopsisEnIngles: enIngles.includes("overview"),
  };
}

export type Origen =
  { tipo: "home" } | { tipo: "search" } | { tipo: "reviews" } | { tipo: "lista"; id: number };

/** `?from=` de la URL; un valor desconocido o ausente es Home (link directo). */
export function origenDesde(from: string | null): Origen {
  if (from === "search") return { tipo: "search" };
  if (from === "reviews") return { tipo: "reviews" };
  const lista = /^list-(\d+)$/.exec(from ?? "");
  if (lista) return { tipo: "lista", id: Number(lista[1]) };
  return { tipo: "home" };
}

/**
 * Qué pedir al editar. La API no acepta un texto vacío (`PUT` con `texto: ""`):
 * vaciar una reseña que existía se hace con `DELETE …/texto/`, aparte.
 */
export function planEdicion(
  previo: { valor: number; texto: string | null },
  valor: number,
  texto: string
) {
  const limpio = texto.trim();
  const cambios: { valor?: number; texto?: string } = {};
  if (valor !== previo.valor) cambios.valor = valor;
  if (limpio && limpio !== (previo.texto ?? "")) cambios.texto = limpio;
  return { borrarTexto: !limpio && Boolean(previo.texto), cambios };
}
