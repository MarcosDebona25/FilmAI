import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SearchView } from "@/components/features/SearchView";
import type { TmdbItem } from "@/lib/catalog";
import { limpiarCacheCatalogo } from "@/lib/use-catalog";
import { reacher, svu } from "./catalog-fixtures";
import { act, fireEvent, render, screen, waitFor, within } from "./render";

/** Recortes reales de `search/movie?query=dune` del 14/10/2026. */
const DUNE_2: TmdbItem = {
  id: 693134,
  media_type: "movie",
  title: "Dune: Part Two",
  release_date: "2024-02-27",
  vote_average: 8.1,
  genre_ids: [878, 12],
};
const DUNE_3: TmdbItem = {
  id: 1170608,
  media_type: "movie",
  title: "Dune: Part Three",
  release_date: "2026-12-15",
  vote_average: 0,
  genre_ids: [878, 12],
};
/** `genre/tv/list` en en-US: TMDB no traduce Kids (tampoco en es-MX). */
const GENEROS = [
  { id: 18, name: "Drama" },
  { id: 878, name: "Science Fiction" },
  { id: 10762, name: "Kids" },
];

const estado = vi.hoisted(() => ({
  params: new URLSearchParams(),
  respuesta: null as null | Record<string, unknown>,
  falla: false,
  /** Si está, la página N responde `porPagina[N - 1]`. */
  porPagina: null as null | Record<string, unknown>[],
  fallaPagina: null as null | number,
  pedidos: [] as string[],
}));
const router = vi.hoisted(() => ({ push: vi.fn(), back: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => estado.params,
}));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...real,
    apiFetch: vi.fn(async (path: string) => {
      estado.pedidos.push(path);
      if (path.startsWith("/api/catalogo/genres/")) return { genres: GENEROS };
      const pagina = Number(new URL(path, "http://x").searchParams.get("page"));
      if (estado.falla || estado.fallaPagina === pagina)
        throw new real.ApiError(502, { code: "upstream_error", params: {}, errors: [] });
      return structuredClone(estado.porPagina ? estado.porPagina[pagina - 1] : estado.respuesta);
    }),
  };
});

const pagina = (results: TmdbItem[], extra = {}) => ({
  page: 1,
  total_pages: 1,
  total_results: results.length,
  results,
  ...extra,
});

