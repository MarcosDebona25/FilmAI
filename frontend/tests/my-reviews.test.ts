import { afterEach, describe, expect, it } from "vitest";

import {
  FILTROS_VACIOS,
  consultaApi,
  filtrosActivos,
  filtrosDesdeUrl,
  guardarUltimasResenas,
  hayFiltros,
  ultimasResenas,
  urlDeFiltros,
} from "@/lib/my-reviews";

afterEach(() => window.sessionStorage.clear());

describe("filtros de Calificaciones y reseñas", () => {
  it("lee la URL y descarta valores que no existen", () => {
    expect(
      filtrosDesdeUrl(new URLSearchParams("q=dune&review=with&type=tv&rating=lt5&sort=highest"))
    ).toEqual({ q: "dune", resena: "with", clase: "tv", nota: "lt5", orden: "highest" });
    expect(filtrosDesdeUrl(new URLSearchParams("review=si&type=anime&rating=3&sort=azar"))).toEqual(
      FILTROS_VACIOS
    );
    // El mismo tope que el backend: 100 caracteres.
    expect(filtrosDesdeUrl(new URLSearchParams(`q=${"a".repeat(150)}`)).q).toHaveLength(100);
  });

  it("escribe la URL sin los valores por defecto y la vuelve a leer igual", () => {
    expect(urlDeFiltros(FILTROS_VACIOS)).toBe("/my-reviews");
    const filtros = {
      q: "el señor",
      resena: "without",
      clase: "movie",
      nota: "8",
      orden: "oldest",
    } as const;
    const url = urlDeFiltros(filtros);
    expect(url).toBe("/my-reviews?q=el+se%C3%B1or&review=without&type=movie&rating=8&sort=oldest");
    expect(filtrosDesdeUrl(new URL(url, "http://x").searchParams)).toEqual(filtros);
  });

  it("traduce a los parámetros de reviews/mias/", () => {
    expect(consultaApi(FILTROS_VACIOS)).toBe("/api/reviews/mias/");
    expect(
      consultaApi({ q: "  dune ", resena: "with", clase: "tv", nota: "8", orden: "lowest" })
    ).toBe("/api/reviews/mias/?q=dune&texto=con&clase=tv&nota_min=8&orden=nota-asc");
    // «Menos de 5» es una nota máxima de 4: las notas son enteras.
    expect(consultaApi({ ...FILTROS_VACIOS, resena: "without", nota: "lt5" })).toBe(
      "/api/reviews/mias/?texto=sin&nota_max=4"
    );
    expect(consultaApi({ ...FILTROS_VACIOS, q: "   " })).toBe("/api/reviews/mias/");
  });

  it("cuenta filtros activos sin el texto ni el orden", () => {
    expect(filtrosActivos({ ...FILTROS_VACIOS, q: "x", orden: "oldest" })).toBe(0);
    expect(filtrosActivos({ ...FILTROS_VACIOS, resena: "with", nota: "9" })).toBe(2);
    expect(hayFiltros({ ...FILTROS_VACIOS, orden: "oldest" })).toBe(false);
    expect(hayFiltros({ ...FILTROS_VACIOS, q: "x" })).toBe(true);
    expect(hayFiltros({ ...FILTROS_VACIOS, clase: "movie" })).toBe(true);
  });

  it("la miga de la ficha solo vuelve a esta pantalla", () => {
    expect(ultimasResenas()).toBe("/my-reviews");
    guardarUltimasResenas("/my-reviews?rating=9");
    expect(ultimasResenas()).toBe("/my-reviews?rating=9");
    guardarUltimasResenas("https://otro.example/my-reviews");
    expect(ultimasResenas()).toBe("/my-reviews");
  });
});
