import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { ListsView } from "@/components/features/lists/ListsView";
import { ApiError } from "@/lib/api";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import type { ResumenLista } from "@/lib/lists";
import { act, fireEvent, render, screen, waitFor, within } from "./render";

function lista(id: number, nombre: string, extra: Partial<ResumenLista> = {}): ResumenLista {
  return {
    id,
    nombre,
    clave: null,
    tipo: "personalizada",
    cantidad_items: 0,
    cantidad_peliculas: 0,
    cantidad_series: 0,
    preview_posters: [],
    ...extra,
  };
}

const INICIALES: ResumenLista[] = [
  lista(1, "Favorites", { clave: "favoritos", tipo: "predeterminada", cantidad_items: 2 }),
  lista(2, "Watchlist", { clave: "pendientes", tipo: "predeterminada" }),
  lista(3, "Watched", { clave: "vistas", tipo: "predeterminada" }),
  lista(10, "Maratón", {
    cantidad_items: 7,
    cantidad_peliculas: 5,
    cantidad_series: 2,
    preview_posters: ["/a.jpg", "/b.jpg", "/c.jpg", "/d.jpg", "/e.jpg"],
  }),
  lista(11, "Clásicos"),
  lista(12, "Terror"),
];

const estado = vi.hoisted(() => ({
  listas: [] as unknown[],
  pedidos: [] as { path: string; method: string; body?: unknown }[],
  fallar: null as null | ((path: string, method: string) => unknown),
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
      const error = estado.fallar?.(path, method);
      if (error) throw error;
      if (method === "GET") return structuredClone(estado.listas);
      if (method === "POST")
        return {
          id: 99,
          nombre: (opciones.body as { nombre: string }).nombre,
          clave: null,
          tipo: "personalizada",
          cantidad_items: 0,
          cantidad_peliculas: 0,
          cantidad_series: 0,
          preview_posters: [],
        };
      if (method === "PUT" && path === "/api/lists/order/") {
        const ids = (opciones.body as { ids: number[] }).ids;
        const todas = estado.listas as ResumenLista[];
        return [
          ...todas.filter((l) => l.tipo === "predeterminada"),
          ...ids.map((id) => todas.find((l) => l.id === id)),
        ];
      }
      if (method === "PUT")
        return { ...(estado.listas as ResumenLista[])[3], ...(opciones.body as object) };
      return undefined;
    }),
  };
});

const escrituras = () => estado.pedidos.filter((p) => p.method !== "GET");
const nombres = () =>
  screen.getAllByRole("heading", { level: 2 }).map((encabezado) => encabezado.textContent);

beforeEach(() => {
  estado.listas = structuredClone(INICIALES);
  estado.pedidos = [];
  estado.fallar = null;
  vi.mocked(toast.success).mockClear();
  vi.mocked(toast.error).mockClear();
});
afterEach(() => vi.useRealTimers());

