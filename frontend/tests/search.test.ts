import { afterEach, describe, expect, it, vi } from "vitest";

import {
  BUSQUEDA_VACIA,
  opcionesDeAnio,
  anioDesdeOpcion,
  opcionDeAnio,
  busquedaDesdeUrl,
  consultaApi,
  filtrosActivos,
  guardarScrollBusqueda,
  guardarUltimaBusqueda,
  scrollGuardado,
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

describe("«A estrenar»", () => {
  it("va en la URL como year=upcoming y a la API como a_estrenar, sin año", () => {
    const busqueda = busquedaDesdeUrl(new URLSearchParams("q=avatar&year=upcoming"));

    expect(busqueda.anio).toBe("proximos");
    expect(urlDeBusqueda(busqueda)).toBe("/search?q=avatar&year=upcoming");
    expect(consultaApi(busqueda)).toBe(
      "/api/catalogo/browse/?q=avatar&tipo=all&a_estrenar=true&page=1"
    );
    expect(filtrosActivos(busqueda)).toBe(1);
  });

  it("el selector traduce sus valores al estado y de vuelta", () => {
    expect(anioDesdeOpcion("upcoming")).toBe("proximos");
    expect(anioDesdeOpcion("1999")).toBe(1999);
    expect(anioDesdeOpcion("")).toBeNull();
    expect(opcionDeAnio("proximos")).toBe("upcoming");
    expect(opcionDeAnio(1999)).toBe("1999");
    expect(opcionDeAnio(null)).toBe("");
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

describe("scroll de la grilla", () => {
  afterEach(() => window.sessionStorage.clear());

  it("devuelve la posición solo para la misma búsqueda", () => {
    guardarScrollBusqueda("/search?q=batman&page=4", 4240);

    expect(scrollGuardado("/search?q=batman&page=4")).toBe(4240);
    expect(scrollGuardado("/search?q=batman")).toBeNull();
  });

  it("con algo roto guardado no rompe", () => {
    window.sessionStorage.setItem("filmai:scroll-busqueda", "{no es json");

    expect(scrollGuardado("/search")).toBeNull();
  });
});

describe("opcionesDeAnio", () => {
  it("años sueltos del actual a 1990 y, antes, décadas hasta la de 1900", () => {
    const opciones = opcionesDeAnio(2026);

    expect(opciones[0]).toEqual({ valor: "2026", decada: null });
    expect(opciones.find((o) => o.valor === "1990")).toBeDefined();
    expect(opciones.find((o) => o.valor === "1989")).toBeUndefined();
    expect(opciones.slice(37).map((o) => o.valor)).toEqual([
      "1980s",
      "1970s",
      "1960s",
      "1950s",
      "1940s",
      "1930s",
      "1920s",
      "1910s",
      "1900s",
    ]);
    expect(opciones.at(-1)).toEqual({ valor: "1900s", decada: 1900 });
  });

  it("una década va en la URL como 1980s y a la API como decada=1980", () => {
    const busqueda = busquedaDesdeUrl(new URLSearchParams("year=1980s"));

    expect(busqueda.anio).toBe("1980s");
    expect(urlDeBusqueda(busqueda)).toBe("/search?year=1980s");
    expect(consultaApi(busqueda)).toBe("/api/catalogo/browse/?tipo=all&decada=1980&page=1");
    // Lo que no es una década válida se ignora.
    expect(busquedaDesdeUrl(new URLSearchParams("year=1985s")).anio).toBeNull();
    expect(busquedaDesdeUrl(new URLSearchParams("year=1890s")).anio).toBeNull();
  });
});
