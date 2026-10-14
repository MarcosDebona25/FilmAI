import { describe, expect, it } from "vitest";

import { normalizeTitle, type Title } from "@/lib/catalog";
import { formatList } from "@/lib/format";
import { alternar, elegirHero, tamanioTitulo, tipoDesdeUrl } from "@/lib/home";
import { insidious, reacher } from "./catalog-fixtures";

const pelicula = normalizeTitle(insidious) as Title;
const serie = normalizeTitle(reacher) as Title;
const sinFondo = { ...pelicula, id: 1, backdrop: null };
const otraPelicula = { ...pelicula, id: 2 };

describe("elegirHero (regla del 03/10/2026)", () => {
  it("en All es el primero de tendencias con imagen de fondo, con su puesto real", () => {
    expect(elegirHero([sinFondo, serie, pelicula])).toEqual({ titulo: serie, puesto: 2 });
  });

  it("en Movies o TV shows saltea el Hero de All para que los tres sean distintos", () => {
    const heroAll = elegirHero([pelicula, serie]);

    expect(elegirHero([pelicula, otraPelicula], heroAll?.titulo)?.titulo.id).toBe(2);
  });

  it("compara por tipo e id: una serie con el mismo número no es el mismo título", () => {
    const serieMismoId = { ...serie, id: pelicula.id };

    expect(elegirHero([serieMismoId], pelicula)?.titulo).toBe(serieMismoId);
  });

  it("sin títulos con imagen no hay Hero", () => {
    expect(elegirHero([sinFondo])).toBeNull();
  });
});

describe("alternar", () => {
  it("intercala y completa con la lista más larga hasta el tope", () => {
    expect(alternar([1, 3, 5, 7], [2, 4], 5)).toEqual([1, 2, 3, 4, 5]);
  });
});

describe("tipoDesdeUrl", () => {
  it("acepta movie y tv; cualquier otra cosa es All", () => {
    expect(tipoDesdeUrl("movie")).toBe("movie");
    expect(tipoDesdeUrl("tv")).toBe("tv");
    expect(tipoDesdeUrl("book")).toBe("all");
    expect(tipoDesdeUrl(null)).toBe("all");
  });
});

describe("formatList", () => {
  it("une los géneros del subtítulo según el idioma", () => {
    expect(formatList(["Thriller", "Drama", "Crime"], "en")).toBe("Thriller, Drama, and Crime");
    expect(formatList(["Suspense", "Drama", "Crimen"], "es")).toBe("Suspense, Drama y Crimen");
  });
});

describe("tamanioTitulo", () => {
  it("los títulos cortos conservan el tamaño del canvas", () => {
    expect(tamanioTitulo("LINK CLICK")).toBe("grande");
    expect(tamanioTitulo("Black Clover")).toBe("grande");
    expect(tamanioTitulo("Abcdefghijklmnop")).toBe("grande"); // 16
  });

  it("los medianos y los largos achican la letra", () => {
    expect(tamanioTitulo("Abcdefghijklmnopq")).toBe("mediano"); // 17
    expect(tamanioTitulo("Spider-Man: Brand New Day")).toBe("mediano"); // 25
    expect(tamanioTitulo("Insidious: Out of the Further")).toBe("chico"); // 29
    expect(tamanioTitulo("Law & Order: Special Victims Unit")).toBe("chico"); // 33
  });

  it("cuenta caracteres, no unidades UTF-16", () => {
    // Cada emoji ocupa dos unidades UTF-16; sigue siendo un carácter visible.
    expect(tamanioTitulo("😀".repeat(16))).toBe("grande");
  });
});
