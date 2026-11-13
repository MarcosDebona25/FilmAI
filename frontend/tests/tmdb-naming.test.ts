import { describe, expect, it } from "vitest";

import { namingViolations, wrongTmdbNames } from "../scripts/i18n/naming.mjs";

describe("nombre de TMDB (TMDB exige «TMDB» o «The Movie Database»)", () => {
  it("rechaza las grafías incorrectas como palabra visible", () => {
    expect(wrongTmdbNames("Powered by TMDb")).toHaveLength(1);
    expect(wrongTmdbNames("Datos de Tmdb")).toHaveLength(1);
    expect(wrongTmdbNames("Provided by The Movie DB")).toHaveLength(1);
    expect(wrongTmdbNames("Provided by TheMovieDB")).toHaveLength(1);
    expect(wrongTmdbNames("See themoviedb for more")).toHaveLength(1);
  });

  it("rechaza enlaces al sitio que no apuntan a https://www.themoviedb.org", () => {
    expect(wrongTmdbNames("https://themoviedb.org/movie/1")).toHaveLength(1);
    expect(wrongTmdbNames("http://www.themoviedb.org")).toHaveLength(1);
    expect(wrongTmdbNames("https://www.themoviedb.org")).toEqual([]);
  });

  it("admite los nombres correctos, los identificadores y el aviso exacto", () => {
    expect(wrongTmdbNames("Data provided by TMDB.")).toEqual([]);
    expect(wrongTmdbNames("The Movie Database (TMDB)")).toEqual([]);
    expect(wrongTmdbNames("Un id_tmdb sale de una herramienta")).toEqual([]);
    expect(
      wrongTmdbNames("This product uses the TMDB API but is not endorsed or certified by TMDB.")
    ).toEqual([]);
  });

  it("los catálogos, el texto legal, los correos y el prompt del chat están limpios", () => {
    expect(namingViolations(process.cwd())).toEqual([]);
  });

  it("nombra la clave o el archivo cuando algo falla", () => {
    const found = namingViolations(process.cwd(), {
      extra: { "messages/en/common.json#footer.main.x": "Data from TMDb" },
    });
    expect(found).toEqual([expect.stringContaining("footer.main.x")]);
  });
});
