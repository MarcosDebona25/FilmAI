import { useState } from "react";
import { Toaster } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TitleActions } from "@/components/features/title/TitleActions";
import { useEstadoFicha } from "@/components/features/title/use-estado-ficha";
import type { ListaFicha } from "@/lib/title-lists";
import { estadoDe, type Estado } from "@/lib/title-status";
import { act, fireEvent, render, screen, waitFor, within } from "./render";

/**
 * El flujo del estado de la ficha de punta a punta, con el `<Toaster>` de
 * verdad: el toast es lo que ve el usuario, así que se prueba su texto, su
 * botón Undo y que el segundo cambio reemplace al primero.
 */
const api = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock("@/lib/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/api")>();
  return { ...real, apiFetch: api.fetch };
});
const { ApiError } = await import("@/lib/api");

/** Cuándo «entró» el título a su estado: el Undo la manda de vuelta. */
const FECHA = "2026-10-01T12:00:00Z";
const lista = (id: number, clave: ListaFicha["clave"], contiene = false): ListaFicha => ({
  id,
  nombre: String(clave),
  clave,
  tipo: "predeterminada",
  cantidad_items: 0,
  contiene,
  item_id: contiene ? id * 10 : null,
  fecha_agregado: contiene ? FECHA : null,
});
const enEstado = (estado: Estado | null): ListaFicha[] => [
  lista(1, "favoritos"),
  lista(2, "pendientes", estado === "pendientes"),
  lista(3, "viendo", estado === "viendo"),
  lista(4, "vistas", estado === "vistas"),
];
/** Lo que responde `PUT /api/lists/status/`. */
const respuesta = (estado: Estado | null, anterior: Estado | null) => ({
  estado,
  estado_anterior: anterior,
  listas: enEstado(estado),
});

function Ficha({ inicial, recargar = true }: { inicial: Estado | null; recargar?: boolean }) {
  const [listas, setListas] = useState(enEstado(inicial));
  const estado = useEstadoFicha({
    idTmdb: 157336,
    tipo: "movie",
    listas,
    onListasChange: setListas,
  });
  return (
    <>
      <TitleActions
        titulo="Interstellar"
        idTmdb={157336}
        tipo="movie"
        listas={listas}
        onListasChange={setListas}
        miCalificacion={null}
        onRate={vi.fn()}
        onCambiarEstado={estado.cambiar}
        cambiandoEstado={estado.guardando}
      />
      <button
        type="button"
        onClick={() => {
          // Como la ficha: el servidor mueve a Watched y las listas se recargan.
          const previo = estadoDe(listas);
          if (recargar) setListas(enEstado("vistas"));
          estado.avisarCalificacion({ valor: 8, previo, conResena: false });
        }}
      >
        simular calificación
      </button>
      <Toaster />
    </>
  );
}

const boton = () => screen.getByRole("button", { name: /^Status/ });
function elegir(nombre: RegExp | string) {
  fireEvent.click(boton());
  fireEvent.click(screen.getByRole("menuitemradio", { name: nombre }));
}
const quitarEstado = () => {
  fireEvent.click(boton());
  fireEvent.click(screen.getByRole("menuitem", { name: "Remove status" }));
};
const aviso = (texto: string | RegExp) => screen.findByText(texto);

beforeEach(() => api.fetch.mockReset());
afterEach(() => vi.useRealTimers());

