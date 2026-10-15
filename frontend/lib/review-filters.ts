/**
 * Orden y nota de las dos listas de reseñas: la comunidad de la ficha (C-07) y
 * «Calificaciones y reseñas». La API es la misma (`orden`, `nota_min`,
 * `nota_max`) y las opciones también.
 */

import type { Nota } from "@/lib/search";

export type Orden = "newest" | "oldest" | "highest" | "lowest";
export const ORDENES: Orden[] = ["newest", "oldest", "highest", "lowest"];

export const ORDEN_API: Record<Orden, string> = {
  newest: "fecha-desc",
  oldest: "fecha-asc",
  highest: "nota-desc",
  lowest: "nota-asc",
};

export const ETIQUETA_ORDEN = {
  newest: "common.sort.newest",
  oldest: "common.sort.oldest",
  highest: "common.sort.highestRating",
  lowest: "common.sort.lowestRating",
} as const satisfies Record<Orden, string>;

/** «N o más» es una nota mínima; «Menos de 5», una máxima de 4 (las notas son enteras). */
export function parametrosNota(nota: Nota): Record<string, string> {
  return nota === "lt5" ? { nota_max: "4" } : { nota_min: nota };
}
