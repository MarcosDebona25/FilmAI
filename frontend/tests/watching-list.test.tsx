import { Toaster } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ListDetailView } from "@/components/features/lists/ListDetailView";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import type { ItemLista, ResumenLista } from "@/lib/lists";
import { act, fireEvent, render, screen, waitFor, within } from "./render";

/**
 * Watching como lista genérica (PR 4, canvas «Watching · list page»): el menú ⋯
 * de cada tarjeta, el toast con Undo (el mismo de la ficha, con el `<Toaster>`
 * de verdad) y el estado vacío.
 */
const estado = vi.hoisted(() => ({
  lista: null as unknown,
  items: [] as ItemLista[],
  pedidos: [] as { path: string; method: string; body?: unknown }[],
  escritorio: true,
  falla: false,
  propia: null as unknown,
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  useRouter: () => ({ push: vi.fn() }),
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));
vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
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
      if (method === "GET" && /^\/api\/lists\/\d+\/$/.test(path))
        return structuredClone(estado.lista);
      // Vistas y las demás tienen la banda de sugerencias; Watching no la pide.
      if (method === "GET" && path.includes("/suggestions/"))
        return { results: [], pagina: 1, paginas: 0, nombre_usado: false };
      if (method === "GET" && path.includes("/items/"))
        return { next: null, total: estado.items.length, results: structuredClone(estado.items) };
      if (method === "GET" && path === "/api/lists/")
        return [
          { id: 2, nombre: "Watchlist", clave: "pendientes", tipo: "predeterminada" },
          { id: 4, nombre: "Watching", clave: "viendo", tipo: "predeterminada" },
        ];
      if (method === "GET" && path.startsWith("/api/reviews/mias/")) {
        if (estado.propia) return estado.propia;
        throw new real.ApiError(404, { code: "not_found", params: {}, errors: [] });
      }
      if (method === "PUT" && path === "/api/lists/status/") {
        if (estado.falla) throw new real.ApiError(500, { code: "server_error" });
        const { estado: nuevo } = opciones.body as { estado: string | null };
        return {
          estado: nuevo,
          estado_anterior: nuevo === "viendo" ? null : "viendo",
          listas: [{ clave: "viendo", contiene: nuevo === "viendo", item_id: 900 }],
        };
      }
      if (method === "POST" && path === "/api/reviews/")
        return { id: 9, valor: 8, texto: null, fecha: "2026-11-17" };
      return undefined;
    }),
  };
});

function lista(extra: Partial<ResumenLista> = {}): ResumenLista {
  return {
    id: 4,
    nombre: "Watching",
    clave: "viendo",
    tipo: "predeterminada",
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
    titulo: `Linterna ${item_id}`,
    poster: null,
    anio: 2020,
    calificacion_promedio: 8.1,
    disponible: true,
    ...extra,
  };
}

const escrituras = () => estado.pedidos.filter((p) => p.method !== "GET");
const estados = () =>
  escrituras()
    .filter((p) => p.path === "/api/lists/status/")
    .map((p) => (p.body as { estado: string | null }).estado);
const titulos = () => screen.getAllByRole("link", { name: /Linterna/ });
const masDe = (n: number) => screen.getByRole("button", { name: `More for Linterna ${n}` });

function Pagina() {
  return (
    <>
      <ListDetailView id={4} />
      <Toaster />
    </>
  );
}

async function abrir(n = 2) {
  const view = render(<Pagina />, { locale: "en" });
  await screen.findByRole("link", { name: /Linterna 1/ });
  return { view, boton: masDe(n) };
}
function elegir(n: number, nombre: string) {
  fireEvent.click(masDe(n));
  fireEvent.click(screen.getByRole("menuitem", { name: nombre }));
}

