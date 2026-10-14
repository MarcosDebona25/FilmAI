/** Reglas del Home (C-05) sin React, para probarlas aparte. */
import type { ContentType } from "@/components/features/TypeSelector";
import type { Title } from "@/lib/catalog";

/**
 * Regla del Hero (pedida el 03/10/2026): el primer título con imagen de fondo.
 * En Movies o TV shows se saltea el Hero de All, así cada opción del selector
 * muestra uno distinto. `puesto` es su posición real en tendencias.
 */
export function elegirHero(titulos: Title[], excluir?: Title | null) {
  const indice = titulos.findIndex(
    (titulo) =>
      titulo.backdrop && !(excluir && excluir.tipo === titulo.tipo && excluir.id === titulo.id)
  );
  return indice === -1 ? null : { titulo: titulos[indice], puesto: indice + 1 };
}

/** Película, serie, película…; cuando una lista se acaba, sigue la otra. */
export function alternar<T>(a: T[], b: T[], tope: number): T[] {
  const mezcla: T[] = [];
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    if (i < a.length) mezcla.push(a[i]);
    if (i < b.length) mezcla.push(b[i]);
  }
  return mezcla.slice(0, tope);
}

/** `?type=` de la URL: `movie` o `tv`; cualquier otra cosa es All. */
export function tipoDesdeUrl(valor: string | null): ContentType {
  return valor === "movie" || valor === "tv" ? valor : "all";
}

/**
 * Tamaño del título del Hero según su largo (pedido del 14/10/2026). A 152 px
 * entran unos 19 caracteres por renglón en escritorio: los títulos cortos
 * conservan el tamaño del canvas y los largos se achican para no comerse el
 * Hero. Cuenta caracteres visibles, no unidades UTF-16.
 */
export function tamanioTitulo(titulo: string): "grande" | "mediano" | "chico" {
  const largo = [...titulo].length;
  return largo <= 16 ? "grande" : largo <= 28 ? "mediano" : "chico";
}