describe("cambiar el estado desde la ficha", () => {
  it("es optimista: el botón cambia antes de que responda el servidor", async () => {
    let responder!: (valor: unknown) => void;
    api.fetch.mockReturnValue(new Promise((resolver) => (responder = resolver)));
    render(<Ficha inicial="pendientes" />, { locale: "en" });

    elegir(/Watching/);

    expect(boton()).toHaveTextContent("Watching");
    expect(boton()).toHaveAttribute("aria-disabled", "true");
    expect(api.fetch).toHaveBeenCalledWith("/api/lists/status/", {
      method: "PUT",
      body: { id_tmdb: 157336, tipo: "movie", estado: "viendo" },
    });
    await act(async () => responder(respuesta("viendo", "pendientes")));
    expect(await aviso("Moved to Watching")).toBeInTheDocument();
    expect(boton()).not.toHaveAttribute("aria-disabled");
  });

  it("el toast trae Undo y avisa a lectores de pantalla que dura 6 segundos", async () => {
    api.fetch.mockResolvedValue(respuesta("viendo", "pendientes"));
    render(<Ficha inicial="pendientes" />, { locale: "en" });

    elegir(/Watching/);

    await aviso("Moved to Watching");
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
    expect(
      screen.getByText("Moved to Watching. Undo available for 6 seconds.")
    ).toBeInTheDocument();
    // Nunca roba el foco.
    expect(boton()).toHaveFocus();
  });

  it("Undo vuelve al estado anterior con el mismo endpoint y avisa sin Undo", async () => {
    api.fetch
      .mockResolvedValueOnce(respuesta("viendo", "pendientes"))
      .mockResolvedValueOnce(respuesta("pendientes", "viendo"));
    render(<Ficha inicial="pendientes" />, { locale: "en" });
    elegir(/Watching/);
    await aviso("Moved to Watching");

    fireEvent.click(screen.getByRole("button", { name: "Undo" }));

    expect(await aviso("Back to Watchlist")).toBeInTheDocument();
    expect(api.fetch).toHaveBeenLastCalledWith("/api/lists/status/", {
      method: "PUT",
      body: { id_tmdb: 157336, tipo: "movie", estado: "pendientes", fecha_agregado: FECHA },
    });
    expect(boton()).toHaveTextContent("Watchlist");
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
    expect(screen.queryByText("Moved to Watching")).toBeNull();
  });

  it("un segundo cambio reemplaza el toast y Undo vuelve un solo paso", async () => {
    api.fetch
      .mockResolvedValueOnce(respuesta("viendo", "pendientes"))
      .mockResolvedValueOnce(respuesta("vistas", "viendo"))
      .mockResolvedValueOnce(respuesta("viendo", "vistas"));
    render(<Ficha inicial="pendientes" />, { locale: "en" });
    elegir(/Watching/);
    await aviso("Moved to Watching");

    elegir(/Watched/);

    await aviso("Moved to Watched");
    expect(screen.queryByText("Moved to Watching")).toBeNull();
    expect(screen.getAllByRole("button", { name: "Undo" })).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(await aviso("Back to Watching")).toBeInTheDocument();
    expect(api.fetch).toHaveBeenLastCalledWith("/api/lists/status/", {
      method: "PUT",
      body: { id_tmdb: 157336, tipo: "movie", estado: "viendo", fecha_agregado: FECHA },
    });
  });

  it("quitar el estado tiene el mismo toast con Undo", async () => {
    api.fetch
      .mockResolvedValueOnce(respuesta(null, "pendientes"))
      .mockResolvedValueOnce(respuesta("pendientes", null));
    render(<Ficha inicial="pendientes" />, { locale: "en" });

    quitarEstado();

    await aviso("Status removed");
    expect(boton()).toHaveTextContent("Status");
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(await aviso("Back to Watchlist")).toBeInTheDocument();
  });

  it("si falla, el botón vuelve al estado anterior y el toast de error no trae Undo", async () => {
    api.fetch.mockRejectedValueOnce(
      new ApiError(500, { code: "server_error", params: {}, errors: [] })
    );
    render(<Ficha inicial="pendientes" />, { locale: "en" });

    elegir(/Watching/);

    expect(await aviso("Couldn’t update the status. Try again.")).toBeInTheDocument();
    expect(boton()).toHaveTextContent("Watchlist");
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
    expect(screen.queryByText("Moved to Watching")).toBeNull();
  });

  it("si falla el Undo, también avisa con el error y deja el estado como estaba", async () => {
    api.fetch
      .mockResolvedValueOnce(respuesta("viendo", "pendientes"))
      .mockRejectedValueOnce(new ApiError(500, { code: "server_error", params: {}, errors: [] }));
    render(<Ficha inicial="pendientes" />, { locale: "en" });
    elegir(/Watching/);
    await aviso("Moved to Watching");

    fireEvent.click(screen.getByRole("button", { name: "Undo" }));

    expect(await aviso("Couldn’t update the status. Try again.")).toBeInTheDocument();
    expect(boton()).toHaveTextContent("Watching");
  });

  it("el toast con Undo dura 6 segundos y el de «Back to» solo 2", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.fetch
      .mockResolvedValueOnce(respuesta("viendo", "pendientes"))
      .mockResolvedValueOnce(respuesta("pendientes", "viendo"));
    render(<Ficha inicial="pendientes" />, { locale: "en" });
    elegir(/Watching/);
    await aviso("Moved to Watching");

    await act(async () => void vi.advanceTimersByTime(5500));
    expect(screen.queryByText("Moved to Watching")).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await aviso("Back to Watchlist");

    await act(async () => void vi.advanceTimersByTime(1500));
    expect(screen.queryByText("Back to Watchlist")).not.toBeNull();
    await act(async () => void vi.advanceTimersByTime(1000));
    await waitFor(() => expect(screen.queryByText("Back to Watchlist")).toBeNull());
  });
});

