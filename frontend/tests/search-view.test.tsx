import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CAMPO_BUSQUEDA } from "@/components/campo-busqueda";
import { SearchView } from "@/components/features/SearchView";
import type { TmdbItem } from "@/lib/catalog";
import en from "@/messages/en/common.json";
import { limpiarCacheSugerencias } from "@/lib/sugerencias";
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

/** Recortes con la forma de `suggest/` (14/11/2026): una persona y una película. */
const RYAN = {
  media_type: "person",
  id: 30614,
  name: "Ryan Gosling",
  rol: "actor",
  gender: 2,
  profile_path: "/r.jpg",
};
const DRIVE = {
  media_type: "movie",
  id: 64690,
  title: "Drive",
  release_date: "2011-09-15",
  poster_path: null,
  vote_average: 7.6,
};

const estado = vi.hoisted(() => ({
  params: new URLSearchParams(),
  respuesta: null as null | Record<string, unknown>,
  falla: false,
  /** Si está, la página N responde `porPagina[N - 1]`. */
  porPagina: null as null | Record<string, unknown>[],
  fallaPagina: null as null | number,
  /** Código con el que `explore/` responde 404 (Not Found), p. ej. `person_not_found`. */
  noEncontrado: null as null | string,
  pedidos: [] as string[],
  /** Lo que contesta `suggest/` (el mismo pedido que usa la lupa de la navbar). */
  sugerencias: { results: [] } as { results: Record<string, unknown>[] },
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
      if (path.startsWith("/api/catalogo/suggest/")) return structuredClone(estado.sugerencias);
      const pagina = Number(new URL(path, "http://x").searchParams.get("page"));
      if (estado.noEncontrado)
        throw new real.ApiError(404, { code: estado.noEncontrado, params: {}, errors: [] });
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
  estado.noEncontrado = null;
  estado.pedidos = [];
  estado.sugerencias = { results: [RYAN, DRIVE] };
  limpiarCacheSugerencias();
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

/** El campo de texto: Género, Año y Nota (`<select>`) también son «combobox». */
const campo = () => screen.getByRole("combobox", { name: en.common.search.placeholder });
const pedidosDeBusqueda = () =>
  estado.pedidos.filter((p) => p.startsWith("/api/catalogo/explore/"));

describe("Buscar", () => {
  it("sin nada elegido pide los populares de todo y no muestra contador", async () => {
    render(<SearchView />, { locale: "en" });

    expect(await screen.findByText("Dune: Part Two")).toBeInTheDocument();
    expect(pedidosDeBusqueda()).toEqual(["/api/catalogo/explore/?tipo=all&page=1"]);
    // La región viva existe, pero vacía: no hay contador.
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
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

    fireEvent.change(campo(), { target: { value: "dun" } });
    fireEvent.change(campo(), { target: { value: "dune" } });
    act(() => vi.advanceTimersByTime(300));
    expect(reemplazos).toEqual([]);
    act(() => vi.advanceTimersByTime(60));

    expect(reemplazos).toEqual(["/search?q=dune"]);
  });

  it("el campo copia el estilo del buscador de la lupa de la navbar", () => {
    render(<SearchView />, { locale: "en" });

    // Las mismas clases que usa `NavbarSearch` (colores, borde, radio, altura, foco).
    expect(campo().className).toBe(CAMPO_BUSQUEDA.input);
    expect(campo().parentElement?.className).toBe(CAMPO_BUSQUEDA.pildora);
    expect(campo()).toHaveAttribute("placeholder", en.common.search.placeholder);

    fireEvent.change(campo(), { target: { value: "dune" } });
    const limpiar = screen.getByRole("button", { name: en.search.input.clearLabel });
    expect(limpiar.className).toBe(CAMPO_BUSQUEDA.limpiar);
  });

  it("Enter busca enseguida", () => {
    render(<SearchView />, { locale: "en" });

    fireEvent.change(campo(), { target: { value: "ocean's" } });
    fireEvent.submit(campo());

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

  it("el año ofrece «A estrenar», años sueltos y décadas antes de 1990", () => {
    render(<SearchView />, { locale: "es" });

    const anio = screen.getByRole("combobox", { name: "Año" });
    const opciones = within(anio).getAllByRole("option");
    expect(opciones.slice(0, 2).map((opcion) => opcion.textContent)).toEqual([
      "Cualquiera",
      "A estrenar",
    ]);
    expect(opciones[2]).toHaveTextContent(String(new Date().getFullYear()));
    expect(opciones.at(-1)).toHaveTextContent("Década de 1900");
    fireEvent.change(anio, { target: { value: "upcoming" } });

    expect(reemplazos).toEqual(["/search?year=upcoming"]);
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
    // El observador se registra un instante después de pintar la grilla: en un
    // CI lento el texto ya está y el observador todavía no.
    await waitFor(() => expect(observadores).toHaveLength(1));

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
    await waitFor(() => expect(observadores).toHaveLength(1));

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
    // Hay dos: el de la fila de filtros y el del estado vacío.
    const botones = screen.getAllByRole("button", { name: "Clear filters" });
    expect(botones).toHaveLength(2);
    fireEvent.click(botones[1]);

    expect(reemplazos).toEqual(["/search?q=dnue"]);
  });

  it("«Clear filters» a la derecha de los filtros solo aparece con filtros activos", async () => {
    render(<SearchView />, { locale: "en" });
    await screen.findByText("Dune: Part Two");
    expect(screen.queryByRole("button", { name: "Clear filters" })).not.toBeInTheDocument();
  });

  it("«Clear filters» de la fila de filtros quita género, año y nota, y deja el texto", async () => {
    estado.params = new URLSearchParams("q=dune&genre=18&year=2024&rating=8");
    render(<SearchView />, { locale: "en" });
    await screen.findByText("Dune: Part Two");

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));

    expect(reemplazos).toEqual(["/search?q=dune"]);
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

    expect(campo()).toHaveAttribute("maxLength", "50");
  });
});

describe("Buscar con una persona", () => {
  /** Recorte de `explore/?persona=525&rol=director` (el backend manda `persona`). */
  const NOLAN = {
    id: 525,
    name: "Christopher Nolan",
    rol: "director",
    gender: 2,
    profile_path: "/x.jpg",
  };
  const DE_NOLAN = (extra = {}) => pagina([DUNE_2], { persona: NOLAN, ...extra });

  it("la manda a la API y muestra el chip con su nombre y rol, sin contar el texto", async () => {
    estado.params = new URLSearchParams("person=525&role=director");
    estado.respuesta = DE_NOLAN({ total_results: 12, total_pages: 1 });
    render(<SearchView />, { locale: "en" });

    const chip = await screen.findByText("Christopher Nolan · Director");
    expect(chip).toBeInTheDocument();
    expect(pedidosDeBusqueda()[0]).toBe(
      "/api/catalogo/explore/?tipo=all&persona=525&rol=director&page=1"
    );
    // Sin texto, el contador nombra a la persona.
    expect(screen.getByRole("status")).toHaveTextContent("12 results for “Christopher Nolan”");
  });

  it("el rol sale según el género: actriz, o solo el nombre si no hay rol", async () => {
    estado.params = new URLSearchParams("person=1&role=actor");
    estado.respuesta = pagina([DUNE_2], {
      persona: { id: 1, name: "Zendaya", rol: "actor", gender: 1, profile_path: null },
    });
    const { unmount } = render(<SearchView />, { locale: "en" });
    expect(await screen.findByText("Zendaya · Actress")).toBeInTheDocument();
    unmount();

    estado.params = new URLSearchParams("person=1");
    estado.respuesta = pagina([DUNE_2], {
      persona: { id: 1, name: "Zendaya", rol: null, gender: 1, profile_path: null },
    });
    render(<SearchView />, { locale: "en" });
    expect(await screen.findByText("Zendaya")).toBeInTheDocument();
  });

  it("la ✕ del chip quita la persona y el rol, y conserva lo demás", async () => {
    estado.params = new URLSearchParams("q=dune&type=movie&person=525&role=director");
    estado.respuesta = DE_NOLAN();
    render(<SearchView />, { locale: "en" });

    fireEvent.click(await screen.findByRole("button", { name: "Remove filter Christopher Nolan" }));

    expect(reemplazos).toEqual(["/search?q=dune&type=movie"]);
  });

  it("«Clear filters» también la quita", async () => {
    estado.params = new URLSearchParams("person=525&role=director&genre=18");
    estado.respuesta = DE_NOLAN();
    render(<SearchView />, { locale: "en" });
    await screen.findByText("Christopher Nolan · Director");

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));

    expect(reemplazos).toEqual(["/search"]);
  });

  it("cambiar el tipo conserva a la persona", async () => {
    estado.params = new URLSearchParams("person=525&role=director");
    estado.respuesta = DE_NOLAN();
    render(<SearchView />, { locale: "en" });
    await screen.findByText("Christopher Nolan · Director");

    fireEvent.click(screen.getByRole("button", { name: "Movies" }));

    expect(reemplazos).toEqual(["/search?type=movie&person=525&role=director"]);
  });

  it("una persona que TMDB no conoce muestra el aviso traducido y deja limpiar", async () => {
    estado.params = new URLSearchParams("person=99999999");
    estado.noEncontrado = "person_not_found";
    render(<SearchView />, { locale: "en" });

    expect(await screen.findByText("We couldn’t find that person.")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Clear filters" }).at(-1)!);

    expect(reemplazos).toEqual(["/search"]);
  });

  it("con persona y sin resultados dice que no hay nada con esos filtros", async () => {
    estado.params = new URLSearchParams("person=525&role=director&type=tv");
    estado.respuesta = pagina([], { persona: NOLAN });
    render(<SearchView />, { locale: "en" });

    expect(await screen.findByText("Nothing with these filters")).toBeInTheDocument();
    expect(screen.getByText("Christopher Nolan · Director")).toBeInTheDocument();
  });
});

describe("el campo de Buscar sugiere como la lupa", () => {
  const ESPERA = 250;
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));

  /** Escribe y deja pasar la espera de las sugerencias (250 ms) y su respuesta. */
  async function escribir(texto: string) {
    fireEvent.change(campo(), { target: { value: texto } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ESPERA);
    });
  }
  const pedidosDeSugerencias = () =>
    estado.pedidos.filter((p) => p.startsWith("/api/catalogo/suggest/"));

  it("agrupa personas y títulos en una lista bajo el campo, con los mismos tiempos", async () => {
    render(<SearchView />, { locale: "en" });
    fireEvent.change(campo(), { target: { value: "ryan" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ESPERA - 60);
    });
    expect(pedidosDeSugerencias()).toEqual([]);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60);
    });

    const lista = await screen.findByRole("listbox");
    expect(pedidosDeSugerencias()).toEqual(["/api/catalogo/suggest/?q=ryan"]);
    expect(within(lista).getByRole("group", { name: "People" })).toBeInTheDocument();
    expect(within(lista).getByRole("group", { name: "Titles" })).toBeInTheDocument();
    expect(within(lista).getByRole("option", { name: /Ryan Gosling.*Actor/ })).toBeInTheDocument();
    expect(within(lista).getByRole("option", { name: /Drive.*Movie · 2011/ })).toBeInTheDocument();
    // Ya se está viendo «todos los resultados»: no hay fila «See all results».
    expect(within(lista).getAllByRole("option")).toHaveLength(2);
    expect(campo()).toHaveAttribute("aria-expanded", "true");
  });

  it("con 1 carácter no pide sugerencias", async () => {
    render(<SearchView />, { locale: "en" });
    await escribir("r");

    expect(pedidosDeSugerencias()).toEqual([]);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("elegir una persona pone su filtro y borra el texto del campo y de la URL", async () => {
    estado.params = new URLSearchParams("q=ryan&type=movie");
    render(<SearchView />, { locale: "en" });
    await escribir("ryan gosl");

    fireEvent.click(await screen.findByRole("option", { name: /Ryan Gosling/ }));

    expect(reemplazos.at(-1)).toBe("/search?type=movie&person=30614&role=actor");
    expect(campo()).toHaveValue("");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    // El texto pendiente (350 ms) no pisa el filtro recién puesto.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(reemplazos).toEqual(["/search?type=movie&person=30614&role=actor"]);
  });

  it("elegir un título abre su ficha con ?from=search", async () => {
    render(<SearchView />, { locale: "en" });
    await escribir("drive");

    fireEvent.click(await screen.findByRole("option", { name: /Drive/ }));

    expect(router.push).toHaveBeenCalledWith("/movie/64690?from=search");
  });

  it("↓ y Enter eligen con el teclado; el foco no sale del campo", async () => {
    render(<SearchView />, { locale: "en" });
    await escribir("ryan");
    const entrada = campo();

    fireEvent.keyDown(entrada, { key: "ArrowDown" });
    expect(entrada).toHaveAttribute("aria-activedescendant", "sug-person-30614");
    fireEvent.keyDown(entrada, { key: "Enter" });

    expect(reemplazos.at(-1)).toBe("/search?person=30614&role=actor");
  });

  it("Enter sin opción activa cierra la lista y busca el texto en los títulos", async () => {
    render(<SearchView />, { locale: "en" });
    await escribir("nolan");
    const entrada = campo();

    fireEvent.keyDown(entrada, { key: "Enter" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    fireEvent.submit(entrada);

    expect(reemplazos).toEqual(["/search?q=nolan"]);
  });

  it("Escape cierra la lista sin salir de Buscar", async () => {
    render(<SearchView />, { locale: "en" });
    await escribir("ryan");
    await screen.findByRole("listbox");

    fireEvent.keyDown(campo(), { key: "Escape" });

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(router.back).not.toHaveBeenCalled();
    expect(router.push).not.toHaveBeenCalled();
  });

  it("anuncia cuántas sugerencias llegaron", async () => {
    render(<SearchView />, { locale: "en" });
    await escribir("ryan");

    expect(await screen.findByText("2 suggestions")).toBeInTheDocument();
  });

  it("si suggest/ falla, la lista no aparece y el campo sigue buscando", async () => {
    estado.sugerencias = null as never;
    render(<SearchView />, { locale: "en" });
    await escribir("ryan");

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});

describe("el aviso «¿Buscabas a…?»", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  const esperar = () =>
    act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

  it("aparece con «ryan gosling» y su enlace pone persona y rol y saca el texto", async () => {
    estado.params = new URLSearchParams("q=ryan+gosling&type=movie");
    render(<SearchView />, { locale: "en" });
    await esperar();

    const aviso = (await screen.findByText(/Looking for Ryan Gosling\?/)).closest("p");
    expect(aviso).toHaveTextContent(/Looking for Ryan Gosling\? See their titles\s*· Actor/);
    // Sale de la misma función: un solo pedido de sugerencias para ese texto.
    expect(estado.pedidos.filter((p) => p.startsWith("/api/catalogo/suggest/"))).toEqual([
      "/api/catalogo/suggest/?q=ryan%20gosling",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "See their titles" }));

    expect(reemplazos.at(-1)).toBe("/search?type=movie&person=30614&role=actor");
    expect(campo()).toHaveValue("");
  });

  it("compara sin acentos ni mayúsculas, con todas las palabras del texto", async () => {
    estado.params = new URLSearchParams("q=penelope+CRUZ");
    estado.sugerencias = {
      results: [
        { ...RYAN, id: 955, name: "Penélope Cruz", gender: 1, rol: "actor" },
        { ...RYAN, id: 1, name: "Penelope Spheeris", rol: "director" },
      ],
    };
    render(<SearchView />, { locale: "en" });
    await esperar();

    expect(await screen.findByText(/Looking for Penélope Cruz\?/)).toBeInTheDocument();
    expect(screen.getByText(/Actress/)).toBeInTheDocument();
  });

  it("de varias personas, solo la primera que cumple", async () => {
    estado.params = new URLSearchParams("q=ryan");
    estado.sugerencias = {
      results: [{ ...RYAN, id: 2, name: "Meg Ryan" }, RYAN],
    };
    render(<SearchView />, { locale: "en" });
    await esperar();

    expect(await screen.findByText(/Looking for Meg Ryan\?/)).toBeInTheDocument();
    expect(screen.queryByText(/Looking for Ryan Gosling/)).not.toBeInTheDocument();
  });

  it("no aparece si ninguna persona contiene todas las palabras", async () => {
    estado.params = new URLSearchParams("q=ryan+gosling");
    estado.sugerencias = { results: [{ ...RYAN, name: "Ryan Reynolds" }, DRIVE] };
    render(<SearchView />, { locale: "en" });
    await esperar();

    expect(estado.pedidos.some((p) => p.startsWith("/api/catalogo/suggest/"))).toBe(true);
    expect(screen.queryByText(/Looking for/)).not.toBeInTheDocument();
  });

  it("no aparece si ya hay una persona filtrada", async () => {
    estado.params = new URLSearchParams("q=ryan+gosling&person=30614&role=actor");
    estado.respuesta = pagina([DUNE_2], {
      persona: { id: 30614, name: "Ryan Gosling", rol: "actor", gender: 2, profile_path: null },
    });
    render(<SearchView />, { locale: "en" });
    await esperar();

    expect(await screen.findByText("Ryan Gosling · Actor")).toBeInTheDocument();
    expect(screen.queryByText(/Looking for/)).not.toBeInTheDocument();
  });

  it("no aparece sin texto", async () => {
    render(<SearchView />, { locale: "en" });
    await esperar();

    expect(screen.queryByText(/Looking for/)).not.toBeInTheDocument();
  });
});
