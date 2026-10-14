/** Listas desde la ficha (L-04 dentro de C-07). */

/** Un resumen de `GET /api/lists/?id_tmdb=&tipo=` (L-01) con la pertenencia. */
export interface ListaFicha {
  id: number;
  nombre: string;
  clave: "favoritos" | "vistas" | "pendientes" | null;
  tipo: "predeterminada" | "personalizada";
  cantidad_items: number;
  contiene: boolean;
  item_id: number | null;
}

/** La lista con `id`, reemplazada por `cambios`; el resto queda igual. */
export function actualizarLista(listas: ListaFicha[], id: number, cambios: Partial<ListaFicha>) {
  return listas.map((lista) => (lista.id === id ? { ...lista, ...cambios } : lista));
}

export const conItem = (lista: ListaFicha, itemId: number): Partial<ListaFicha> => ({
  contiene: true,
  item_id: itemId,
  cantidad_items: lista.cantidad_items + 1,
});

export const sinItem = (lista: ListaFicha): Partial<ListaFicha> => ({
  contiene: false,
  item_id: null,
  cantidad_items: Math.max(0, lista.cantidad_items - 1),
});
