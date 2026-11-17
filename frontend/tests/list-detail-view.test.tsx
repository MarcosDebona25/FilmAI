import userEvent from "@testing-library/user-event";
import { Component, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { ListDetailView } from "@/components/features/lists/ListDetailView";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import type { ItemLista, ResumenLista } from "@/lib/lists";
import { render, screen, waitFor, within } from "./render";

const router = vi.hoisted(() => ({ push: vi.fn() }));
const estado = vi.hoisted(() => ({
  lista: null as unknown,
  paginas: [] as Record<string, unknown>[],
  pedidos: [] as { path: string; method: string; body?: unknown }[],
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  useRouter: () => router,
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));
vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), custom: vi.fn(), dismiss: vi.fn() },
}));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => ({ perfil: { pk: 1 }, error: null, recargar: vi.fn() }),
}));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...real,
    apiFetch: vi.fn(async (path: string, opciones: { method?: string; body?: unknown } = {}) => {
      const method = opciones.method ?? "GET";
      estado.pedidos.push({ path, method, body: opciones.body });
      if (method === "GET" && /^\/api\/lists\/\d+\/$/.test(path)) {
        if (estado.lista === "404") throw new real.ApiError(404, { code: "not_found" });
        return structuredClone(estado.lista);
      }
      if (method === "GET" && path.includes("/items/")) {
        const siguiente = path.includes("cursor=") ? estado.paginas[1] : estado.paginas[0];
        return structuredClone(siguiente);
      }
      if (method === "DELETE" && path.includes("/items/")) {
        return undefined;
      }
      if (method === "PUT") return { ...(estado.lista as object), ...(opciones.body as object) };
      return undefined;
    }),
  };
});

function lista(extra: Partial<ResumenLista> = {}): ResumenLista {
  return {
    id: 7,
    nombre: "Maratón",
    clave: null,
    tipo: "personalizada",
    cantidad_items: 3,
    cantidad_peliculas: 2,
    cantidad_series: 1,
    preview_posters: [],
    ...extra,
  };
}
function item(item_id: number, extra: Partial<ItemLista> = {}): ItemLista {
  return {
    item_id,
    fecha_agregado: "2026-10-01T00:00:00Z",
    id_tmdb: 100 + item_id,
    tipo: "movie",
    titulo: `Título ${item_id}`,
    poster: null,
    anio: 2020,
    calificacion_promedio: 8.1,
    disponible: true,
    ...extra,
  };
}
function pagina(results: ItemLista[], extra: Record<string, unknown> = {}) {
  return { next: null, total: results.length, results, ...extra };
}

const lecturas = () =>
  estado.pedidos.filter((p) => p.method === "GET" && p.path.includes("/items/")).map((p) => p.path);
const escrituras = () => estado.pedidos.filter((p) => p.method !== "GET");

let reemplazos: string[] = [];

beforeEach(() => {
  window.history.replaceState(null, "", "/lists/7");
  estado.lista = lista();
  estado.paginas = [pagina([item(1), item(2), item(3, { tipo: "tv", anio: null })])];
  estado.pedidos = [];
  reemplazos = [];
  router.push.mockClear();
  vi.mocked(toast.success).mockClear();
  // Registra cada cambio de URL y lo aplica, como lo hace el navegador.
  const original = window.history.replaceState.bind(window.history);
  vi.spyOn(window.history, "replaceState").mockImplementation((estado, titulo, url) => {
    reemplazos.push(String(url));
    original(estado, titulo, url);
  });
});
afterEach(() => vi.useRealTimers());

