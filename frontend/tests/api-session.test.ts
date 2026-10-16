import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, SESION_VENCIDA, apiFetch } from "@/lib/api";

const respuesta = (status: number, json: unknown = {}) =>
  new Response(status === 204 ? null : JSON.stringify(json), { status });

describe("apiFetch renueva la sesión", () => {
  let pedidos: string[];
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    pedidos = [];
    document.cookie = "csrftoken=abc";
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "csrftoken=; Max-Age=0";
  });

  /** `fetch` simulado: `rutas` dice qué contesta cada ruta, en orden. */
  function backend(rutas: Record<string, number[]>) {
    fetchMock.mockImplementation(async (url: string) => {
      const ruta = new URL(url).pathname;
      pedidos.push(ruta);
      const estado = rutas[ruta]?.shift() ?? 200;
      return respuesta(estado, { ruta });
    });
  }

  it("con el access vencido renueva y repite el pedido sin que se note", async () => {
    backend({ "/api/profile/": [401, 200], "/api/auth/token/refresh/": [200] });
    await expect(apiFetch("/api/profile/")).resolves.toEqual({ ruta: "/api/profile/" });
    expect(pedidos).toEqual(["/api/profile/", "/api/auth/token/refresh/", "/api/profile/"]);
    // La renovación es una mutación: lleva el token CSRF.
    const [, opciones] = fetchMock.mock.calls[1];
    expect(opciones).toMatchObject({ method: "POST", credentials: "include" });
    expect(opciones.headers["X-CSRFToken"]).toBe("abc");
  });

  it("varios 401 a la vez comparten una sola renovación", async () => {
    backend({
      "/api/lists/": [401, 200],
      "/api/profile/": [401, 200],
      "/api/auth/token/refresh/": [200],
    });
    await Promise.all([apiFetch("/api/lists/"), apiFetch("/api/profile/")]);
    expect(pedidos.filter((ruta) => ruta === "/api/auth/token/refresh/")).toHaveLength(1);
  });

  it("si no se puede renovar, avisa que venció y devuelve el 401", async () => {
    backend({ "/api/profile/": [401, 401], "/api/auth/token/refresh/": [401] });
    const aviso = vi.fn();
    window.addEventListener(SESION_VENCIDA, aviso);
    await expect(apiFetch("/api/profile/")).rejects.toMatchObject({ status: 401 });
    window.removeEventListener(SESION_VENCIDA, aviso);
    expect(aviso).toHaveBeenCalledOnce();
  });

  it("las rutas de auth no intentan renovar", async () => {
    backend({ "/api/auth/login/": [401] });
    await expect(
      apiFetch("/api/auth/login/", { method: "POST", body: { usuario: "x" } })
    ).rejects.toBeInstanceOf(ApiError);
    expect(pedidos).toEqual(["/api/auth/login/"]);
  });
});

describe("apiFetch sin conexión", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("convierte el fallo del navegador en un error entendible", async () => {
    // Sin red, `fetch` rechaza con «Failed to fetch» en inglés, y ese texto
    // llegaba tal cual a la pantalla (Q-03, 16/10/2026).
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const error = await apiFetch("/api/catalogo/trending/").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 0, code: "network_error" });
    expect((error as ApiError).message).not.toContain("Failed to fetch");
    expect((error as ApiError).message).toMatch(/conectarnos|connect/);
  });
});
