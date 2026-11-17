import { describe, expect, it } from "vitest";

import { conEstado, estadoDe } from "@/lib/title-status";
import type { ListaFicha } from "@/lib/title-lists";

const lista = (campos: Partial<ListaFicha>): ListaFicha => ({
  id: 1,
  nombre: "x",
  clave: null,
  tipo: "predeterminada",
  cantidad_items: 0,
  contiene: false,
  item_id: null,
  ...campos,
});
const LISTAS = [
  lista({ id: 1, clave: "favoritos", contiene: true, item_id: 5, cantidad_items: 2 }),
  lista({ id: 2, clave: "pendientes", contiene: true, item_id: 6, cantidad_items: 4 }),
  lista({ id: 3, clave: "viendo", cantidad_items: 1 }),
  lista({ id: 4, clave: "vistas", cantidad_items: 7 }),
  lista({ id: 5, tipo: "personalizada", contiene: true, item_id: 9, cantidad_items: 3 }),
];

describe("estado único de un título", () => {
  it("estadoDe lee en cuál de Pendientes, Viendo y Vistas está", () => {
    expect(estadoDe(LISTAS)).toBe("pendientes");
    expect(estadoDe(LISTAS.map((l) => ({ ...l, contiene: false })))).toBeNull();
  });

  it("estadoDe ignora Favoritos y las listas propias", () => {
    const soloFavoritas = LISTAS.map((l) =>
      l.clave === "pendientes" ? { ...l, contiene: false } : l
    );
    expect(estadoDe(soloFavoritas)).toBeNull();
  });

  it("conEstado mueve la pertenencia y los conteos, y no toca el resto", () => {
    const nuevas = conEstado(LISTAS, "viendo");

    expect(nuevas.find((l) => l.clave === "pendientes")).toMatchObject({
      contiene: false,
      item_id: null,
      cantidad_items: 3,
    });
    expect(nuevas.find((l) => l.clave === "viendo")).toMatchObject({
      contiene: true,
      cantidad_items: 2,
    });
    expect(nuevas.find((l) => l.clave === "vistas")).toMatchObject({ contiene: false });
    expect(nuevas.find((l) => l.clave === "favoritos")).toEqual(LISTAS[0]);
    expect(nuevas.at(-1)).toEqual(LISTAS.at(-1));
  });

  it("conEstado(null) quita el estado y repetir el estado no cambia nada", () => {
    expect(estadoDe(conEstado(LISTAS, null))).toBeNull();
    expect(conEstado(LISTAS, "pendientes")).toEqual(LISTAS);
  });
});
