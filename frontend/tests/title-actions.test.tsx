import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TitleActions } from "@/components/features/title/TitleActions";
import type { ListaFicha } from "@/lib/title-lists";
import { fireEvent, render, screen, waitFor, within } from "./render";

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
  lista({
    id: 2,
    nombre: "Watched",
    clave: "vistas",
    tipo: "predeterminada",
    contiene: true,
    item_id: 70,
  }),
  lista({
    id: 3,
    nombre: "Watchlist",
    clave: "pendientes",
    tipo: "predeterminada",
    contiene: true,
    item_id: 71,
  }),
  lista({ id: 4, nombre: "Weekend marathon", cantidad_items: 3 }),
];

function renderizar(props: Partial<Parameters<typeof TitleActions>[0]> = {}) {
  const onListasChange = vi.fn();
  const onRate = vi.fn();
  const onCalificacionBorrada = vi.fn();
  render(
    <TitleActions
      titulo="Interstellar"
      idTmdb={157336}
      tipo="movie"
      listas={LISTAS}
      onListasChange={onListasChange}
      miCalificacion={null}
      onRate={onRate}
      onCalificacionBorrada={onCalificacionBorrada}
      {...props}
    />,
    { locale: "en" }
  );
  return { onListasChange, onRate, onCalificacionBorrada };
}

beforeEach(() => api.fetch.mockReset());
afterEach(() => vi.clearAllMocks());

describe("acciones de la ficha", () => {
  it("los botones reflejan en qué listas está la producción", () => {
    renderizar();

    expect(screen.getByRole("button", { name: "Favorite" })).toHaveAttribute(
      "aria-pressed",
      "false"
    );
    expect(screen.getByRole("button", { name: "Watched" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Watchlist" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
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
          onCalificacionBorrada={vi.fn()}
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

  it("quitar de Pendientes borra el ítem por su id", async () => {
    api.fetch.mockResolvedValue(undefined);
    renderizar();

    fireEvent.click(screen.getByRole("button", { name: "Watchlist" }));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith("Removed from Watchlist."));
    expect(api.fetch).toHaveBeenCalledWith("/api/lists/3/items/71/", { method: "DELETE" });
  });

  it("quitar de Vistas algo calificado pide confirmar y borra la calificación", async () => {
    api.fetch
      .mockRejectedValueOnce(
        new ApiError(409, { code: "rating_blocks_removal_from_watched", params: {}, errors: [] })
      )
      .mockResolvedValueOnce(undefined);
    const { onCalificacionBorrada } = renderizar({
      miCalificacion: { id: 9, valor: 9, texto: "La vi tres veces." },
    });

    fireEvent.click(screen.getByRole("button", { name: "Watched" }));
    const dialogo = await screen.findByRole("alertdialog", { name: "Remove from Watched?" });
    expect(within(dialogo).getByText("La vi tres veces.")).toBeInTheDocument();
    fireEvent.click(within(dialogo).getByRole("button", { name: "Remove from Watched" }));

    await waitFor(() => expect(onCalificacionBorrada).toHaveBeenCalled());
    expect(api.fetch).toHaveBeenLastCalledWith("/api/lists/2/items/70/?borrar_calificacion=true", {
      method: "DELETE",
    });
    expect(toast.success).toHaveBeenCalledWith("Rating and review removed.");
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

  it("Escape lo cierra y devuelve el foco al botón", () => {
    renderizar();
    abrir();

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("button", { name: "Add Interstellar to a list" })).toHaveFocus();
  });
});