beforeEach(() => {
  window.history.replaceState(null, "", "/lists/4");
  estado.lista = lista();
  estado.items = [item(1), item(2), item(3, { tipo: "tv" })];
  estado.pedidos = [];
  estado.escritorio = true;
  estado.falla = false;
  estado.propia = null;
  window.matchMedia = ((consulta: string) => ({
    matches: estado.escritorio,
    media: consulta,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia;
});
afterEach(() => vi.useRealTimers());

describe("Watching: el menú ⋯ de cada tarjeta", () => {
  it("cada tarjeta lleva el botón, con menú y etiqueta del título", async () => {
    await abrir();

    for (const n of [1, 2, 3]) {
      expect(masDe(n)).toHaveAttribute("aria-haspopup", "menu");
      expect(masDe(n)).toHaveAttribute("aria-expanded", "false");
    }
    expect(screen.getByText("3 items · 2 movies · 1 TV show")).toBeInTheDocument();
  });

  it("Watching no tiene la banda de sugerencias ni la pide (el backend respondería 404)", async () => {
    await abrir();

    expect(estado.pedidos.some((p) => p.path.includes("/suggestions/"))).toBe(false);
    expect(screen.queryByRole("region", { name: /Suggested/ })).toBeNull();
  });

  it("las otras listas no lo tienen", async () => {
    estado.lista = lista({ nombre: "Watched", clave: "vistas" });
    render(<Pagina />, { locale: "en" });
    await screen.findByRole("link", { name: /Linterna 1/ });

    expect(screen.queryByRole("button", { name: /^More for/ })).toBeNull();
  });

  it("abre con los tres ítems; con las flechas se mueve el foco", async () => {
    const { boton } = await abrir();

    fireEvent.click(boton);

    expect(boton).toHaveAttribute("aria-expanded", "true");
    const menu = screen.getByRole("menu", { name: "More for Linterna 2" });
    const filas = within(menu).getAllByRole("menuitem");
    expect(filas.map((fila) => fila.textContent)).toEqual([
      "Mark as finished",
      "Rate it…",
      "Remove from Watching",
    ]);
    expect(filas[0]).toHaveFocus();
    fireEvent.keyDown(menu, { key: "ArrowDown" });
    expect(filas[1]).toHaveFocus();
    fireEvent.keyDown(menu, { key: "ArrowUp" });
    fireEvent.keyDown(menu, { key: "ArrowUp" });
    expect(filas[2]).toHaveFocus();
  });

  it("Escape lo cierra y el foco vuelve al ⋯", async () => {
    const { boton } = await abrir();
    fireEvent.click(boton);

    fireEvent(
      screen.getByRole("dialog", { hidden: true }),
      new Event("cancel", { cancelable: true })
    );

    await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(boton).toHaveFocus();
  });

  it("un solo menú abierto a la vez", async () => {
    await abrir();

    fireEvent.click(masDe(1));
    fireEvent.click(masDe(3));

    expect(screen.getAllByRole("menu")).toHaveLength(1);
    expect(screen.getByRole("menu", { name: "More for Linterna 3" })).toBeInTheDocument();
    expect(masDe(1)).toHaveAttribute("aria-expanded", "false");
  });

  it("el clic afuera lo cierra", async () => {
    const { boton } = await abrir();
    fireEvent.click(boton);
    const dialogo = screen.getByRole("dialog", { hidden: true });
    dialogo.getBoundingClientRect = () =>
      ({ left: 10, right: 100, top: 10, bottom: 100 }) as DOMRect;

    fireEvent.click(dialogo, { clientX: 500, clientY: 500 });

    await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
    expect(boton).toHaveFocus();
  });
});

describe("Watching: Mark as finished y Remove con Undo", () => {
  it("Mark as finished: sale de la grilla, baja el conteo y avisa con Rate it y Undo", async () => {
    await abrir();

    elegir(2, "Mark as finished");

    await screen.findByText("Linterna 2 moved to Watched");
    expect(estados()).toEqual(["vistas"]);
    expect(escrituras()[0].body).toEqual({ id_tmdb: 102, tipo: "movie", estado: "vistas" });
    expect(titulos()).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /Linterna 2/ })).toBeNull();
    expect(screen.getByText("2 items · 1 movie · 1 TV show")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rate it" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
  });

  it("Undo la devuelve a su posición anterior, con el conteo de antes y sin toast", async () => {
    await abrir();
    elegir(2, "Mark as finished");
    await screen.findByText("Linterna 2 moved to Watched");

    fireEvent.click(screen.getByRole("button", { name: "Undo" }));

    await waitFor(() => expect(screen.getAllByRole("link", { name: /Linterna/ })).toHaveLength(3));
    expect(estados()).toEqual(["vistas", "viendo"]);
    // Vuelve con su fecha: «Started» no pasa a ser la de hoy.
    expect(escrituras()[1].body).toEqual({
      id_tmdb: 102,
      tipo: "movie",
      estado: "viendo",
      fecha_agregado: "2026-10-01T00:00:00Z",
    });
    expect(
      screen.getAllByRole("link", { name: /Linterna/ }).map((enlace) => enlace.getAttribute("href"))
    ).toEqual(["/movie/101?from=list-4", "/movie/102?from=list-4", "/tv/103?from=list-4"]);
    expect(screen.getByText("3 items · 2 movies · 1 TV show")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Linterna 2 moved to Watched")).toBeNull());
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
  });

  it("Undo con la tarjeta ya en la grilla no suma el conteo", async () => {
    // Con el `item_id` que devuelve el servidor al volver a anotarla (900).
    estado.items = [
      item(1),
      item(900, { id_tmdb: 102, titulo: "Linterna 2" }),
      item(3, { tipo: "tv" }),
    ];
    const { view } = await abrir();
    elegir(2, "Mark as finished");
    await screen.findByText("Linterna 2 moved to Watched");
    expect(screen.getByText("2 items · 1 movie · 1 TV show")).toBeInTheDocument();

    // Una búsqueda vuelve a pedir la primera página y esta trae la tarjeta otra vez.
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "Linterna" } });
    // El mock de `useSearchParams` lee la URL al dibujar: tras la espera del texto, se redibuja.
    await waitFor(() => expect(window.location.search).toContain("q=Linterna"));
    view.rerender(<Pagina />);
    await waitFor(() => expect(screen.getAllByRole("link", { name: /Linterna/ })).toHaveLength(3));
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));

    await waitFor(() => expect(screen.queryByRole("button", { name: "Undo" })).toBeNull());
    expect(screen.getAllByRole("link", { name: /Linterna/ })).toHaveLength(3);
    expect(screen.getByText("2 items · 1 movie · 1 TV show")).toBeInTheDocument();
  });

  it("Remove from Watching: queda sin estado, con su toast y su Undo (sin Rate it)", async () => {
    await abrir();

    elegir(1, "Remove from Watching");

    await screen.findByText("Linterna 1 removed from Watching");
    expect(estados()).toEqual([null]);
    expect(screen.queryByRole("link", { name: /Linterna 1/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Rate it" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => expect(screen.getAllByRole("link", { name: /Linterna/ })).toHaveLength(3));
    expect(screen.getAllByRole("link", { name: /Linterna/ })[0]).toHaveAttribute(
      "href",
      "/movie/101?from=list-4"
    );
  });

  it("una acción nueva reemplaza el toast y Undo solo revierte la última", async () => {
    await abrir();
    elegir(1, "Mark as finished");
    await screen.findByText("Linterna 1 moved to Watched");

    elegir(3, "Remove from Watching");

    await screen.findByText("Linterna 3 removed from Watching");
    expect(screen.queryByText("Linterna 1 moved to Watched")).toBeNull();
    expect(screen.getAllByRole("button", { name: "Undo" })).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => expect(screen.getAllByRole("link", { name: /Linterna/ })).toHaveLength(2));
    expect(screen.getByRole("link", { name: /Linterna 3/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Linterna 1/ })).toBeNull();
  });

  it("si falla, la tarjeta vuelve a su lugar y el toast de error no trae Undo", async () => {
    estado.falla = true;
    await abrir();

    elegir(2, "Mark as finished");

    expect(await screen.findByText(en.title.status.error)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Linterna/ })).toHaveLength(3);
    expect(screen.getByText("3 items · 2 movies · 1 TV show")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
  });

  it("en celular el toast no trae Rate it (vive en la hoja)", async () => {
    estado.escritorio = false;
    await abrir();

    elegir(2, "Mark as finished");

    await screen.findByText("Linterna 2 moved to Watched");
    expect(screen.queryByRole("button", { name: "Rate it" })).toBeNull();
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
  });

  it("en español usa los nombres de los estados", async () => {
    render(<Pagina />, { locale: "es" });
    await screen.findByRole("link", { name: /Linterna 1/ });

    fireEvent.click(screen.getByRole("button", { name: "Más acciones para Linterna 1" }));
    fireEvent.click(screen.getByRole("menuitem", { name: es.lists.watching.markFinished }));

    expect(await screen.findByText("Linterna 1 pasó a Vistas")).toBeInTheDocument();
  });
});