describe("calificar desde la ficha", () => {
  const calificar = () =>
    fireEvent.click(screen.getByRole("button", { name: "simular calificación" }));

  it("desde Watchlist avisa que pasó a Watched, con Undo que restaura el estado", async () => {
    api.fetch.mockResolvedValueOnce(respuesta("pendientes", "vistas"));
    render(<Ficha inicial="pendientes" />, { locale: "en" });

    calificar();

    const toast = await screen.findByText("Rated ★ 8 · Moved to Watched");
    expect(toast).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(await aviso("Back to Watchlist")).toBeInTheDocument();
    expect(api.fetch).toHaveBeenCalledWith("/api/lists/status/", {
      method: "PUT",
      body: { id_tmdb: 157336, tipo: "movie", estado: "pendientes", fecha_agregado: FECHA },
    });
  });

  it("desde Watching también tiene Undo", async () => {
    render(<Ficha inicial="viendo" />, { locale: "en" });
    calificar();
    await aviso("Rated ★ 8 · Moved to Watched");
    expect(within(document.body).getByRole("button", { name: "Undo" })).toBeInTheDocument();
  });

  it("el Undo funciona aunque las listas del servidor no hayan llegado todavía", async () => {
    // La ficha no actualiza las listas por su cuenta: `calificarSinRecargar`
    // solo avisa, como `TitleView` antes de que responda `recargarListas()`.
    api.fetch.mockResolvedValueOnce(respuesta("viendo", "vistas"));
    render(<Ficha inicial="viendo" recargar={false} />, { locale: "en" });

    calificar();

    await aviso("Rated ★ 8 · Moved to Watched");
    // Las listas ya muestran Watched (optimista), no el estado de antes.
    expect(boton()).toHaveTextContent("Watched");
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(await aviso("Back to Watching")).toBeInTheDocument();
    expect(api.fetch).toHaveBeenCalledWith("/api/lists/status/", {
      method: "PUT",
      body: { id_tmdb: 157336, tipo: "movie", estado: "viendo", fecha_agregado: FECHA },
    });
    expect(boton()).toHaveTextContent("Watching");
  });

  it("si ya estaba en Watched dice solo «Rated ★ 8», sin Undo", async () => {
    render(<Ficha inicial="vistas" />, { locale: "en" });

    calificar();

    expect(await aviso("Rated ★ 8")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
  });

  it("sin estado previo tampoco ofrece Undo", async () => {
    render(<Ficha inicial={null} />, { locale: "en" });
    calificar();
    expect(await aviso("Rated ★ 8")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
  });
});

describe("bloqueo mientras se guarda el estado", () => {
  it("con un guardado en curso, favorita y Rate quedan deshabilitados y no mandan otro PUT", async () => {
    let responder!: (valor: unknown) => void;
    api.fetch.mockReturnValue(new Promise((resolver) => (responder = resolver)));
    render(<Ficha inicial="pendientes" />, { locale: "en" });

    elegir(/Watching/);

    // Test: `guardando` llega a TitleActions y deshabilita el resto de las acciones.
    expect(screen.getByRole("button", { name: "Favorite" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Rate/ })).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(screen.getByRole("button", { name: "Favorite" }));
    expect(api.fetch).toHaveBeenCalledTimes(1);
    await act(async () => responder(respuesta("viendo", "pendientes")));
    await aviso("Moved to Watching");
    expect(screen.getByRole("button", { name: "Favorite" })).toBeEnabled();
  });

  it("«Saving…» sale pasados 200 ms, sin Undo, y lo reemplaza el toast de siempre", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let responder!: (valor: unknown) => void;
    api.fetch.mockReturnValue(new Promise((resolver) => (responder = resolver)));
    render(<Ficha inicial="pendientes" />, { locale: "en" });

    elegir(/Watching/);

    await act(async () => void vi.advanceTimersByTime(150));
    expect(screen.queryByText("Saving…")).toBeNull();
    await act(async () => void vi.advanceTimersByTime(100));
    expect(await screen.findByText("Saving…")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();

    await act(async () => responder(respuesta("viendo", "pendientes")));
    await aviso("Moved to Watching");
    expect(screen.queryByText("Saving…")).toBeNull();
    expect(screen.getByRole("button", { name: "Undo" })).toBeEnabled();
  });

  it("el Undo no se puede pulsar mientras el nuevo guardado está en curso", async () => {
    api.fetch.mockResolvedValueOnce(respuesta("viendo", "pendientes"));
    render(<Ficha inicial="pendientes" />, { locale: "en" });
    elegir(/Watching/);
    await aviso("Moved to Watching");
    let responder!: (valor: unknown) => void;
    api.fetch.mockReturnValueOnce(new Promise((resolver) => (responder = resolver)));

    elegir(/Watched/);

    const undo = screen.queryByRole("button", { name: "Undo" });
    if (undo) expect(undo).toBeDisabled();
    await act(async () => responder(respuesta("vistas", "viendo")));
    await aviso("Moved to Watched");
    expect(api.fetch).toHaveBeenCalledTimes(2);
  });
});
