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
  params: new URLSearchParams(),
  lista: null as unknown,
  paginas: [] as Record<string, unknown>[],
  propia: null as unknown,
  bloquear: false,
  pedidos: [] as { path: string; method: string; body?: unknown }[],
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => estado.params,
  useRouter: () => router,
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));
vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
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
      if (method === "GET" && path.startsWith("/api/reviews/mias/")) return estado.propia;
      if (method === "DELETE" && path.includes("/items/")) {
        if (estado.bloquear && !path.includes("borrar_calificacion=true"))
          throw new real.ApiError(409, { code: "rating_blocks_removal_from_watched" });
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
  estado.params = new URLSearchParams();
  estado.lista = lista();
  estado.paginas = [pagina([item(1), item(2), item(3, { tipo: "tv", anio: null })])];
  estado.propia = null;
  estado.bloquear = false;
  estado.pedidos = [];
  reemplazos = [];
  router.push.mockClear();
  vi.mocked(toast.success).mockClear();
  vi.spyOn(window.history, "replaceState").mockImplementation((_, __, url) => {
    reemplazos.push(String(url));
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

  it("pide los ítems con los filtros de la URL y los traduce a la API", async () => {
    estado.params = new URLSearchParams("q=alien&type=tv&rating=lt5&sort=highest");
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

    // `useSearchParams` está fijo en el test: cada cambio parte de los filtros vacíos.
    expect(reemplazos).toEqual(["/lists/7?type=tv", "/lists/7?rating=8", "/lists/7?sort=title"]);
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
    estado.params = new URLSearchParams("type=tv");
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

  it("Watched con título calificado: pide confirmar el borrado de la calificación y reintenta", async () => {
    estado.lista = lista({ nombre: "Watched", clave: "vistas", tipo: "predeterminada" });
    estado.bloquear = true;
    estado.propia = { id: 5, valor: 9, texto: "Me encantó", fecha: "2026-10-02" };
    const user = userEvent.setup();
    render(<ListDetailView id={7} />, { locale: "en" });
    await screen.findByRole("link", { name: /Título 1/ });

    await user.click(screen.getByRole("button", { name: "Remove Título 1 from Watched" }));
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", {
        name: en.common.actions.remove,
      })
    );

    const confirmar = await screen.findByRole("alertdialog", {
      name: en.title.watched.removeConfirmTitle,
    });
    expect(within(confirmar).getByText(/and your review will be deleted/)).toBeInTheDocument();
    expect(within(confirmar).getByText("Me encantó")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Título 1/ })).toBeInTheDocument();

    await user.click(within(confirmar).getByRole("button", { name: en.title.watched.remove }));

    await waitFor(() => expect(screen.queryByRole("link", { name: /Título 1/ })).toBeNull());
    expect(escrituras().map((p) => p.path)).toEqual([
      "/api/lists/7/items/1/",
      "/api/lists/7/items/1/?borrar_calificacion=true",
    ]);
    expect(toast.success).toHaveBeenCalledWith(en.title.feedback.ratingReviewDeleted);
  });

  it("cancelar la confirmación de Watched deja el título en la lista", async () => {
    estado.lista = lista({ nombre: "Watched", clave: "vistas", tipo: "predeterminada" });
    estado.bloquear = true;
    const user = userEvent.setup();
    render(<ListDetailView id={7} />, { locale: "es" });
    await screen.findByRole("link", { name: /Título 1/ });

    await user.click(
      screen.getByRole("button", { name: `Quitar Título 1 de ${es.enums.defaultList.vistas}` })
    );
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", {
        name: es.common.actions.remove,
      })
    );
    const confirmar = await screen.findByRole("alertdialog", {
      name: es.title.watched.removeConfirmTitle,
    });
    await user.click(within(confirmar).getByRole("button", { name: es.common.actions.cancel }));

    expect(screen.getByRole("link", { name: /Título 1/ })).toBeInTheDocument();
    expect(escrituras()).toHaveLength(1);
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
    estado.params = new URLSearchParams("type=movie");
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
