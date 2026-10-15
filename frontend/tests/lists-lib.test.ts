import { describe, expect, it } from "vitest";

import {
  aplicarOrden,
  combinarItems,
  consultaItems,
  errorDeNombre,
  filtrosActivos,
  filtrosDesdeUrl,
  hayFiltros,
  itemATitulo,
  reordenar,
  rutaPaginaItems,
  urlDeFiltros,
  type ItemLista,
  type ResumenLista,
} from "@/lib/lists";

function lista(id: number, tipo: ResumenLista["tipo"], nombre = `L${id}`): ResumenLista {
  return {
    id,
    nombre,
    clave: tipo === "predeterminada" ? "favoritos" : null,
    tipo,
    cantidad_items: 0,
    cantidad_peliculas: 0,
    cantidad_series: 0,
    preview_posters: [],
  };
}

const listas = [
  lista(1, "predeterminada"),
  lista(2, "predeterminada"),
  lista(3, "personalizada"),
  lista(4, "personalizada"),
  lista(5, "personalizada"),
];

describe("nombre de lista", () => {
  it("rechaza vacío y caracteres inválidos, acepta letras con acento y números", () => {
    expect(errorDeNombre("   ")).toBe("required");
    expect(errorDeNombre("Cine #1")).toBe("invalid");
    expect(errorDeNombre("Maratón 2024")).toBeNull();
  });
});

describe("orden de las personalizadas", () => {
  it("mueve una personalizada y deja fuera a las predeterminadas", () => {
    expect(reordenar(listas, 0, 2)).toEqual([4, 5, 3]);
    expect(reordenar(listas, 2, 0)).toEqual([5, 3, 4]);
  });

  it("un movimiento fuera de rango no cambia el orden", () => {
    expect(reordenar(listas, 0, 3)).toEqual([3, 4, 5]);
    expect(reordenar(listas, -1, 1)).toEqual([3, 4, 5]);
  });

  it("aplica un orden y mantiene las predeterminadas arriba", () => {
    expect(aplicarOrden(listas, [5, 3, 4]).map((l) => l.id)).toEqual([1, 2, 5, 3, 4]);
  });
});

describe("filtros del detalle", () => {
  it("ida y vuelta por la URL, ignorando valores desconocidos", () => {
    const filtros = filtrosDesdeUrl(new URLSearchParams("q=alien&type=tv&rating=8&sort=title"));
    expect(filtros).toEqual({ q: "alien", clase: "tv", nota: "8", orden: "title" });
    expect(urlDeFiltros(7, filtros)).toBe("/lists/7?q=alien&type=tv&rating=8&sort=title");
    expect(filtrosDesdeUrl(new URLSearchParams("type=x&rating=2&sort=zzz"))).toEqual({
      q: "",
      clase: null,
      nota: null,
      orden: "recent",
    });
    expect(urlDeFiltros(7, filtrosDesdeUrl(new URLSearchParams()))).toBe("/lists/7");
  });

  it("traduce a la API: nota «N o más», «menos de 5» y orden", () => {
    const base = {
      q: " dune ",
      clase: "movie" as const,
      nota: "9" as const,
      orden: "recent" as const,
    };
    expect(consultaItems(7, base)).toBe("/api/lists/7/items/?q=dune&clase=movie&nota=9%2B");
    expect(consultaItems(7, { ...base, nota: "lt5", orden: "lowest" })).toBe(
      "/api/lists/7/items/?q=dune&clase=movie&nota=m5&orden=nota-asc"
    );
    expect(consultaItems(7, { q: "", clase: null, nota: null, orden: "recent" })).toBe(
      "/api/lists/7/items/"
    );
  });

  it("cuenta tipo y nota; el orden y el texto no entran en el badge", () => {
    const filtros = { q: "x", clase: "tv" as const, nota: null, orden: "title" as const };
    expect(filtrosActivos(filtros)).toBe(1);
    expect(hayFiltros({ ...filtros, clase: null })).toBe(true);
    expect(hayFiltros({ q: " ", clase: null, nota: null, orden: "title" })).toBe(false);
  });
});

describe("ítems", () => {
  const item = (item_id: number): ItemLista => ({
    item_id,
    fecha_agregado: "2026-10-01T00:00:00Z",
    id_tmdb: 100 + item_id,
    tipo: "movie",
    titulo: `T${item_id}`,
    poster: "/p.jpg",
    anio: 2020,
    calificacion_promedio: null,
  });

  it("no repite ítems al sumar una página", () => {
    expect(combinarItems([item(1), item(2)], [item(2), item(3)]).map((i) => i.item_id)).toEqual([
      1, 2, 3,
    ]);
  });

  it("solo reutiliza el cursor del next", () => {
    expect(rutaPaginaItems(7, "https://evil.test/api/lists/9/items/?cursor=abc")).toBe(
      "/api/lists/7/items/?cursor=abc"
    );
  });

  it("arma el título para la tarjeta con el póster de TMDB", () => {
    const titulo = itemATitulo(item(1));
    expect(titulo).toMatchObject({ tipo: "movie", id: 101, nota: null });
    expect(titulo.poster).toBe("https://image.tmdb.org/t/p/w342/p.jpg");
  });
});
