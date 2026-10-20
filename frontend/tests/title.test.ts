import { describe, expect, it } from "vitest";

import { normalizarFicha, origenDesde, planEdicion } from "@/lib/title";
import { routes } from "@/lib/routes";
import { BREAKING_BAD, INTERSTELLAR } from "./title-fixtures";

describe("normalizarFicha", () => {
  it("una película trae duración y póster grande", () => {
    expect(normalizarFicha(INTERSTELLAR, "movie")).toMatchObject({
      tipo: "movie",
      titulo: "Interstellar",
      lema: "Mankind was born on Earth. It was never meant to die here.",
      anio: 2014,
      duracion: 169,
      temporadas: null,
      nota: 8.49,
      votos: 41471,
      generos: ["Adventure", "Drama", "Science Fiction"],
      poster: "https://image.tmdb.org/t/p/w500/yQvGrMoipbRoddT0ZR8tPoR7NfX.jpg",
      backdrop: "https://image.tmdb.org/t/p/w1280/8sNiAPPYU14PUepFNeSNGUTiHW.jpg",
    });
  });

  it("una serie trae temporadas y episodios en lugar de duración", () => {
    expect(normalizarFicha(BREAKING_BAD, "tv")).toMatchObject({
      titulo: "Breaking Bad",
      anio: 2008,
      duracion: null,
      temporadas: 5,
      episodios: 62,
      generos: ["Drama", "Crime"],
    });
  });
});

describe("origenDesde", () => {
  it("reconoce cada origen y todo lo demás es Home", () => {
    expect(origenDesde("search")).toEqual({ tipo: "search" });
    expect(origenDesde("reviews")).toEqual({ tipo: "reviews" });
    expect(origenDesde("list-12")).toEqual({ tipo: "lista", id: 12 });
    expect(origenDesde("list-abc")).toEqual({ tipo: "home" });
    expect(origenDesde(null)).toEqual({ tipo: "home" });
  });

  it("un from hostil nunca produce un destino fuera del sitio (F9)", () => {
    const hostiles = [
      "https://evil.example",
      "//evil.example",
      "/\\evil.example",
      "javascript:alert(1)",
      "list-1/../../evil",
      "list-12\n",
      "list-12 ",
      "LIST-12",
      "search/../x",
      "list-",
    ];
    for (const from of hostiles) {
      expect(origenDesde(from), from).toEqual({ tipo: "home" });
    }
  });

  it("el id de lista sale de dígitos: la miga solo enlaza a /lists/<número>", () => {
    const origen = origenDesde("list-007");
    expect(origen).toEqual({ tipo: "lista", id: 7 });
    expect(routes.list(7)).toBe("/lists/7");
  });

  it("la tarjeta puede sumar el origen a la ruta de la ficha", () => {
    expect(routes.title("movie", 157336, "home")).toBe("/movie/157336?from=home");
  });
});

describe("planEdicion", () => {
  const previo = { valor: 9, texto: "La vi tres veces." };

  it("manda solo lo que cambió", () => {
    expect(planEdicion(previo, 7, "La vi tres veces.")).toEqual({
      borrarTexto: false,
      cambios: { valor: 7 },
    });
    expect(planEdicion(previo, 9, "  Mejor la segunda vez.  ")).toEqual({
      borrarTexto: false,
      cambios: { texto: "Mejor la segunda vez." },
    });
  });

  it("vaciar el texto que existía lo borra aparte", () => {
    expect(planEdicion(previo, 8, "   ")).toEqual({ borrarTexto: true, cambios: { valor: 8 } });
  });

  it("sin cambios no hay nada que pedir", () => {
    expect(planEdicion({ valor: 6, texto: null }, 6, "")).toEqual({
      borrarTexto: false,
      cambios: {},
    });
  });
});
