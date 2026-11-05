import type { MediaType } from "@/lib/catalog";

/**
 * Fondos elegidos a mano, para títulos cuya imagen de TMDB repite el arte del
 * póster. No hay un dato que permita detectarlos: se agregan de a uno, con una
 * ruta de `/{tipo}/{id}/images` (05/11/2026).
 */
const FONDOS_ELEGIDOS: Record<string, string> = {
  // Attack on Titan: la de TMDB es un primer plano de la cara, igual que el póster.
  "tv:1429": "/2b0s0iMNl9CgrCMz0VGKlMw3vZw.jpg",
};

/** La ruta del fondo de un título: la elegida a mano o, si no hay, la de TMDB. */
export function rutaDeFondo(tipo: MediaType, id: number, ruta?: string | null) {
  return FONDOS_ELEGIDOS[`${tipo}:${id}`] ?? ruta;
}
