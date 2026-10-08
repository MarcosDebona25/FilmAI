import type { CodedError } from "./errors";

export class ReviewValidationError extends Error implements CodedError {
  constructor(
    public code: string,
    public params = {}
  ) {
    super(code);
  }
}

export type MiResena = {
  id: number;
  id_tmdb: number;
  tipo: "movie" | "tv";
  titulo: string;
  campos_en_ingles?: string[];
  poster: string;
  valor: number;
  fecha: string;
  texto: string | null;
};
export type PaginaResenas = { total: number; next: string | null; results: MiResena[] };

export function rutaPagina(next: string) {
  // Solo reutilizamos el cursor: nunca enviamos cookies a un origen recibido de la API.
  const url = new URL(next, "http://filmai.local");
  return `/api/reviews/mias/${url.search}`;
}
export function combinarResenas(actuales: MiResena[], nuevas: MiResena[]) {
  const items = new Map(actuales.map((item) => [item.id, item]));
  for (const item of nuevas) if (!items.has(item.id)) items.set(item.id, item);
  return [...items.values()];
}
export function cambiosResena(item: MiResena, valor: number, texto: string) {
  const body: { valor?: number; texto?: string } = {};
  if (!Number.isInteger(valor) || valor < 1 || valor > 10)
    throw new ReviewValidationError("invalid");
  if (texto.length > 1000) throw new ReviewValidationError("max_length", { maxLength: 1000 });
  const limpio = texto.trim();
  if (item.texto && !limpio) throw new ReviewValidationError("review_update_empty");
  if (valor !== item.valor) body.valor = valor;
  if (limpio && limpio !== (item.texto ?? "")) body.texto = limpio;
  return body;
}

export function posterUrl(poster: string) {
  if (!poster) return null;
  if (poster.startsWith("/") && !poster.startsWith("//"))
    return `https://image.tmdb.org/t/p/w185${poster}`;
  try {
    const url = new URL(poster);
    return url.protocol === "https:" && url.hostname === "image.tmdb.org" ? url.href : null;
  } catch {
    return null;
  }
}
