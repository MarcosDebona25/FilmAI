import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TitleActions } from "@/components/features/title/TitleActions";
import type { ListaFicha } from "@/lib/title-lists";
import { fireEvent, render, screen, waitFor, within } from "./render";
import type { Estado } from "@/lib/title-status";

const api = vi.hoisted(() => ({ fetch: vi.fn() }));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
vi.mock("sonner", () => ({ toast }));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return { ...real, apiFetch: api.fetch };
});
const { ApiError } = await import("@/lib/api");

// Forma de `GET /api/lists/?id_tmdb=&tipo=` (L-01): resumen con pertenencia.
const lista = (campos: Partial<ListaFicha>): ListaFicha => ({
  id: 1,
  nombre: "Favoritos",
  clave: null,
  tipo: "personalizada",
  cantidad_items: 0,
  contiene: false,
  item_id: null,
  ...campos,
});
const LISTAS = [
  lista({ id: 1, nombre: "Favorites", clave: "favoritos", tipo: "predeterminada" }),
  lista({ id: 2, nombre: "Watched", clave: "vistas", tipo: "predeterminada" }),
  lista({
    id: 3,
    nombre: "Watchlist",
    clave: "pendientes",
    tipo: "predeterminada",
    contiene: true,
    item_id: 71,
  }),
  lista({ id: 5, nombre: "Watching", clave: "viendo", tipo: "predeterminada" }),
  lista({ id: 4, nombre: "Weekend marathon", cantidad_items: 3 }),
];

function renderizar(props: Partial<Parameters<typeof TitleActions>[0]> = {}) {
  const onListasChange = vi.fn();
  const onRate = vi.fn();
  const onCambiarEstado = vi.fn();
  render(
    <TitleActions
      titulo="Interstellar"
      idTmdb={157336}
      tipo="movie"
      listas={LISTAS}
      onListasChange={onListasChange}
      miCalificacion={null}
      onRate={onRate}
      onCambiarEstado={onCambiarEstado}
      {...props}
    />,
    { locale: "en" }
  );
  return { onListasChange, onRate, onCambiarEstado };
}

beforeEach(() => api.fetch.mockReset());
afterEach(() => vi.clearAllMocks());