describe("Listas: vista general", () => {
  it("muestra el resumen, las predeterminadas fijas sin menú y las personalizadas con ⋯", async () => {
    render(<ListsView />, { locale: "en" });

    expect(await screen.findByRole("heading", { level: 1, name: "Lists" })).toBeInTheDocument();
    expect(screen.getByText("6 lists · 3 defaults")).toBeInTheDocument();
    expect(nombres()).toEqual([
      "Favorites",
      "Watchlist",
      "Watched",
      "Maratón",
      "Clásicos",
      "Terror",
    ]);
    expect(screen.getAllByText(en.common.lists.defaultBadge)).toHaveLength(3);
    // Solo las personalizadas tienen ⋯ y manija.
    expect(screen.getAllByRole("button", { name: /^Actions for the list/ })).toHaveLength(3);
    expect(screen.getAllByRole("button", { name: en.common.lists.reorderLabel })).toHaveLength(3);
    expect(screen.getByText("7 items · 5 movies · 2 TV shows")).toBeInTheDocument();
    expect(screen.getByText("2 items · 0 movies · 0 TV shows")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Maratón" })).toHaveAttribute("href", "/lists/10");
  });

  it("nombra las predeterminadas por su clave en cada idioma", async () => {
    render(<ListsView />, { locale: "es" });

    await screen.findByRole("heading", { level: 1, name: es.nav.main.lists });
    expect(nombres().slice(0, 3)).toEqual([
      es.enums.defaultList.favoritos,
      es.enums.defaultList.pendientes,
      es.enums.defaultList.vistas,
    ]);
  });

  it("crea una lista al final, la anuncia y valida el nombre antes de enviar", async () => {
    const user = userEvent.setup();
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Maratón");

    await user.click(screen.getByRole("button", { name: en.lists.create.title }));
    const dialogo = screen.getByRole("dialog", { name: en.lists.create.title });
    await user.click(within(dialogo).getByRole("button", { name: en.common.actions.create }));
    expect(within(dialogo).getByRole("alert")).toHaveTextContent(en.lists.name.requiredError);
    await user.type(within(dialogo).getByLabelText(en.common.lists.nameLabel), "Cine #1");
    await user.click(within(dialogo).getByRole("button", { name: en.common.actions.create }));
    expect(within(dialogo).getByRole("alert")).toHaveTextContent(
      en.lists.name.invalidCharactersError
    );
    expect(escrituras()).toHaveLength(0);

    await user.clear(within(dialogo).getByLabelText(en.common.lists.nameLabel));
    await user.type(within(dialogo).getByLabelText(en.common.lists.nameLabel), "Sunday marathon");
    await user.click(within(dialogo).getByRole("button", { name: en.common.actions.create }));

    await waitFor(() => expect(nombres().at(-1)).toBe("Sunday marathon"));
    expect(escrituras()).toEqual([
      { path: "/api/lists/", method: "POST", body: { nombre: "Sunday marathon" } },
    ]);
    expect(toast.success).toHaveBeenCalledWith(en.lists.feedback.created);
  });

  it("deja el diálogo abierto con el error del backend si el nombre está repetido", async () => {
    estado.fallar = (_, method) =>
      method === "POST" &&
      new ApiError(409, {
        code: "list_name_duplicated",
        params: {},
        errors: [{ field: "nombre", code: "list_name_duplicated", params: {} }],
      });
    const user = userEvent.setup();
    render(<ListsView />, { locale: "es" });
    await screen.findByText("Maratón");

    await user.click(screen.getByRole("button", { name: es.lists.create.title }));
    await user.type(screen.getByLabelText(es.common.lists.nameLabel), "Maratón");
    await user.click(screen.getByRole("button", { name: es.common.actions.create }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      es.errors.codes.list_name_duplicated
    );
    expect(screen.getByRole("dialog", { name: es.lists.create.title })).toBeInTheDocument();
  });

  it("renombra desde el menú", async () => {
    const user = userEvent.setup();
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Maratón");

    await user.click(screen.getByRole("button", { name: "Actions for the list Maratón" }));
    await user.click(screen.getByRole("button", { name: en.common.lists.rename }));
    const campo = screen.getByLabelText(en.common.lists.nameLabel);
    expect(campo).toHaveValue("Maratón");
    await user.clear(campo);
    await user.type(campo, "Semana");
    await user.click(screen.getByRole("button", { name: en.common.actions.save }));

    await waitFor(() => expect(nombres()).toContain("Semana"));
    expect(escrituras()).toEqual([
      { path: "/api/lists/10/", method: "PUT", body: { nombre: "Semana" } },
    ]);
    expect(toast.success).toHaveBeenCalledWith(en.lists.feedback.renamed);
  });

  it("elimina con confirmación y no hace nada si se cancela", async () => {
    const user = userEvent.setup();
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Clásicos");

    await user.click(screen.getByRole("button", { name: "Actions for the list Clásicos" }));
    await user.click(screen.getByRole("button", { name: en.common.actions.delete }));
    const aviso = screen.getByRole("alertdialog", { name: "Delete “Clásicos”?" });
    await user.click(within(aviso).getByRole("button", { name: en.common.actions.cancel }));
    expect(escrituras()).toHaveLength(0);

    await user.click(screen.getByRole("button", { name: "Actions for the list Clásicos" }));
    await user.click(screen.getByRole("button", { name: en.common.actions.delete }));
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", {
        name: en.common.actions.delete,
      })
    );

    await waitFor(() => expect(nombres()).not.toContain("Clásicos"));
    expect(escrituras()).toEqual([{ path: "/api/lists/11/", method: "DELETE", body: undefined }]);
    expect(toast.success).toHaveBeenCalledWith(en.lists.feedback.deleted);
  });

  it("en celular el menú ofrece Move up/Move down y reordena con la API", async () => {
    const user = userEvent.setup();
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Clásicos");

    await user.click(screen.getByRole("button", { name: "Actions for the list Clásicos" }));
    expect(screen.queryByRole("button", { name: en.common.lists.moveLeft })).toBeNull();
    expect(screen.getByRole("button", { name: en.common.lists.moveDown })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: en.common.lists.moveUp }));

    await waitFor(() => expect(nombres().slice(3)).toEqual(["Clásicos", "Maratón", "Terror"]));
    expect(escrituras()).toEqual([
      { path: "/api/lists/order/", method: "PUT", body: { ids: [11, 10, 12] } },
    ]);
    expect(toast.success).toHaveBeenCalledWith(en.lists.feedback.orderSaved);
  });

  it("deshabilita Move up en la primera personalizada y Move down en la última", async () => {
    const user = userEvent.setup();
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Maratón");

    await user.click(screen.getByRole("button", { name: "Actions for the list Maratón" }));
    expect(screen.getByRole("button", { name: en.common.lists.moveUp })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: en.common.actions.cancel }));
    await user.click(screen.getByRole("button", { name: "Actions for the list Terror" }));
    expect(screen.getByRole("button", { name: en.common.lists.moveDown })).toBeDisabled();
  });

  it("en escritorio el menú ofrece Move left/Move right", async () => {
    vi.stubGlobal("matchMedia", (consulta: string) => ({
      matches: consulta.includes("min-width"),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    const user = userEvent.setup();
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Clásicos");

    await user.click(screen.getByRole("button", { name: "Actions for the list Clásicos" }));
    expect(screen.queryByRole("menuitem", { name: en.common.lists.moveUp })).toBeNull();
    await user.click(screen.getByRole("menuitem", { name: en.common.lists.moveRight }));

    await waitFor(() => expect(nombres().slice(3)).toEqual(["Maratón", "Terror", "Clásicos"]));
    vi.unstubAllGlobals();
  });

  it("si guardar el orden falla, vuelve al orden anterior y avisa", async () => {
    estado.fallar = (path, method) =>
      method === "PUT" &&
      path === "/api/lists/order/" &&
      new ApiError(500, { code: "server_error" });
    const user = userEvent.setup();
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Clásicos");

    await user.click(screen.getByRole("button", { name: "Actions for the list Clásicos" }));
    await user.click(screen.getByRole("button", { name: en.common.lists.moveUp }));

    await waitFor(() => expect(toast.error).toHaveBeenCalled());
    expect(nombres().slice(3)).toEqual(["Maratón", "Clásicos", "Terror"]);
  });
});

describe("Listas: arrastre", () => {
  function tarjeta(nombre: string) {
    return screen.getByRole("heading", { level: 2, name: nombre }).closest("li") as HTMLElement;
  }
  const manija = (nombre: string) =>
    tarjeta(nombre).querySelector("[data-drag-handle]") as HTMLElement;
  const toque = (x: number, y: number) => ({
    touches: [{ identifier: 1, clientX: x, clientY: y, target: document.body }],
  });

  it("el menú del sistema queda anulado en las tarjetas arrastrables (táctil)", async () => {
    vi.stubGlobal("matchMedia", (consulta: string) => ({
      matches: consulta.includes("pointer: coarse"),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Maratón");

    const permitido = fireEvent.contextMenu(tarjeta("Maratón"));
    expect(permitido).toBe(false);
    expect(tarjeta("Maratón").className).toContain("touch-callout:none");
    expect(tarjeta("Maratón").className).toContain("select-none");
    expect(screen.getByRole("link", { name: "Maratón" })).toHaveAttribute("draggable", "false");
    vi.unstubAllGlobals();
  });

  it("un movimiento antes de la pulsación larga es scroll: no levanta la tarjeta", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Maratón");

    const li = tarjeta("Maratón");
    fireEvent.touchStart(li, toque(100, 100));
    await act(async () => vi.advanceTimersByTime(100));
    fireEvent.touchMove(li, toque(100, 140));
    await act(async () => vi.advanceTimersByTime(400));
    fireEvent.touchEnd(li, toque(100, 140));

    expect(manija("Maratón")).not.toHaveAttribute("aria-pressed");
    expect(escrituras()).toHaveLength(0);
  });

  it("una pulsación larga quieta levanta la tarjeta y el anuncio sale en el idioma", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<ListsView />, { locale: "es" });
    await screen.findByText("Maratón");

    const li = tarjeta("Maratón");
    fireEvent.touchStart(li, toque(100, 100));
    await act(async () => vi.advanceTimersByTime(300));

    await waitFor(() => expect(manija("Maratón")).toHaveAttribute("aria-pressed", "true"));
    expect(document.body.textContent).toContain("Maratón movida a la posición 1 de 3");
    fireEvent.touchEnd(li, toque(100, 100));
  });

  it("un toque corto no arrastra y el enlace sigue siendo un enlace", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<ListsView />, { locale: "en" });
    await screen.findByText("Maratón");

    const li = tarjeta("Maratón");
    fireEvent.touchStart(li, toque(100, 100));
    await act(async () => vi.advanceTimersByTime(80));
    fireEvent.touchEnd(li, toque(100, 100));
    await act(async () => vi.advanceTimersByTime(500));

    expect(manija("Maratón")).not.toHaveAttribute("aria-pressed");
  });
});
