import { apiFetch } from "@/lib/api";
import type { MediaType } from "@/lib/catalog";
import type { ListaFicha } from "@/lib/title-lists";

/**
 * El estado único de un título (PR 4, 15/11/2026): Pendientes, Viendo o Vistas,
 * uno solo a la vez. Es la clave de la lista predeterminada que lo contiene; sin
 * estado, ninguna de las tres lo tiene.
 */
export type Estado = "pendientes" | "viendo" | "vistas";

/** En el orden del menú de la ficha. */
export const ESTADOS: readonly Estado[] = ["pendientes", "viendo", "vistas"];

/** En cuál de las tres listas de estado está el título; `null` si en ninguna. */
export function estadoDe(listas: ListaFicha[]): Estado | null {
  const lista = listas.find(
    (candidata) => ESTADOS.some((e) => candidata.clave === e) && candidata.contiene
  );
  return (lista?.clave as Estado | undefined) ?? null;
}

/**
 * Las listas como quedarían con ese estado, para mostrarlo antes de que
 * responda el servidor (cambio optimista). Ajusta la pertenencia y el conteo de
 * las tres listas de estado; Favoritos y las propias quedan como están. El
 * `item_id` del ingreso nuevo se conoce recién con la respuesta.
 */
export function conEstado(listas: ListaFicha[], estado: Estado | null): ListaFicha[] {
  return listas.map((lista) => {
    if (!ESTADOS.some((e) => e === lista.clave)) return lista;
    const debeContener = lista.clave === estado;
    if (debeContener === lista.contiene) return lista;
    return {
      ...lista,
      contiene: debeContener,
      item_id: null,
      fecha_agregado: null,
      cantidad_items: Math.max(0, lista.cantidad_items + (debeContener ? 1 : -1)),
    };
  });
}

/** Lo que responde `PUT /api/lists/status/`. */
export interface RespuestaEstado {
  estado: Estado | null;
  /** A lo que vuelve el Undo. */
  estado_anterior: Estado | null;
  /** Lo mismo que `GET /api/lists/?id_tmdb=&tipo=`. */
  listas: ListaFicha[];
}

/**
 * Pone el estado del título de una vez (quita el anterior en la misma
 * operación). `estado` es obligatorio aunque sea `null`: así un olvido no borra
 * el estado. El Undo es llamar de nuevo con `estado_anterior` y la fecha que
 * tenía (`fechaAgregado`), para que «Empezada el» no se reinicie.
 */
export function guardarEstado(datos: {
  idTmdb: number;
  tipo: MediaType;
  estado: Estado | null;
  /** Solo el Undo: la fecha que el título tenía en ese estado (ISO). */
  fechaAgregado?: string | null;
}) {
  return apiFetch<RespuestaEstado>("/api/lists/status/", {
    method: "PUT",
    body: {
      id_tmdb: datos.idTmdb,
      tipo: datos.tipo,
      estado: datos.estado,
      ...(datos.fechaAgregado ? { fecha_agregado: datos.fechaAgregado } : {}),
    },
  });
}

/** La fecha en que el título entró a la lista de ese estado, si la conocemos. */
export function fechaDeEstado(listas: ListaFicha[], estado: Estado | null): string | null {
  if (!estado) return null;
  return listas.find((lista) => lista.clave === estado)?.fecha_agregado ?? null;
}
