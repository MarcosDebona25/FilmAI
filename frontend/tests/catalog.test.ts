import { describe, expect, it } from "vitest";

import { normalizeTitle, normalizeTitles, tmdbImage, tmdbLoader } from "@/lib/catalog";
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

  it("descarta un título repetido, pero no una serie con el mismo número", () => {
    const serieMismoId = { ...reacher, id: insidious.id };

    expect(
      normalizeTitles([insidious, insidious, serieMismoId]).map((t) => `${t.tipo}-${t.id}`)
    ).toEqual(["movie-1291595", "tv-1291595"]);
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

describe("tmdbLoader", () => {
  const poster = "https://image.tmdb.org/t/p/w342/abc.jpg";
  const backdrop = "https://image.tmdb.org/t/p/w1280/fondo.jpg";

  it("elige el ancho de TMDB más chico que alcanza", () => {
    expect(tmdbLoader({ src: poster, width: 64 })).toBe("https://image.tmdb.org/t/p/w92/abc.jpg");
    expect(tmdbLoader({ src: poster, width: 180 })).toBe("https://image.tmdb.org/t/p/w185/abc.jpg");
    expect(tmdbLoader({ src: backdrop, width: 640 })).toBe(
      "https://image.tmdb.org/t/p/w780/fondo.jpg"
    );
  });

  it("acepta un ancho hasta 10 % menor antes de saltar al siguiente", () => {
    // Celular con densidad 2: Next pide 828 px; 780 alcanza y pesa la mitad que 1280.
    expect(tmdbLoader({ src: backdrop, width: 828 })).toBe(
      "https://image.tmdb.org/t/p/w780/fondo.jpg"
    );
  });

  it("nunca pasa del ancho que pidió la URL", () => {
    // Antes de este loader se bajaba siempre ese ancho: no puede pesar más.
    expect(tmdbLoader({ src: poster, width: 1080 })).toBe(poster);
    expect(tmdbLoader({ src: backdrop, width: 3840 })).toBe(backdrop);
  });

  it("deja igual lo que no es del CDN de TMDB", () => {
    expect(tmdbLoader({ src: "/avatars/a.png", width: 96 })).toBe("/avatars/a.png");
  });
});
