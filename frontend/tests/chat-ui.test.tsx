import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EventoChat } from "@/lib/chat";
import { ApiError } from "@/lib/api";
import { act, fireEvent, render, screen, waitFor, within } from "./render";

const cuenta = vi.hoisted(() => ({ perfil: { pk: 1, nombre: "Juan" } as object | null }));
vi.mock("@/components/AccountProvider", () => ({ useAccount: () => cuenta }));
const nav = vi.hoisted(() => ({ pathname: "/home" }));
vi.mock("next/navigation", () => ({ usePathname: () => nav.pathname }));

const chat = vi.hoisted(() => ({
  enviarMensaje: vi.fn(),
  prepararChat: vi.fn(),
  cargarHistorial: vi.fn(),
}));
vi.mock("@/lib/chat", async (original) => ({ ...(await original()), ...chat }));

import { ChatProvider } from "@/components/ChatProvider";
import { ChatFab } from "@/components/features/chat/ChatFab";
import { ChatPanel } from "@/components/features/chat/ChatPanel";

function Chat() {
  return (
    <ChatProvider>
      <ChatFab />
      <ChatPanel />
    </ChatProvider>
  );
}

/** Un stream que entrega los eventos dados y espera a que el test lo suelte. */
function respuesta(eventos: EventoChat[]) {
  let soltar = () => {};
  const listo = new Promise<void>((resolver) => (soltar = resolver));
  chat.enviarMensaje.mockImplementation(async function* () {
    await listo;
    yield* eventos;
  });
  return () => soltar();
}

const FIN: EventoChat = { tipo: "fin", id: 2, id_pregunta: 1 };