describe("Detalle de una lista", () => {
  it("muestra el nombre, el resumen y las tarjetas que vuelven a la lista desde la ficha", async () => {
    render(<ListDetailView id={7} />, { locale: "en" });

    expect(await screen.findByRole("heading", { level: 1, name: "Maratón" })).toBeInTheDocument();
    expect(screen.getByText("3 items · 2 movies · 1 TV show")).toBeInTheDocument();
    const enlace = await screen.findByRole("link", { name: /Título 1/ });
    expect(enlace).toHaveAttribute("href", "/movie/101?from=list-7");
    expect(screen.getByRole("link", { name: /Título 3/ })).toHaveAttribute(
      "href",
      "/tv/103?from=list-7"
    );
    expect(lecturas()).toEqual(["/api/lists/7/items/"]);
  });

  it("un título que TMDB ya no tiene es una tarjeta gris sin enlace y se puede quitar", async () => {
    const user = userEvent.setup();
    estado.paginas = [
      pagina([item(1), item(2, { disponible: false, titulo: "", anio: null, id_tmdb: 902 })]),
    ];
    render(<ListDetailView id={7} />, { locale: "en" });

    const aviso = await screen.findByText("Title no longer available");
    // No hay ficha a la que ir: ni la tarjeta ni su texto son enlaces.
    expect(aviso.closest("a")).toBeNull();
    expect(screen.queryByRole("link", { name: /902/ })).toBeNull();
    expect(screen.getByRole("link", { name: /Título 1/ })).toBeInTheDocument();
    // Quitarla funciona como siempre, y el aviso la nombra con su leyenda.
    await user.click(
      screen.getByRole("button", { name: "Remove Title no longer available from Maratón" })
    );
    expect(
      await screen.findByText("Remove “Title no longer available” from Maratón?")
    ).toBeVisible();
  });

  it("cada tarjeta muestra la fecha en que se agregó, en el formato del idioma", async () => {
    estado.paginas = [pagina([item(1, { fecha_agregado: "2026-10-18T12:00:00Z" })])];
    render(<ListDetailView id={7} />, { locale: "es" });

    expect(await screen.findByText("Agregada a esta lista el 18/10/2026")).toBeInTheDocument();
  });

  it("pide los ítems con los filtros de la URL y los traduce a la API", async () => {
    window.history.replaceState(null, "", "/lists/7?q=alien&type=tv&rating=lt5&sort=highest");
    render(<ListDetailView id={7} />, { locale: "en" });

    await screen.findByRole("heading", { level: 1, name: "Maratón" });
    await waitFor(() =>
      expect(lecturas()).toEqual(["/api/lists/7/items/?q=alien&clase=tv&nota=m5&orden=nota-desc"])
    );
    expect(screen.getByText("Showing 3 of 3 items")).toBeInTheDocument();
  });

  it("filtrar actualiza la URL sin recargar", async () => {
    const user = userEvent.setup();
    render(<ListDetailView id={7} />, { locale: "en" });
    await screen.findByRole("link", { name: /Título 1/ });

    await user.selectOptions(screen.getByLabelText(en.common.content.typeShortLabel), "tv");
    await user.selectOptions(screen.getByLabelText(en.common.rating.tmdbLabel), "8");
    await user.selectOptions(screen.getByLabelText(en.common.filters.sortLabel), "title");

    expect(reemplazos).toEqual([
      "/lists/7?type=tv",
      "/lists/7?type=tv&rating=8",
      "/lists/7?type=tv&rating=8&sort=title",
    ]);
  });

  it("espera 350 ms después de la última tecla para buscar por título", async () => {
    const user = userEvent.setup();
    render(<ListDetailView id={7} />, { locale: "en" });
    await screen.findByRole("link", { name: /Título 1/ });

    await user.type(screen.getByRole("searchbox", { name: "Search in Maratón" }), "dune");
    expect(reemplazos).toEqual([]);
    await waitFor(() => expect(reemplazos).toEqual(["/lists/7?q=dune"]));
  });

  it("sin coincidencias muestra el aviso y «Clear filters» los quita", async () => {
    window.history.replaceState(null, "", "/lists/7?type=tv");
    estado.paginas = [pagina([])];
    const user = userEvent.setup();
    render(<ListDetailView id={7} />, { locale: "en" });

    expect(await screen.findByText(en.lists.detail.filteredEmpty)).toBeInTheDocument();
    expect(screen.getByText("Showing 0 of 3 items")).toBeInTheDocument();
    const limpiar = screen.getAllByRole("button", { name: en.common.filters.clear });
    await user.click(limpiar[limpiar.length - 1]);
    expect(reemplazos.at(-1)).toBe("/lists/7");
  });

  it("una lista vacía lleva a Explorar y no muestra filtros", async () => {
    estado.lista = lista({ cantidad_items: 0, cantidad_peliculas: 0, cantidad_series: 0 });
    estado.paginas = [pagina([])];
    render(<ListDetailView id={7} />, { locale: "es" });

    expect(await screen.findByText(es.lists.detail.emptyTitle)).toBeInTheDocument();
    expect(screen.getByText(es.lists.detail.emptyDescription)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: es.common.actions.explore })).toHaveAttribute(
      "href",
      "/search"
    );
    expect(screen.queryByRole("searchbox")).toBeNull();
  });

  it("una lista vacía dice solo «0 ítems», sin el desglose por tipo", async () => {
    estado.lista = lista({ cantidad_items: 0, cantidad_peliculas: 0, cantidad_series: 0 });
    estado.paginas = [pagina([])];
    render(<ListDetailView id={7} />, { locale: "es" });

    await screen.findByText(es.lists.detail.emptyTitle);
    // Un texto para celular y otro para escritorio: ambos sin desglose.
    expect(screen.getAllByText("0 ítems")).toHaveLength(2);
    expect(screen.queryByText(/ · /)).toBeNull();
  });

  it("una lista con ítems mantiene el desglose en escritorio", async () => {
    estado.paginas = [pagina([item(1)])];
    render(<ListDetailView id={7} />, { locale: "es" });

    expect(await screen.findByText("3 ítems · 2 películas · 1 serie")).toBeInTheDocument();
  });

  it("en la lista Watching las tarjetas dicen «Empezada el» con la fecha de agregado", async () => {
    estado.lista = lista({ clave: "viendo", tipo: "predeterminada" });
    estado.paginas = [pagina([item(1)])];
    render(<ListDetailView id={7} />, { locale: "es" });

    expect(await screen.findByText("Empezada el 01/10/2026")).toBeInTheDocument();
    expect(screen.queryByText(/Agregada a esta lista/)).toBeNull();
  });

  it("carga la página siguiente por cursor con «Load more» y no repite ítems", async () => {
    estado.paginas = [
      pagina([item(1), item(2)], { next: "http://x/api/lists/7/items/?cursor=abc", total: 3 }),
      pagina([item(2), item(3)], { total: 3 }),
    ];
    const user = userEvent.setup();
    render(<ListDetailView id={7} />, { locale: "en" });
    await screen.findByRole("link", { name: /Título 1/ });

    await user.click(screen.getByRole("button", { name: en.lists.detail.loadMore }));

    await screen.findByRole("link", { name: /Título 3/ });
    expect(screen.getAllByRole("link", { name: /Título 2/ })).toHaveLength(1);
    expect(lecturas().at(-1)).toBe("/api/lists/7/items/?cursor=abc");
    expect(screen.queryByRole("button", { name: en.lists.detail.loadMore })).toBeNull();
  });

  it("quita un ítem con confirmación y actualiza los contadores", async () => {
    const user = userEvent.setup();
    render(<ListDetailView id={7} />, { locale: "en" });
    await screen.findByRole("link", { name: /Título 1/ });

    await user.click(screen.getByRole("button", { name: "Remove Título 1 from Maratón" }));
    const aviso = screen.getByRole("alertdialog", { name: "Remove “Título 1” from Maratón?" });
    await user.click(within(aviso).getByRole("button", { name: en.common.actions.remove }));

    await waitFor(() => expect(screen.queryByRole("link", { name: /Título 1/ })).toBeNull());
    expect(escrituras()).toEqual([
      { path: "/api/lists/7/items/1/", method: "DELETE", body: undefined },
    ]);
    expect(screen.getByText("2 items · 1 movie · 1 TV show")).toBeInTheDocument();
    expect(toast.success).toHaveBeenCalledWith(en.lists.feedback.itemRemoved);
  });

  it("las predeterminadas no tienen menú ⋯ y las personalizadas sí", async () => {
    estado.lista = lista({ nombre: "Favorites", clave: "favoritos", tipo: "predeterminada" });
    const primera = render(<ListDetailView id={7} />, { locale: "en" });
    await screen.findByRole("link", { name: /Título 1/ });
    expect(screen.queryByRole("button", { name: /^Actions for/ })).toBeNull();
    primera.unmount();

    estado.lista = lista();
    render(<ListDetailView id={7} />, { locale: "en" });
    expect(await screen.findByRole("button", { name: "Actions for Maratón" })).toBeInTheDocument();
  });

  it("renombra y elimina la lista desde el menú", async () => {
    const user = userEvent.setup();
    render(<ListDetailView id={7} />, { locale: "en" });
    await user.click(await screen.findByRole("button", { name: "Actions for Maratón" }));
    await user.click(screen.getByRole("button", { name: en.common.lists.rename }));
    const campo = screen.getByLabelText(en.common.lists.nameLabel);
    await user.clear(campo);
    await user.type(campo, "Semana");
    await user.click(screen.getByRole("button", { name: en.common.actions.save }));
    expect(await screen.findByRole("heading", { level: 1, name: "Semana" })).toBeInTheDocument();
    expect(toast.success).toHaveBeenCalledWith(en.lists.feedback.renamed);

    await user.click(screen.getByRole("button", { name: "Actions for Semana" }));
    await user.click(screen.getByRole("button", { name: en.common.lists.delete }));
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", {
        name: en.common.actions.delete,
      })
    );

    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/lists"));
    expect(escrituras().at(-1)).toEqual({
      path: "/api/lists/7/",
      method: "DELETE",
      body: undefined,
    });
  });

  it("una lista inexistente responde con 404 (Not Found)", async () => {
    estado.lista = "404";
    const registrar = vi.spyOn(console, "error").mockImplementation(() => undefined);
    class Limite extends Component<{ children: ReactNode }, { error: Error | null }> {
      state = { error: null as Error | null };
      static getDerivedStateFromError(error: Error) {
        return { error };
      }
      render() {
        return this.state.error ? <p>{this.state.error.message}</p> : this.props.children;
      }
    }
    render(
      <Limite>
        <ListDetailView id={7} />
      </Limite>,
      { locale: "en" }
    );

    expect(await screen.findByText("NEXT_NOT_FOUND")).toBeInTheDocument();
    registrar.mockRestore();
  });

  it("en celular, la hoja de filtros aplica al momento y cuenta los resultados", async () => {
    window.history.replaceState(null, "", "/lists/7?type=movie");
    const user = userEvent.setup();
    render(<ListDetailView id={7} />, { locale: "en" });
    await screen.findByRole("link", { name: /Título 1/ });

    await user.click(screen.getByRole("button", { name: /Filters and sort/ }));
    const hoja = screen.getByRole("dialog", { name: en.lists.detail.filtersTitle });
    await user.click(within(hoja).getByRole("button", { name: "8 or higher" }));
    expect(reemplazos.at(-1)).toBe("/lists/7?type=movie&rating=8");
    await user.click(within(hoja).getByRole("radio", { name: en.lists.detail.sortFirstAdded }));
    expect(reemplazos.at(-1)).toContain("sort=first");
    expect(within(hoja).getByRole("button", { name: "Show 3 results" })).toBeInTheDocument();
  });
});
