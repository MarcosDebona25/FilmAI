import { describe, expect, it } from "vitest";
import { tmdbImage } from "@/lib/catalog";
import { combinarResenas, rutaPagina, type MiResena } from "@/lib/reviews";
import { tieneCambios } from "@/lib/profile-draft";
import type { Perfil } from "@/components/AccountProvider";
const item: MiResena = {
  id: 1,
  id_tmdb: 10,
  tipo: "movie",
  titulo: "Interstellar",
  poster: "/poster.jpg",
  valor: 8,
  fecha: "2026-10-03",
  texto: "Muy buena",
  moderada: false,
};
describe("contratos de edición y paginación", () => {
  it("reutiliza solo el cursor en nuestra ruta de API", () =>
    expect(rutaPagina("https://otro.example/api/reviews/mias/?cursor=a%3D")).toBe(
      "/api/reviews/mias/?cursor=a%3D"
    ));
  it("deduplica páginas sin cambiar el orden", () =>
    expect(
      combinarResenas(
        [item],
        [
          { ...item, valor: 9 },
          { ...item, id: 2 },
        ]
      ).map((x) => [x.id, x.valor])
    ).toEqual([
      [1, 8],
      [2, 8],
    ]));
  it("admite pósters de TMDB en w185 y descarta imágenes ajenas", () => {
    expect(tmdbImage("/p.jpg", "w185")).toBe("https://image.tmdb.org/t/p/w185/p.jpg");
    expect(tmdbImage("https://image.tmdb.org/t/p/w185/p.jpg", "w185")).toContain("image.tmdb.org");
    expect(tmdbImage("", "w185")).toBeNull();
    expect(tmdbImage("https://otro.example/p.jpg", "w185")).toBeNull();
  });
});
describe("perfil y advertencias", () => {
  const perfil = {
    nombre: "Juan",
    apellido: "Pérez",
    nombre_usuario: "juanperez",
    avatar_id: 1,
  } as Perfil;
  it("detecta cambios de avatar y campos, pero no un borrador revertido", () => {
    expect(tieneCambios(null, perfil)).toBe(false);
    expect(tieneCambios(perfil, perfil)).toBe(false);
    expect(tieneCambios({ ...perfil, avatar_id: 2 }, perfil)).toBe(true);
    expect(tieneCambios({ ...perfil, nombre: "Pedro" }, perfil)).toBe(true);
  });
});
