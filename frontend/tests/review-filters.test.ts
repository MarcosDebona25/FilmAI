import { afterEach, describe, expect, it, vi } from "vitest";

import { crearUltimaVista } from "@/lib/last-view";
import { ORDENES, ORDEN_API, parametrosNota } from "@/lib/review-filters";
import { NOTAS, de, etiquetaNota } from "@/lib/search";

describe("filtros compartidos de reseñas", () => {
  it("«N o más» es una nota mínima y «Menos de 5», una máxima de 4", () => {
    expect(parametrosNota("9")).toEqual({ nota_min: "9" });
    expect(parametrosNota("5")).toEqual({ nota_min: "5" });
    expect(parametrosNota("lt5")).toEqual({ nota_max: "4" });
  });

  it("cada orden tiene su valor de la API", () => {
    expect(ORDENES.map((orden) => ORDEN_API[orden])).toEqual([
      "fecha-desc",
      "fecha-asc",
      "nota-desc",
      "nota-asc",
    ]);
  });

  it("`de` solo acepta valores de la lista", () => {
    expect(de(NOTAS, "lt5")).toBe("lt5");
    expect(de(NOTAS, "9+")).toBeNull();
    expect(de(NOTAS, null)).toBeNull();
  });

  it("la etiqueta de la nota tiene forma larga y corta", () => {
    const t = (clave: string, valores?: { value: string }) =>
      valores ? `${clave}:${valores.value}` : clave;

    expect(etiquetaNota(t, null)).toBe("common.filters.anyRating");
    expect(etiquetaNota(t, null, true)).toBe("common.filters.anyRating");
    expect(etiquetaNota(t, "9")).toBe("common.filters.ratingAtLeastNine");
    expect(etiquetaNota(t, "9", true)).toBe("search.filters.ratingShort:9");
    expect(etiquetaNota(t, "lt5", true)).toBe("search.filters.ratingShortBelowFive");
  });
});

describe("última vista", () => {
  const vista = crearUltimaVista("filmai:prueba", "/lista");

  afterEach(() => {
    vi.restoreAllMocks();
    window.sessionStorage.clear();
  });

  it("devuelve lo guardado si es de la misma ruta", () => {
    vista.guardar("/lista?q=dune");
    expect(vista.leer()).toBe("/lista?q=dune");
    vista.guardar("/lista");
    expect(vista.leer()).toBe("/lista");
  });

  it("sin nada guardado, o con otra ruta, vuelve a la ruta sin filtros", () => {
    expect(vista.leer()).toBe("/lista");
    vista.guardar("/listas-ajenas");
    expect(vista.leer()).toBe("/lista");
    vista.guardar("https://otro.sitio/lista?q=a");
    expect(vista.leer()).toBe("/lista");
  });

  it("sin sessionStorage (modo privado) no rompe", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });

    expect(() => vista.guardar("/lista?q=a")).not.toThrow();
    expect(vista.leer()).toBe("/lista");
  });
});