describe("Watching: calificar", () => {
  async function calificar() {
    const dialogo = await screen.findByRole("dialog", { name: /Linterna 2/ });
    fireEvent.click(within(dialogo).getByRole("radio", { name: "8 out of 10" }));
    await act(async () => {
      fireEvent.click(within(dialogo).getByRole("button", { name: "Post" }));
    });
  }

  it("Rate it… abre el diálogo de la ficha; calificar la pasa a Watched, con Undo", async () => {
    await abrir();

    elegir(2, "Rate it…");
    await calificar();

    await screen.findByText("Rated ★ 8 · Moved to Watched");
    expect(escrituras().map((p) => p.path)).toEqual(["/api/reviews/"]);
    expect(screen.queryByRole("link", { name: /Linterna 2/ })).toBeNull();
    expect(screen.getByText("2 items · 1 movie · 1 TV show")).toBeInTheDocument();

    // Undo la devuelve a Watching (la nota se conserva) en su lugar.
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => expect(screen.getAllByRole("link", { name: /Linterna/ })).toHaveLength(3));
    expect(estados()).toEqual(["viendo"]);
    expect(screen.getAllByRole("link", { name: /Linterna/ })[1]).toHaveAttribute(
      "href",
      "/movie/102?from=list-4"
    );
  });

  it("«Rate it» del toast abre el mismo diálogo y cierra el toast", async () => {
    await abrir();
    elegir(2, "Mark as finished");
    await screen.findByText("Linterna 2 moved to Watched");

    fireEvent.click(screen.getByRole("button", { name: "Rate it" }));

    expect(await screen.findByRole("dialog", { name: /Linterna 2/ })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Linterna 2 moved to Watched")).toBeNull());
    await calificar();
    // Ya estaba en Watched: solo avisa de la nota, sin Undo.
    await screen.findByText("Rated ★ 8");
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
    expect(estados()).toEqual(["vistas"]);
  });

  it("si el título ya tenía nota, abre en edición y no lo mueve", async () => {
    estado.propia = { id: 5, valor: 6, texto: null, fecha: "2026-10-01" };
    await abrir();

    elegir(2, "Rate it…");

    const dialogo = await screen.findByRole("dialog", { name: "Edit rating" });
    expect(within(dialogo).getByRole("radio", { name: "6 out of 10" })).toHaveAttribute(
      "aria-checked",
      "true"
    );
  });
});

