import { describe, expect, it } from "vitest";
import { combinarResenas, posterUrl, rutaPagina, type MiResena } from "@/lib/reviews";
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
  it("admite pósters de TMDB y descarta imágenes ajenas", () => {
    expect(posterUrl("/p.jpg")).toBe("https://image.tmdb.org/t/p/w185/p.jpg");
    expect(posterUrl("https://image.tmdb.org/t/p/w185/p.jpg")).toContain("image.tmdb.org");
    expect(posterUrl("")).toBeNull();
    expect(posterUrl("https://otro.example/p.jpg")).toBeNull();
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