describe("el chat en pantalla", () => {
  beforeEach(() => {
    cuenta.perfil = { pk: 1, nombre: "Juan" };
    nav.pathname = "/home";
    chat.prepararChat.mockResolvedValue(undefined);
    chat.cargarHistorial.mockReset();
    chat.cargarHistorial.mockResolvedValue({ mensajes: [], next: null });
  });

  it("sin sesión el FAB está deshabilitado y no pide nada", async () => {
    cuenta.perfil = null;
    render(<Chat />);
    const fab = screen.getByRole("button", { name: "Preguntale a FilmAI" });
    expect(fab).toBeDisabled();
    await userEvent.click(fab);
    expect(chat.prepararChat).not.toHaveBeenCalled();
  });

  it("no aparece en las pantallas de acceso", () => {
    nav.pathname = "/login";
    render(<Chat />);
    expect(screen.queryByRole("button", { name: "Preguntale a FilmAI" })).toBeNull();
  });

  it("solo con el teclado: abre, envía con Enter y Escape devuelve el foco al FAB", async () => {
    const usuario = userEvent.setup();
    const soltar = respuesta([{ tipo: "texto", delta: "Probá *Moon*" }, FIN]);
    render(<Chat />);
    const fab = screen.getByRole("button", { name: "Preguntale a FilmAI" });
    fab.focus();
    await usuario.keyboard("{Enter}");
    const campo = screen.getByRole("textbox", { name: "Tu mensaje" });
    expect(campo).toHaveFocus();
    expect(chat.prepararChat).toHaveBeenCalledOnce();

    await usuario.keyboard("Algo corto");
    await usuario.keyboard("{Enter}");
    expect(chat.enviarMensaje).toHaveBeenCalledWith("Algo corto", expect.any(AbortSignal));
    soltar();
    await screen.findByText("Moon");

    // jsdom no traduce Escape en el evento `cancel` del <dialog>: se dispara a mano.
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
    await waitFor(() => expect(fab).toHaveFocus());
  });

  it("Mayús+Enter hace un salto de línea y no envía", async () => {
    const usuario = userEvent.setup();
    render(<Chat />);
    await usuario.click(screen.getByRole("button", { name: "Preguntale a FilmAI" }));
    await usuario.keyboard("una{Shift>}{Enter}{/Shift}dos");
    expect(screen.getByRole("textbox", { name: "Tu mensaje" })).toHaveValue("una\ndos");
    expect(chat.enviarMensaje).not.toHaveBeenCalled();
  });

  it("al pegar 600 caracteres queda en 500 y el contador muestra el tope", async () => {
    const usuario = userEvent.setup();
    render(<Chat />);
    await usuario.click(screen.getByRole("button", { name: "Preguntale a FilmAI" }));
    const campo = screen.getByRole("textbox", { name: "Tu mensaje" });
    expect(campo).toHaveAttribute("maxLength", "500");
    await usuario.click(campo);
    await usuario.paste("x".repeat(600));
    expect(campo).toHaveValue("x".repeat(500));
    expect(screen.getByText("500/500")).toBeInTheDocument();
  });

  it("mientras responde, el botón es Cancelar y al cancelar avisa y devuelve la pregunta", async () => {
    const usuario = userEvent.setup();
    respuesta([]); // Nunca se suelta: la respuesta queda en curso.
    render(<Chat />);
    await usuario.click(screen.getByRole("button", { name: "Preguntale a FilmAI" }));
    await usuario.keyboard("Una serie{Enter}");
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.getByRole("status")).toHaveTextContent("Solicitud cancelada");
    expect(screen.getByRole("textbox", { name: "Tu mensaje" })).toHaveValue("Una serie");
    expect(screen.getByRole("button", { name: "Enviar" })).toBeInTheDocument();
  });

  it("muestra «Buscando en el catálogo…» con el estado searching", async () => {
    const usuario = userEvent.setup();
    const soltar = respuesta([{ tipo: "estado", code: "searching" }]);
    render(<Chat />);
    await usuario.click(screen.getByRole("button", { name: "Preguntale a FilmAI" }));
    await usuario.keyboard("Algo{Enter}");
    soltar();
    expect(await screen.findByText("Buscando en el catálogo…")).toBeInTheDocument();
  });

  it("un error del stream se muestra traducido por su código", async () => {
    const usuario = userEvent.setup();
    const soltar = respuesta([
      { tipo: "texto", delta: "parcial" },
      { tipo: "error", code: "chat_unavailable", params: {}, errors: [] },
    ]);
    render(<Chat />);
    await usuario.click(screen.getByRole("button", { name: "Preguntale a FilmAI" }));
    await usuario.keyboard("Algo{Enter}");
    soltar();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No podemos procesar tu solicitud. Intentá más tarde."
    );
    expect(screen.queryByText("parcial")).toBeNull();
  });

  it("la región aria-live recibe la respuesta una vez, completa, al llegar fin", async () => {
    const usuario = userEvent.setup();
    // Los eventos se sueltan de a uno, como llegan de la red: si salieran todos
    // juntos, React los dibujaría en un solo render y el test no vería los parciales.
    const pasos: (() => void)[] = [];
    const esperar = () => new Promise<void>((seguir) => pasos.push(seguir));
    chat.enviarMensaje.mockImplementation(async function* () {
      await esperar();
      yield { tipo: "texto", delta: "Uno, " } satisfies EventoChat;
      await esperar();
      yield { tipo: "texto", delta: "dos" } satisfies EventoChat;
      await esperar();
      yield FIN;
    });
    const siguiente = async () => {
      await waitFor(() => expect(pasos.length).toBeGreaterThan(0));
      pasos.shift()!();
    };
    const { container } = render(<Chat />);
    await usuario.click(screen.getByRole("button", { name: "Preguntale a FilmAI" }));
    // `role="log"` anuncia por su cuenta: se anula para que el aviso sea único.
    expect(screen.getByRole("log")).toHaveAttribute("aria-live", "off");
    await usuario.keyboard("Algo{Enter}");
    const region = container.querySelector('[aria-live="polite"]')!;
    const cambios: string[] = [];
    new MutationObserver(() => cambios.push(region.textContent ?? "")).observe(region, {
      childList: true,
      characterData: true,
      subtree: true,
    });
    await siguiente();
    await screen.findByText("Uno,");
    await siguiente();
    await screen.findByText("Uno, dos");
    await siguiente();
    await waitFor(() => expect(region).toHaveTextContent("Uno, dos"));
    expect(cambios).toEqual(["Uno, dos"]);
  });

  it("las tarjetas llevan a la ficha con ?from=chat", async () => {
    const usuario = userEvent.setup();
    const soltar = respuesta([
      { tipo: "texto", delta: "Mirá" },
      {
        tipo: "tarjetas",
        tarjetas: [
          { id_tmdb: 157336, tipo: "movie", titulo: "Interstellar", poster: "/p.jpg", anio: 2014 },
        ],
      },
      FIN,
    ]);
    render(<Chat />);
    await usuario.click(screen.getByRole("button", { name: "Preguntale a FilmAI" }));
    await usuario.keyboard("Algo{Enter}");
    soltar();
    const link = await screen.findByRole("link", { name: /Interstellar/ });
    expect(link).toHaveAttribute("href", "/movie/157336?from=chat");
  });

  it("el anuncio lee el texto del link pero no su URL", async () => {
    const usuario = userEvent.setup();
    const soltar = respuesta([{ tipo: "texto", delta: "Mirá [Moon](https://ejemplo/x)" }, FIN]);
    const { container } = render(<Chat />);
    await usuario.click(screen.getByRole("button", { name: "Preguntale a FilmAI" }));
    await usuario.keyboard("Algo{Enter}");
    soltar();
    await waitFor(() =>
      expect(container.querySelector('[aria-live="polite"]')).toHaveTextContent("Mirá Moon")
    );
    expect(container.querySelector('[aria-live="polite"]')).not.toHaveTextContent("ejemplo");
  });

  describe("bienvenida e historial", () => {
    const abrir = async () => {
      const usuario = userEvent.setup();
      render(<Chat />);
      await usuario.click(screen.getByRole("button", { name: "Preguntale a FilmAI" }));
      return usuario;
    };

    it("sin mensajes muestra la bienvenida con el nombre y tres sugerencias, sin llamar al modelo", async () => {
      await abrir();
      expect(
        await screen.findByText(/¡Hola, Juan! Contame qué tenés ganas de ver/)
      ).toBeInTheDocument();
      const sugerencias = screen.getByRole("list", { name: "Sugerencias" });
      expect(within(sugerencias).getAllByRole("button")).toHaveLength(3);
      expect(chat.enviarMensaje).not.toHaveBeenCalled();
    });

    it("un clic en una sugerencia la envía y la bienvenida desaparece", async () => {
      const usuario = await abrir();
      respuesta([]);
      await usuario.click(await screen.findByRole("button", { name: "Una serie para maratonear" }));
      expect(chat.enviarMensaje).toHaveBeenCalledWith(
        "Una serie para maratonear",
        expect.any(AbortSignal)
      );
      expect(screen.queryByRole("list", { name: "Sugerencias" })).toBeNull();
    });

    it("con historial no hay bienvenida y se muestra la conversación en orden", async () => {
      chat.cargarHistorial.mockResolvedValue({
        mensajes: [
          { id: 1, rol: "usuario", texto: "algo corto" },
          { id: 2, rol: "asistente", texto: "Probá **Moon**", tarjetas: [] },
        ],
        next: null,
      });
      await abrir();
      expect(await screen.findByText("algo corto")).toBeInTheDocument();
      expect(screen.getByText("Moon")).toBeInTheDocument();
      expect(screen.queryByRole("list", { name: "Sugerencias" })).toBeNull();
    });

    it("si el historial falla muestra el error traducido y reintentar lo vuelve a pedir", async () => {
      chat.cargarHistorial
        .mockRejectedValueOnce(new ApiError(0, { code: "network_error" }))
        .mockResolvedValueOnce({
          mensajes: [{ id: 1, rol: "usuario", texto: "volvió" }],
          next: null,
        });
      const usuario = await abrir();
      expect(await screen.findByRole("alert")).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: "Reintentar" }));
      expect(await screen.findByText("volvió")).toBeInTheDocument();
      expect(screen.queryByRole("alert")).toBeNull();
    });

    it("al llegar arriba del todo pide las páginas anteriores", async () => {
      let alVerCentinela: ((entradas: { isIntersecting: boolean }[]) => void) | null = null;
      vi.stubGlobal(
        "IntersectionObserver",
        class {
          constructor(callback: (entradas: { isIntersecting: boolean }[]) => void) {
            alVerCentinela = callback;
          }
          observe() {}
          disconnect() {}
        }
      );
      try {
        chat.cargarHistorial
          .mockResolvedValueOnce({
            mensajes: [{ id: 3, rol: "usuario", texto: "reciente" }],
            next: "c1",
          })
          .mockResolvedValueOnce({
            mensajes: [{ id: 1, rol: "usuario", texto: "antiguo" }],
            next: null,
          });
        await abrir();
        await screen.findByText("reciente");
        await waitFor(() => expect(alVerCentinela).not.toBeNull());
        act(() => alVerCentinela!([{ isIntersecting: true }]));
        expect(await screen.findByText("antiguo")).toBeInTheDocument();
        expect(chat.cargarHistorial).toHaveBeenLastCalledWith("c1");
        const textos = screen.getAllByText(/reciente|antiguo/).map((n) => n.textContent);
        expect(textos).toEqual(["antiguo", "reciente"]);
      } finally {
        vi.unstubAllGlobals();
      }
    });
  });

  describe("badge de respuesta sin leer", () => {
    it("se enciende si la respuesta termina con el panel cerrado y se apaga al abrir", async () => {
      const usuario = userEvent.setup();
      const soltar = respuesta([{ tipo: "texto", delta: "Listo" }, FIN]);
      render(<Chat />);
      const fab = screen.getByRole("button", { name: "Preguntale a FilmAI" });
      await usuario.click(fab);
      await usuario.keyboard("Algo{Enter}");
      fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
      expect(screen.queryByText("Hay una respuesta nueva")).toBeNull();
      soltar();
      expect(await screen.findByText("Hay una respuesta nueva")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Preguntale a FilmAI.*Hay una respuesta nueva/ })
      ).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: /Preguntale a FilmAI/ }));
      expect(screen.queryByText("Hay una respuesta nueva")).toBeNull();
    });
  });
});
