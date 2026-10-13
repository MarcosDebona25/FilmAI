import { describe, expect, it } from "vitest";

import { normalizeTitle, normalizeTitles, tmdbImage } from "@/lib/catalog";
import { routes } from "@/lib/routes";
import { insidious, persona, reacher } from "./catalog-fixtures";

describe("normalizeTitle", () => {
  it("una película de TMDB queda con la forma de la app", () => {
    expect(normalizeTitle(insidious)).toEqual({
      tipo: "movie",
      id: 1291595,
      titulo: "Insidious: Out of the Further",
      sinopsis: insidious.overview,
      anio: 2026,
      nota: 7.725,
      poster: "https://image.tmdb.org/t/p/w342/4tTrW9dXCByS5wt2pXVWb58zNjz.jpg",
      backdrop: "https://image.tmdb.org/t/p/w1280/p40lmrdI4blcAPZQMTPaiy5v5Ym.jpg",
      generoIds: [27, 53],
      tituloEnIngles: false,
      sinopsisEnIngles: false,
    });
  });

  it("una serie toma el nombre y el año de first_air_date", () => {
    const serie = normalizeTitle(reacher);

    expect(serie).toMatchObject({ tipo: "tv", titulo: "Reacher", anio: 2022 });
  });

  it("sin media_type usa el tipo que le pasan (discover no lo trae)", () => {
    const sinTipo = { ...insidious, media_type: undefined };

    expect(normalizeTitle(sinTipo, "movie")?.tipo).toBe("movie");
    expect(normalizeTitle(sinTipo)).toBeNull();
  });

  it("descarta personas y deja el resto en orden", () => {
    expect(normalizeTitles([insidious, persona, reacher]).map((t) => t.id)).toEqual([
      1291595, 108978,
    ]);
  });

  it("sin votos no hay nota y sin fecha no hay año", () => {
    // El 13/10/2026, 9 de 100 títulos de trending tenían vote_average 0.
    const titulo = normalizeTitle({ ...insidious, vote_average: 0, release_date: "" });

    expect(titulo?.nota).toBeNull();
    expect(titulo?.anio).toBeNull();
  });

  it("marca los campos que el backend completó en inglés", () => {
    const titulo = normalizeTitle({ ...insidious, campos_en_ingles: ["title"] });

    expect(titulo?.tituloEnIngles).toBe(true);
    expect(titulo?.sinopsisEnIngles).toBe(false);
  });
});

describe("tmdbImage", () => {
  it("arma la URL de TMDB con el tamaño pedido", () => {
    expect(tmdbImage("/a.jpg", "w342")).toBe("https://image.tmdb.org/t/p/w342/a.jpg");
  });

  it("rechaza lo que no sea una ruta de TMDB", () => {
    expect(tmdbImage(null, "w342")).toBeNull();
    expect(tmdbImage("//otro.com/a.jpg", "w342")).toBeNull();
    expect(tmdbImage("https://otro.com/a.jpg", "w342")).toBeNull();
  });
});

describe("routes.title", () => {
  it("lleva a la ficha de película o de serie", () => {
    expect(routes.title("movie", 1291595)).toBe("/movie/1291595");
    expect(routes.title("tv", 108978)).toBe("/tv/108978");
  });
});