describe("Watching: estado vacío", () => {
  it("«Nothing in progress» con «Open Watchlist» hacia la lista Pendientes", async () => {
    estado.lista = lista({ cantidad_items: 0, cantidad_peliculas: 0, cantidad_series: 0 });
    estado.items = [];
    render(<Pagina />, { locale: "en" });

    expect(await screen.findByRole("heading", { name: "Nothing in progress" })).toBeInTheDocument();
    expect(screen.getByText(en.lists.watching.emptyDescription)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "Open Watchlist" })).toHaveAttribute(
        "href",
        "/lists/2"
      )
    );
    expect(screen.queryByRole("link", { name: en.common.actions.explore })).toBeNull();
  });

  it("al sacar el último título, el estado vacío reemplaza a la grilla", async () => {
    estado.lista = lista({ cantidad_items: 1, cantidad_peliculas: 1, cantidad_series: 0 });
    estado.items = [item(1)];
    await abrir(1);

    elegir(1, "Mark as finished");

    expect(await screen.findByRole("heading", { name: "Nothing in progress" })).toBeInTheDocument();
    expect(screen.queryAllByRole("link", { name: /Linterna/ })).toHaveLength(0);
    // Undo trae la tarjeta de vuelta y el vacío desaparece.
    fireEvent.click(await screen.findByRole("button", { name: "Undo" }));
    expect(await screen.findByRole("link", { name: /Linterna 1/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Nothing in progress" })).toBeNull();
  });

  it("las otras listas vacías siguen invitando a explorar", async () => {
    estado.lista = lista({
      nombre: "Maratón",
      clave: null,
      tipo: "personalizada",
      cantidad_items: 0,
    });
    estado.items = [];
    render(<Pagina />, { locale: "en" });

    expect(await screen.findByText(en.lists.detail.emptyTitle)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: en.common.actions.explore })).toBeInTheDocument();
  });
});

describe("Watching: título con el conteo en la misma línea", () => {
  it("el conteo acompaña al título y en celular dice solo los ítems", async () => {
    await abrir();

    const titulo = screen.getByRole("heading", { level: 1, name: "Watching" });
    const linea = titulo.parentElement!;
    expect(linea).toHaveTextContent("3 items · 2 movies · 1 TV show");
    expect(within(linea).getByText("3 items", { exact: true })).toHaveClass("md:hidden");
  });
});
