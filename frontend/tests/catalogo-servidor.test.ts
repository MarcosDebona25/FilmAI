import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { pedirAlCatalogo, pedirVarias } from "@/lib/catalogo-servidor";

const fetchFalso = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchFalso);
  vi.stubEnv("API_URL_INTERNA", "http://backend:8000/");
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  fetchFalso.mockReset();
});

describe("pedirAlCatalogo (servidor de Next)", () => {
  it("sin API_URL_INTERNA no pide nada: el navegador hace todo como antes", async () => {
    vi.stubEnv("API_URL_INTERNA", "");

    expect(await pedirAlCatalogo("/api/catalogo/trending/?media_type=all", "es")).toBeNull();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("pide al backend interno en el idioma de la página y cachea 5 minutos", async () => {
    fetchFalso.mockResolvedValue(new Response(JSON.stringify({ results: [] })));

    const datos = await pedirAlCatalogo("/api/catalogo/trending/?media_type=all", "es");

    expect(datos).toEqual({ results: [] });
    const [url, opciones] = fetchFalso.mock.calls[0];
    expect(url).toBe("http://backend:8000/api/catalogo/trending/?media_type=all");
    expect(opciones.headers).toEqual({ "Accept-Language": "es" });
    expect(opciones.next).toEqual({ revalidate: 300 });
    expect(opciones.signal).toBeInstanceOf(AbortSignal);
  });

  it("una respuesta de error vuelve null", async () => {
    fetchFalso.mockResolvedValue(new Response("{}", { status: 503 }));

    expect(await pedirAlCatalogo("/api/catalogo/genres/?tipo=tv", "en")).toBeNull();
  });

  it("un corte o una demora vuelve null en vez de romper la página", async () => {
    fetchFalso.mockRejectedValue(new DOMException("timeout", "TimeoutError"));

    expect(await pedirAlCatalogo("/api/catalogo/genres/?tipo=tv", "en")).toBeNull();
  });
});

describe("pedirVarias", () => {
  it("devuelve solo las rutas que llegaron", async () => {
    fetchFalso.mockImplementation(async (url: string) =>
      url.includes("genres")
        ? new Response("{}", { status: 502 })
        : new Response(JSON.stringify({ results: [1] }))
    );

    const datos = await pedirVarias(
      ["/api/catalogo/trending/?media_type=all", "/api/catalogo/genres/?tipo=movie"],
      "en"
    );

    expect(datos).toEqual({ "/api/catalogo/trending/?media_type=all": { results: [1] } });
  });
});
