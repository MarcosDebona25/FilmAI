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
  /** Un administrador la ocultó: su texto no se puede editar ni borrar (F10). */
  moderada: boolean;
};
export type PaginaResenas = {
  total: number;
  /** Sin filtros (`reviews/mias/` lo manda siempre que no se pide una ficha). */
  total_propias?: number;
  next: string | null;
  results: MiResena[];
};

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
