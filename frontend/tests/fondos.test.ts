import { describe, expect, it } from "vitest";

import { normalizeTitle, type TmdbItem } from "@/lib/catalog";
import { rutaDeFondo } from "@/lib/fondos";
import { normalizarFicha } from "@/lib/title";

const ELEGIDA = "/2b0s0iMNl9CgrCMz0VGKlMw3vZw.jpg";
const DE_TMDB = "/rqbCbjB19amtOtFQbb3K2lgm2zv.jpg";

describe("rutaDeFondo", () => {
  it("usa la imagen elegida para un título de la lista", () => {
    expect(rutaDeFondo("tv", 1429, DE_TMDB)).toBe(ELEGIDA);
  });

  it("un título que no está en la lista conserva la de TMDB", () => {
    expect(rutaDeFondo("tv", 1396, DE_TMDB)).toBe(DE_TMDB);
  });

  it("una película con el mismo id que la serie no se confunde", () => {
    expect(rutaDeFondo("movie", 1429, DE_TMDB)).toBe(DE_TMDB);
  });

  it("sin imagen de TMDB sigue sin imagen", () => {
    expect(rutaDeFondo("tv", 1396, null)).toBeNull();
  });
});

describe("dónde se aplica", () => {
  it("en la ficha", () => {
    const ficha = normalizarFicha(
      { id: 1429, name: "Attack on Titan", backdrop_path: DE_TMDB },
      "tv"
    );

    expect(ficha.backdrop).toContain(ELEGIDA);
  });

  it("en el Inicio", () => {
    const item = { id: 1429, name: "Attack on Titan", backdrop_path: DE_TMDB } as TmdbItem;

    expect(normalizeTitle(item, "tv")?.backdrop).toContain(ELEGIDA);
  });
});