describe("acciones de la ficha", () => {
  it("ya no hay botones sueltos de Watched ni de Watchlist: el estado va en un solo botón", () => {
    renderizar();

    expect(screen.getByRole("button", { name: "Favorite" })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
    expect(screen.queryByRole("button", { name: "Watched" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Watchlist" })).toBeNull();
    expect(screen.getByRole("button", { name: "Status: Watchlist" })).toBeInTheDocument();
  });

  it("Rate abre el modal; con nota, el botón la muestra y dice que edita", () => {
    const { onRate } = renderizar();
    fireEvent.click(screen.getByRole("button", { name: "Rate" }));
    expect(onRate).toHaveBeenCalled();
  });

  it("con calificación, el botón la anuncia", () => {
    renderizar({ miCalificacion: { id: 9, valor: 9, texto: null } });

    expect(
      screen.getByRole("button", { name: "Your rating: 9 out of 10. Edit" })
    ).toBeInTheDocument();
  });

  it("agregar a Favoritos pide el alta y avisa", async () => {
    api.fetch.mockResolvedValue({ item_id: 80 });
    const { onListasChange } = renderizar();

    fireEvent.click(screen.getByRole("button", { name: "Favorite" }));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Added to Favorites."));
    expect(api.fetch).toHaveBeenCalledWith("/api/lists/1/items/", {
      method: "POST",
      body: { id_tmdb: 157336, tipo: "movie" },
    });
    const favoritos = onListasChange.mock.calls[0][0].find((l: ListaFicha) => l.id === 1);
    expect(favoritos).toMatchObject({ contiene: true, item_id: 80, cantidad_items: 1 });
  });

  it("después de alternar, el foco sigue en el mismo botón", async () => {
    // Si el botón se volviera a montar, quien usa el teclado perdería su lugar.
    api.fetch.mockResolvedValue({ item_id: 80 });
    const Envoltorio = () => {
      const [listas, setListas] = useState(LISTAS);
      return (
        <TitleActions
          titulo="Interstellar"
          idTmdb={157336}
          tipo="movie"
          listas={listas}
          onListasChange={setListas}
          miCalificacion={null}
          onRate={vi.fn()}
          onCambiarEstado={vi.fn()}
        />
      );
    };
    render(<Envoltorio />, { locale: "en" });
    const favorito = screen.getByRole("button", { name: "Favorite" });
    favorito.focus();

    fireEvent.click(favorito);

    await waitFor(() => expect(favorito).toHaveAttribute("aria-pressed", "true"));
    expect(favorito).toHaveFocus();
  });
});

describe("menú «Add to list»", () => {
  const abrir = () =>
    fireEvent.click(screen.getByRole("button", { name: "Add Interstellar to a list" }));

  it("muestra solo las listas propias y alterna la pertenencia", async () => {
    api.fetch.mockResolvedValue({ item_id: 90 });
    renderizar();
    abrir();

    const menu = screen.getByRole("dialog", { name: "Add Interstellar to a list" });
    expect(within(menu).queryByRole("button", { name: /Favorites/ })).toBeNull();
    fireEvent.click(within(menu).getByRole("button", { name: /Weekend marathon/ }));

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("You added Interstellar to “Weekend marathon”.")
    );
  });

  it("crear una lista valida el nombre y avisa si ya existe", async () => {
    api.fetch.mockRejectedValueOnce(
      new ApiError(409, { code: "list_name_duplicated", params: {}, errors: [] })
    );
    renderizar();
    abrir();
    fireEvent.click(screen.getByRole("button", { name: "New list" }));

    fireEvent.click(screen.getByRole("button", { name: "Create and add" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a name for the list.");
    expect(api.fetch).not.toHaveBeenCalled();

    fireEvent.change(screen.getByRole("textbox", { name: "Name of the new list" }), {
      target: { value: "Weekend marathon" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create and add" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You already have a list with that name."
    );
  });

  it("crear una lista nueva la crea y le agrega la producción", async () => {
    api.fetch
      .mockResolvedValueOnce({
        id: 5,
        nombre: "Sci Fi",
        clave: null,
        tipo: "personalizada",
        cantidad_items: 0,
      })
      .mockResolvedValueOnce({ item_id: 91 });
    const { onListasChange } = renderizar();
    abrir();
    fireEvent.click(screen.getByRole("button", { name: "New list" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Name of the new list" }), {
      target: { value: "Sci Fi" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create and add" }));

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("You created “Sci Fi” and added Interstellar.")
    );
    expect(api.fetch).toHaveBeenNthCalledWith(1, "/api/lists/", {
      method: "POST",
      body: { nombre: "Sci Fi" },
    });
    expect(api.fetch).toHaveBeenNthCalledWith(2, "/api/lists/5/items/", {
      method: "POST",
      body: { id_tmdb: 157336, tipo: "movie" },
    });
    expect(onListasChange.mock.lastCall![0].at(-1)).toMatchObject({
      id: 5,
      contiene: true,
      item_id: 91,
      cantidad_items: 1,
    });
  });

  it("es un <dialog> modal: el clic en el fondo lo cierra y el clic adentro no", () => {
    renderizar();
    abrir();
    const menu = screen.getByRole("dialog");
    expect(menu.tagName).toBe("DIALOG");

    fireEvent.click(menu.querySelector("p") as HTMLElement);
    expect(screen.queryByRole("dialog")).not.toBeNull();

    // jsdom no calcula cajas: el clic cae fuera del rectángulo (0,0,0,0) del diálogo.
    fireEvent.click(menu, { clientX: 500, clientY: 500 });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("Escape lo cierra y devuelve el foco al botón", () => {
    renderizar();
    abrir();

    // Escape en un `<dialog>` modal dispara `cancel`, no un `keydown` que podamos atender.
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("button", { name: "Add Interstellar to a list" })).toHaveFocus();
  });
});

describe("botón de estado", () => {
  const boton = (nombre: string | RegExp = /^Status/) =>
    screen.getByRole("button", { name: nombre });
  const sinEstado = LISTAS.map((l) => (l.id === 3 ? { ...l, contiene: false, item_id: null } : l));
  const conEstado = (clave: Estado) =>
    LISTAS.map((l) => ({
      ...l,
      contiene: l.clave === clave ? true : l.clave === "pendientes" ? false : l.contiene,
    }));

  it("sin estado dice «Status»; con estado, nombra el estado actual", () => {
    renderizar({ listas: sinEstado });
    expect(boton("Status")).toHaveTextContent("Status");
  });

  it("muestra el estado de cada lista: Watching y Watched", () => {
    renderizar({ listas: conEstado("viendo") });
    expect(boton()).toHaveTextContent("Watching");
  });

  it("abre un menú con los tres estados como radios y marca el actual", () => {
    renderizar();
    fireEvent.click(boton());

    const menu = screen.getByRole("menu", { name: "Status for Interstellar" });
    const radios = within(menu).getAllByRole("menuitemradio");
    expect(radios.map((r) => r.textContent)).toEqual([
      "WatchlistWant to watch it",
      "WatchingStarted, not finished",
      "WatchedFinished",
    ]);
    expect(radios.map((r) => r.getAttribute("aria-checked"))).toEqual(["true", "false", "false"]);
    expect(within(menu).getByRole("menuitem", { name: "Remove status" })).toBeInTheDocument();
    expect(boton()).toHaveAttribute("aria-expanded", "true");
  });

  it("sin estado no ofrece «Remove status»", () => {
    renderizar({ listas: sinEstado });
    fireEvent.click(boton("Status"));

    expect(screen.queryByRole("menuitem", { name: "Remove status" })).toBeNull();
  });

  it("elegir un estado avisa al padre y cierra el menú devolviendo el foco al botón", () => {
    const { onCambiarEstado } = renderizar();
    fireEvent.click(boton());

    fireEvent.click(screen.getByRole("menuitemradio", { name: /Watching/ }));

    expect(onCambiarEstado).toHaveBeenCalledWith("viendo");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(boton()).toHaveFocus();
  });

  it("«Remove status» manda null", () => {
    const { onCambiarEstado } = renderizar();
    fireEvent.click(boton());

    fireEvent.click(screen.getByRole("menuitem", { name: "Remove status" }));

    expect(onCambiarEstado).toHaveBeenCalledWith(null);
  });

  it("elegir el estado actual solo cierra el menú", () => {
    const { onCambiarEstado } = renderizar();
    fireEvent.click(boton());

    fireEvent.click(screen.getByRole("menuitemradio", { name: /Watchlist/ }));

    expect(onCambiarEstado).not.toHaveBeenCalled();
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("al abrir, el foco cae en el estado marcado y ↑/↓ mueven el foco", () => {
    renderizar();
    fireEvent.click(boton());
    const menu = screen.getByRole("menu");
    const radios = within(menu).getAllByRole("menuitemradio");
    expect(radios[0]).toHaveFocus();

    fireEvent.keyDown(radios[0], { key: "ArrowDown" });
    expect(radios[1]).toHaveFocus();
    fireEvent.keyDown(radios[1], { key: "ArrowDown" });
    expect(radios[2]).toHaveFocus();
    fireEvent.keyDown(radios[2], { key: "ArrowDown" });
    expect(within(menu).getByRole("menuitem", { name: "Remove status" })).toHaveFocus();
    fireEvent.keyDown(document.activeElement as HTMLElement, { key: "ArrowDown" });
    expect(radios[0]).toHaveFocus();
    fireEvent.keyDown(radios[0], { key: "ArrowUp" });
    expect(within(menu).getByRole("menuitem", { name: "Remove status" })).toHaveFocus();
  });

  it("Escape cierra el menú y el foco vuelve al botón", () => {
    renderizar();
    fireEvent.click(boton());

    fireEvent(
      screen.getByRole("dialog", { hidden: true }),
      new Event("cancel", { cancelable: true })
    );

    expect(screen.queryByRole("menu")).toBeNull();
    expect(boton()).toHaveFocus();
  });

  it("con un cambio en curso el botón no deja abrir otro", () => {
    renderizar({ cambiandoEstado: true });
    expect(boton()).toHaveAttribute("aria-disabled", "true");
  });
});
