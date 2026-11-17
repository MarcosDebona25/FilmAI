import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "@/lib/api";
import { useCursorList } from "@/lib/use-cursor-list";

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));

type Pagina = { results: number[]; next: string | null };
type Datos = { items: number[]; next: string | null };

const pagina = (results: number[], next: string | null): Pagina => ({ results, next });

function usar(primera = "/api/x/", cuenta: number | null = 1) {
  return renderHook(
    (props: { primera: string; cuenta: number | null }) =>
      useCursorList<Pagina, Datos>({
        cuenta: props.cuenta,
        primera: props.primera,
        rutaSiguiente: (next) => `/api/x/?cursor=${next}`,
        inicial: (p) => ({ items: p.results, next: p.next }),
        combinar: (actual, p) => ({ items: [...actual.items, ...p.results], next: p.next }),
      }),
    { initialProps: { primera, cuenta } }
  );
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset();
});

describe("useCursorList", () => {
  it("sin cuenta no pide nada", () => {
    const { result } = usar("/api/x/", null);
    expect(apiFetch).not.toHaveBeenCalled();
    expect(result.current.datos).toBeNull();
    expect(result.current.estado).toBe("cargando");
  });

  it("pide la primera página y queda lista", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(pagina([1, 2], "c2"));
    const { result } = usar();
    await waitFor(() => expect(result.current.estado).toBe("listo"));
    expect(apiFetch).toHaveBeenCalledWith("/api/x/");
    expect(result.current.datos?.items).toEqual([1, 2]);
    expect(result.current.puedeSeguir).toBe(true);
  });

  it("cargarMas suma la página siguiente con su cursor", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(pagina([1], "c2"));
    const { result } = usar();
    await waitFor(() => expect(result.current.estado).toBe("listo"));
    vi.mocked(apiFetch).mockResolvedValueOnce(pagina([2], null));
    act(() => result.current.cargarMas());
    expect(result.current.mas).toBe("cargando");
    await waitFor(() => expect(result.current.mas).toBe("quieto"));
    expect(apiFetch).toHaveBeenLastCalledWith("/api/x/?cursor=c2");
    expect(result.current.datos?.items).toEqual([1, 2]);
    expect(result.current.puedeSeguir).toBe(false);
  });

  it("si falla la siguiente página queda en error y se reintenta", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(pagina([1], "c2"));
    const { result } = usar();
    await waitFor(() => expect(result.current.estado).toBe("listo"));
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("falla"));
    act(() => result.current.cargarMas());
    await waitFor(() => expect(result.current.mas).toBe("error"));
    expect(result.current.puedeSeguir).toBe(false);
    vi.mocked(apiFetch).mockResolvedValueOnce(pagina([2], null));
    act(() => result.current.reintentarMas());
    await waitFor(() => expect(result.current.datos?.items).toEqual([1, 2]));
  });

  it("si falla la primera página queda en error y reintentar la pide de nuevo", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("falla"));
    const { result } = usar();
    await waitFor(() => expect(result.current.estado).toBe("error"));
    vi.mocked(apiFetch).mockResolvedValueOnce(pagina([1], null));
    act(() => result.current.reintentar());
    await waitFor(() => expect(result.current.estado).toBe("listo"));
    expect(result.current.intento).toBe(1);
  });

  it("una consulta nueva descarta la respuesta vieja", async () => {
    let soltarVieja: (valor: Pagina) => void = () => {};
    vi.mocked(apiFetch).mockReturnValueOnce(new Promise((resolver) => (soltarVieja = resolver)));
    const { result, rerender } = usar("/api/x/?q=a");
    vi.mocked(apiFetch).mockResolvedValueOnce(pagina([9], null));
    rerender({ primera: "/api/x/?q=b", cuenta: 1 });
    await waitFor(() => expect(result.current.datos?.items).toEqual([9]));
    await act(async () => soltarVieja(pagina([1], null)));
    expect(result.current.datos?.items).toEqual([9]);
  });

  it("cargarMas no hace nada sin cursor", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(pagina([1], null));
    const { result } = usar();
    await waitFor(() => expect(result.current.estado).toBe("listo"));
    act(() => result.current.cargarMas());
    expect(apiFetch).toHaveBeenCalledTimes(1);
  });
});
