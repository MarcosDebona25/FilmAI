import type { ReactNode } from "react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import { limpiarCacheCatalogo, useCatalog, useCatalogPaginas } from "@/lib/use-catalog";
import { renderHook as renderHookBase, waitFor } from "./render";

const api = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return { ...real, apiFetch: api.fetch };
});

/** Los hooks leen el idioma de next-intl (la caché es por idioma). */
const idioma = { actual: "es" as "es" | "en" };
function ConIdioma({ children }: { children: ReactNode }) {
  return (
    <NextIntlClientProvider locale={idioma.actual} messages={{}}>
      {children}
    </NextIntlClientProvider>
  );
}
const renderHook: typeof renderHookBase = (hook, opciones) =>
  renderHookBase(hook, { wrapper: ConIdioma, ...opciones });

afterEach(() => {
  idioma.actual = "es";
  api.fetch.mockReset();
  limpiarCacheCatalogo();
});

describe("useCatalogPaginas", () => {
  it("junta las páginas en orden aunque lleguen desordenadas", async () => {
    let segunda: (valor: string) => void = () => undefined;
    api.fetch.mockImplementation((path: string) =>
      path === "/p?page=2" ? new Promise((resolver) => (segunda = resolver)) : Promise.resolve(path)
    );
    const { result } = renderHook(() => useCatalogPaginas<string>(["/p?page=1", "/p?page=2"]));

    await waitFor(() => expect(result.current.paginas).toEqual(["/p?page=1"]));
    expect(result.current.cargandoMas).toBe(true);
    segunda("/p?page=2");

    await waitFor(() => expect(result.current.paginas).toEqual(["/p?page=1", "/p?page=2"]));
    expect(result.current.cargandoMas).toBe(false);
  });

  it("no vuelve a pedir lo que ya está en la caché, ni lo de useCatalog", async () => {
    api.fetch.mockImplementation((path: string) => Promise.resolve(path));
    const previa = renderHook(() => useCatalog<string>("/p?page=1"));
    await waitFor(() => expect(previa.result.current.status).toBe("ok"));

    const { result } = renderHook(() => useCatalogPaginas<string>(["/p?page=1", "/p?page=2"]));

    await waitFor(() => expect(result.current.paginas).toHaveLength(2));
    expect(api.fetch.mock.calls.map(([path]) => path)).toEqual(["/p?page=1", "/p?page=2"]);
  });

  it("si una página falla avisa, y otro intento la vuelve a pedir", async () => {
    api.fetch.mockRejectedValueOnce(new Error("caída"));
    const { result, rerender } = renderHook(
      ({ intento }) => useCatalogPaginas<string>(["/p?page=1"], intento),
      { initialProps: { intento: 0 } }
    );
    await waitFor(() => expect(result.current.status).toBe("error"));

    api.fetch.mockResolvedValueOnce("ok");
    rerender({ intento: 1 });

    await waitFor(() => expect(result.current.paginas).toEqual(["ok"]));
    expect(result.current.status).toBe("ok");
  });
});

describe("caché por idioma", () => {
  it("al cambiar de idioma vuelve a pedir, y al volver usa lo guardado", async () => {
    // La API traduce según Accept-Language: «Animales» en es, «Animals» en en.
    api.fetch.mockImplementation(() =>
      Promise.resolve(idioma.actual === "es" ? "Animales" : "Animals")
    );
    const { result, rerender } = renderHook(() => useCatalog<string>("/trending"));
    await waitFor(() => expect(result.current.data).toBe("Animales"));

    idioma.actual = "en";
    rerender();
    await waitFor(() => expect(result.current.data).toBe("Animals"));

    idioma.actual = "es";
    rerender();
    await waitFor(() => expect(result.current.data).toBe("Animales"));
    expect(api.fetch).toHaveBeenCalledTimes(2);
  });

  it("las páginas de Buscar también se guardan por idioma", async () => {
    api.fetch.mockImplementation((path: string) => Promise.resolve(`${idioma.actual} ${path}`));
    const { result, rerender } = renderHook(() => useCatalogPaginas<string>(["/p?page=1"]));
    await waitFor(() => expect(result.current.paginas).toEqual(["es /p?page=1"]));

    idioma.actual = "en";
    rerender();
    await waitFor(() => expect(result.current.paginas).toEqual(["en /p?page=1"]));
  });
});
