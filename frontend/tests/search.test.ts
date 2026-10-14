import { afterEach, describe, expect, it, vi } from "vitest";

import {
  BUSQUEDA_VACIA,
  aniosDisponibles,
  busquedaDesdeUrl,
  consultaApi,
  filtrosActivos,
  guardarUltimaBusqueda,
  ultimaBusqueda,
  urlDeBusqueda,
} from "@/lib/search";

describe("busquedaDesdeUrl", () => {
  it("sin parámetros es la búsqueda vacía", () => {
    expect(busquedaDesdeUrl(new URLSearchParams())).toEqual(BUSQUEDA_VACIA);
  });

  it("lee texto, tipo, filtros y página", () => {
    const params = new URLSearchParams("q=dune&type=movie&genre=878&year=2021&rating=8&page=2");

    expect(busquedaDesdeUrl(params)).toEqual({
      q: "dune",
      tipo: "movie",
      genero: 878,
      anio: 2021,
      nota: "8",
      pagina: 2,
    });
  });

  it("descarta lo que no entiende en vez de romper", () => {
    const params = new URLSearchParams("type=person&genre=abc&year=-3&rating=11&page=0");

    expect(busquedaDesdeUrl(params)).toEqual(BUSQUEDA_VACIA);
  });

  it("recorta el texto a 50 caracteres", () => {
    const params = new URLSearchParams({ q: "x".repeat(60) });

    expect(busquedaDesdeUrl(params).q).toHaveLength(50);
  });
});

describe("urlDeBusqueda", () => {
  it("la búsqueda vacía es /search, sin parámetros", () => {
    expect(urlDeBusqueda(BUSQUEDA_VACIA)).toBe("/search");
  });

  it("solo escribe lo que difiere de lo predeterminado e ida y vuelta da lo mismo", () => {
    const busqueda = { ...BUSQUEDA_VACIA, q: "ocean's", tipo: "tv" as const, nota: "lt5" as const };

    const url = urlDeBusqueda(busqueda);

    expect(url).toBe("/search?q=ocean%27s&type=tv&rating=lt5");
    expect(busquedaDesdeUrl(new URL(url, "http://x").searchParams)).toEqual(busqueda);
  });
});

describe("consultaApi", () => {
  it("traduce al contrato de browse/ (nota con +, «Menos de 5» como m5)", () => {
    expect(
      consultaApi({ q: " dune ", tipo: "all", genero: 878, anio: 2021, nota: "8", pagina: 3 })
    ).toBe("/api/catalogo/browse/?q=dune&tipo=all&genero=878&anio=2021&nota=8%2B&page=3");
    expect(consultaApi({ ...BUSQUEDA_VACIA, nota: "lt5" })).toBe(
      "/api/catalogo/browse/?tipo=all&nota=m5&page=1"
    );
  });
});

describe("filtrosActivos", () => {
  it("cuenta género, año y nota; el texto y el tipo no son filtros", () => {
    expect(filtrosActivos({ ...BUSQUEDA_VACIA, q: "dune", tipo: "movie" })).toBe(0);
    expect(filtrosActivos({ ...BUSQUEDA_VACIA, genero: 18, anio: 2020, nota: "7" })).toBe(3);
  });
});

describe("aniosDisponibles", () => {
  it("va del año actual a 1900", () => {
    const anios = aniosDisponibles(2026);

    expect(anios[0]).toBe(2026);
    expect(anios.at(-1)).toBe(1900);
    expect(anios).toHaveLength(127);
  });
});

describe("última búsqueda", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.sessionStorage.clear();
  });

  it("devuelve la que se guardó", () => {
    guardarUltimaBusqueda("/search?q=dune&genre=878");

    expect(ultimaBusqueda()).toBe("/search?q=dune&genre=878");
  });

  it("sin nada guardado, o con algo que no es de Buscar, va a /search", () => {
    expect(ultimaBusqueda()).toBe("/search");
    window.sessionStorage.setItem("filmai:ultima-busqueda", "https://otro.sitio/");
    expect(ultimaBusqueda()).toBe("/search");
  });

  it("sin sessionStorage (modo privado) no rompe", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });

    expect(() => guardarUltimaBusqueda("/search?q=dune")).not.toThrow();
    expect(ultimaBusqueda()).toBe("/search");
  });
});