let reemplazos: string[];
/** `IntersectionObserver` simulado: jsdom no lo implementa. */
const observadores: { acercar: () => void }[] = [];
beforeEach(() => {
  estado.params = new URLSearchParams();
  estado.respuesta = pagina([DUNE_2, reacher, DUNE_3, svu], { total_pages: 3, total_results: 57 });
  estado.falla = false;
  estado.porPagina = null;
  estado.fallaPagina = null;
  estado.pedidos = [];
  observadores.length = 0;
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(
        private callback: IntersectionObserverCallback,
        opciones?: IntersectionObserverInit
      ) {
        // `next/link` también observa (precarga de enlaces): solo interesa el
        // de la grilla, que anticipa 600 px.
        if (opciones?.rootMargin?.includes("600px")) observadores.push(this);
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
  reemplazos = [];
  limpiarCacheCatalogo();
  vi.spyOn(window.history, "replaceState").mockImplementation((_, __, url) => {
    reemplazos.push(String(url));
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
  window.sessionStorage.clear();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

const pedidosDeBusqueda = () => estado.pedidos.filter((p) => p.startsWith("/api/catalogo/browse/"));

describe("Buscar", () => {
  it("sin nada elegido pide los populares de todo y no muestra contador", async () => {
    render(<SearchView />, { locale: "en" });

    expect(await screen.findByText("Dune: Part Two")).toBeInTheDocument();
    expect(pedidosDeBusqueda()).toEqual(["/api/catalogo/browse/?tipo=all&page=1"]);
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("con texto muestra el contador y cada tarjeta lleva a la ficha desde Search", async () => {
    estado.params = new URLSearchParams("q=dune");
    render(<SearchView />, { locale: "en" });

    expect(await screen.findByRole("status")).toHaveTextContent("57 results for “dune”");
    expect(screen.getByRole("link", { name: /Dune: Part Two/ })).toHaveAttribute(
      "href",
      "/movie/693134?from=search"
    );
    // Sin votos en TMDB, la tarjeta lo dice en vez de mostrar «★ 0».
    expect(
      within(screen.getByRole("link", { name: /Dune: Part Three/ })).getByText("No ratings")
    ).toBeInTheDocument();
  });

  it("escribir espera 350 ms antes de buscar y vuelve a la página 1", async () => {
    estado.params = new URLSearchParams("page=2");
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<SearchView />, { locale: "en" });

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "dun" } });
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "dune" } });
    act(() => vi.advanceTimersByTime(300));
    expect(reemplazos).toEqual([]);
    act(() => vi.advanceTimersByTime(60));

    expect(reemplazos).toEqual(["/search?q=dune"]);
  });

  it("Enter busca enseguida", () => {
    render(<SearchView />, { locale: "en" });

    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "ocean's" } });
    fireEvent.submit(screen.getByRole("searchbox"));

    expect(reemplazos).toEqual(["/search?q=ocean%27s"]);
  });

  it("los filtros van a la URL y los géneros sin traducir de TMDB llevan el nuestro", async () => {
    render(<SearchView />, { locale: "es" });

    const genero = screen.getByRole("combobox", { name: "Género" });
    expect(await within(genero).findByRole("option", { name: "Infantil" })).toBeInTheDocument();
    fireEvent.change(genero, { target: { value: "878" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Calificación" }), {
      target: { value: "lt5" },
    });

    expect(reemplazos).toEqual(["/search?genre=878", "/search?rating=lt5"]);
  });

  it("cambiar el tipo conserva un género común y descarta los que cambian de id", () => {
    estado.params = new URLSearchParams("genre=18");
    const { unmount } = render(<SearchView />, { locale: "en" });
    fireEvent.click(screen.getByRole("button", { name: "TV shows" }));
    unmount();

    estado.params = new URLSearchParams("genre=878");
    render(<SearchView />, { locale: "en" });
    fireEvent.click(screen.getByRole("button", { name: "TV shows" }));

    expect(reemplazos).toEqual(["/search?type=tv&genre=18", "/search?type=tv"]);
  });

  it("al acercarse el final de la grilla pide la página siguiente", async () => {
    estado.params = new URLSearchParams("q=dune");
    window.history.pushState(null, "", "/search?q=dune");
    render(<SearchView />, { locale: "en" });
    await screen.findByText("Dune: Part Two");

    act(() => observadores[0].acercar());

    expect(reemplazos).toEqual(["/search?q=dune&page=2"]);
  });

  it("un aviso que llega tarde no pisa un filtro elegido mientras tanto", async () => {
    // Carrera que cazó el CI: con pocos resultados el aviso de «llegó al final»
    // salía con la búsqueda vieja y borraba la nota recién elegida.
    estado.params = new URLSearchParams("q=dune");
    window.history.pushState(null, "", "/search?q=dune");
    render(<SearchView />, { locale: "en" });
    await screen.findByText("Dune: Part Two");

    window.history.pushState(null, "", "/search?q=dune&rating=8");
    act(() => observadores[0].acercar());

    expect(reemplazos).toEqual([]);
  });

  it("con page=2 junta las dos páginas, sin repetidos, y deja de pedir en la última", async () => {
    estado.params = new URLSearchParams("q=dune&page=2");
    // Reacher llega en las dos páginas: la popularidad puede cambiar entre pedidos.
    estado.porPagina = [
      pagina([DUNE_2, reacher], { total_pages: 2, total_results: 3 }),
      pagina([reacher, svu], { total_pages: 2, total_results: 3 }),
    ];
    render(<SearchView />, { locale: "en" });

    expect(await screen.findByText("Law & Order: Special Victims Unit")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Reacher/ })).toHaveLength(1);
    expect(screen.getByText("Dune: Part Two")).toBeInTheDocument();
    expect(observadores).toHaveLength(0);
  });

  it("abrir una ficha guarda el scroll y al volver la grilla vuelve ahí", async () => {
    estado.params = new URLSearchParams("q=dune&page=2");
    estado.porPagina = [
      pagina([DUNE_2], { total_pages: 2, total_results: 2 }),
      pagina([svu], { total_pages: 2, total_results: 2 }),
    ];
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cuadro) => {
      cuadro(0);
      return 0;
    });
    const { unmount } = render(<SearchView />, { locale: "en" });
    window.scrollY = 1800;
    // En el `<li>` y no en el enlace: el guardado escucha en la grilla y así
    // jsdom no intenta navegar.
    fireEvent.click((await screen.findByText("Law & Order: Special Victims Unit")).closest("li")!);
    unmount();

    render(<SearchView />, { locale: "en" });

    await waitFor(() => expect(window.scrollTo).toHaveBeenCalledWith({ top: 1800 }));
  });

  it("si falla una página siguiente conserva lo cargado y ofrece reintentar", async () => {
    estado.params = new URLSearchParams("q=dune&page=2");
    estado.porPagina = [
      pagina([DUNE_2], { total_pages: 3, total_results: 3 }),
      pagina([svu], { total_pages: 3, total_results: 3 }),
    ];
    estado.fallaPagina = 2;
    render(<SearchView />, { locale: "en" });

    expect(await screen.findByRole("alert")).toHaveTextContent("The catalog couldn’t respond.");
    expect(screen.getByText("Dune: Part Two")).toBeInTheDocument();
    estado.fallaPagina = null;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Law & Order: Special Victims Unit")).toBeInTheDocument();
  });

  it("sin resultados ofrece limpiar los filtros", async () => {
    estado.params = new URLSearchParams("q=dnue&genre=18");
    estado.respuesta = pagina([]);
    render(<SearchView />, { locale: "en" });

    expect(await screen.findByText("Nothing for “dnue”")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));

    expect(reemplazos).toEqual(["/search?q=dnue"]);
  });

  it("si la API falla avisa y Reintentar vuelve a pedir", async () => {
    estado.falla = true;
    render(<SearchView />, { locale: "en" });

    expect(await screen.findByRole("alert")).toHaveTextContent("The catalog couldn’t respond.");
    estado.falla = false;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Dune: Part Two")).toBeInTheDocument();
    expect(pedidosDeBusqueda()).toHaveLength(2);
  });

  it("Escape vuelve atrás si se llegó desde la app, y al Inicio si se abrió directo", () => {
    const navegacion = vi.spyOn(performance, "getEntriesByType");
    render(<SearchView />, { locale: "en" });

    navegacion.mockReturnValue([{ name: "http://localhost/home" } as PerformanceEntry]);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(router.back).toHaveBeenCalledTimes(1);

    navegacion.mockReturnValue([{ name: "http://localhost/search?q=dune" } as PerformanceEntry]);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(router.push).toHaveBeenCalledWith("/home");
  });

  it("guarda la búsqueda para que la miga de la ficha vuelva a ella", () => {
    estado.params = new URLSearchParams("q=dune&genre=878");
    render(<SearchView />, { locale: "en" });

    expect(window.sessionStorage.getItem("filmai:ultima-busqueda")).toBe(
      "/search?q=dune&genre=878"
    );
  });

  it("en celular, «Filters» dice cuántos hay activos y abre la hoja", async () => {
    estado.params = new URLSearchParams("genre=18&year=2020");
    render(<SearchView />, { locale: "en" });

    fireEvent.click(screen.getByRole("button", { name: "Filters, 2 active" }));
    const hoja = screen.getByRole("dialog", { name: "Filters" });
    expect(await within(hoja).findByRole("option", { name: "Kids" })).toBeInTheDocument();
    expect(within(hoja).getByRole("combobox", { name: "Year" })).toHaveValue("2020");

    fireEvent.click(within(hoja).getByRole("button", { name: "Below 5" }));
    fireEvent.click(within(hoja).getByRole("button", { name: "Clear" }));
    fireEvent.click(within(hoja).getByRole("button", { name: "Show results" }));

    expect(reemplazos).toEqual(["/search?genre=18&year=2020&rating=lt5", "/search"]);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("con la hoja abierta, Escape la cierra a ella y no sale de Buscar", () => {
    render(<SearchView />, { locale: "en" });
    fireEvent.click(screen.getByRole("button", { name: "Filters" }));

    fireEvent.keyDown(document, { key: "Escape" });

    expect(router.back).not.toHaveBeenCalled();
    expect(router.push).not.toHaveBeenCalled();
  });

  it("el campo no deja escribir más de 50 caracteres", () => {
    render(<SearchView />, { locale: "en" });

    expect(screen.getByRole("searchbox")).toHaveAttribute("maxLength", "50");
  });
});
