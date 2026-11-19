import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SimilarTitles } from "@/components/features/title/SimilarTitles";
import { render, screen, waitFor, within } from "./render";

const estado = vi.hoisted(() => ({
  respuesta: { results: [] as Record<string, unknown>[] },
  falla: false,
  colgado: false,
  pedidos: [] as string[],
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...real,
    apiFetch: vi.fn(async (path: string) => {
      estado.pedidos.push(path);
      if (estado.colgado) return new Promise(() => {});
      if (estado.falla)
        throw new real.ApiError(502, { code: "upstream_error", params: {}, errors: [] });
      return structuredClone(estado.respuesta);
    }),
  };
});

const parecido = (indice: number, extra: Record<string, unknown> = {}) => ({
  id_tmdb: 9000 + indice,
  tipo: "movie",
  titulo: `Similar ${indice}`,
  poster: `/similar-${indice}.jpg`,
  anio: 2000 + indice,
  calificacion_promedio: 7.6,
  origen: "catalogo",
  ...extra,
});

/** `IntersectionObserver` simulado: jsdom no lo implementa. */
const observadores: { margen?: string; acercar: () => void }[] = [];
/** La fila llega a 400 px del viewport. */
const acercar = () => act(() => observadores.forEach((observador) => observador.acercar()));

beforeEach(() => {
  estado.respuesta = { results: Array.from({ length: 20 }, (_, i) => parecido(i + 1)) };
  estado.falla = false;
  estado.colgado = false;
  estado.pedidos = [];
  observadores.length = 0;
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      margen?: string;
      constructor(
        private callback: IntersectionObserverCallback,
        opciones?: IntersectionObserverInit
      ) {
        this.margen = opciones?.rootMargin;
        // `next/link` también observa (precarga de enlaces): solo interesa el
        // de la fila, que anticipa 400 px.
        if (this.margen?.includes("400px")) observadores.push(this);
      }
      observe() {}
      unobserve() {}
      takeRecords() {
        return [];
      }
      disconnect() {
        const i = observadores.indexOf(this);
        if (i >= 0) observadores.splice(i, 1);
      }
      acercar() {
        this.callback(
          [{ isIntersecting: true } as IntersectionObserverEntry],
          this as unknown as IntersectionObserver
        );
      }
    }
  );
});

const dibujar = (from?: string) =>
  render(<SimilarTitles tipo="movie" id={157336} titulo="Interstellar" from={from} />, {
    locale: "en",
  });
const fila = () => screen.queryByRole("region", { name: "More like Interstellar" });

describe("«More like {title}» en la ficha", () => {
  it("no pide nada ni dibuja la fila hasta estar a 400 px del viewport", () => {
    dibujar();

    expect(observadores).toHaveLength(1);
    expect(estado.pedidos).toEqual([]);
    expect(fila()).toBeNull();
    expect(screen.queryByRole("heading")).toBeNull();
  });

  it("al acercarse pide los parecidos y muestra las 20 tarjetas con su tipo", async () => {
    estado.respuesta.results[6] = parecido(7, { tipo: "tv", titulo: "Foundation" });
    dibujar();
    acercar();

    await waitFor(() => expect(within(fila()!).getAllByRole("listitem")).toHaveLength(20));
    expect(estado.pedidos).toEqual(["/api/catalogo/movie/157336/similar/"]);
    expect(within(fila()!).getByRole("heading", { level: 2 })).toHaveTextContent(
      "More like Interstellar"
    );
    const pelicula = within(fila()!).getByRole("link", { name: /Similar 1\b/ });
    expect(pelicula).toHaveAttribute("href", "/movie/9001");
    expect(pelicula).toHaveTextContent("Movie");
    const serie = within(fila()!).getByRole("link", { name: /Foundation/ });
    expect(serie).toHaveAttribute("href", "/tv/9007");
    expect(serie).toHaveTextContent("TV show");
  });

  it("las tarjetas conservan el origen de la ficha actual", async () => {
    dibujar("list-4");
    acercar();

    await waitFor(() => expect(fila()).not.toBeNull());
    expect(within(fila()!).getByRole("link", { name: /Similar 1\b/ })).toHaveAttribute(
      "href",
      "/movie/9001?from=list-4"
    );
  });

  it("mientras carga muestra los esqueletos de la fila del Inicio", () => {
    estado.colgado = true;
    dibujar();
    acercar();

    expect(fila()).toHaveAttribute("aria-busy", "true");
    expect(fila()!.querySelectorAll("[data-skeleton]")).toHaveLength(7);
  });

  it("sin resultados no dibuja nada: ni título ni mensaje", async () => {
    estado.respuesta = { results: [] };
    const { container } = dibujar();
    acercar();

    await waitFor(() => expect(container).toBeEmptyDOMElement());
    expect(estado.pedidos).toHaveLength(1);
  });

  it("si el pedido falla no dibuja nada: ni título ni mensaje de error", async () => {
    estado.falla = true;
    const { container } = dibujar();
    acercar();

    await waitFor(() => expect(container).toBeEmptyDOMElement());
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
