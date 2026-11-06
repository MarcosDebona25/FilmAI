import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EventoChat } from "@/lib/chat";
import { fireEvent, render, screen, waitFor } from "./render";

const cuenta = vi.hoisted(() => ({ perfil: { pk: 1 } as object | null }));
vi.mock("@/components/AccountProvider", () => ({ useAccount: () => cuenta }));
const nav = vi.hoisted(() => ({ pathname: "/home" }));
vi.mock("next/navigation", () => ({ usePathname: () => nav.pathname }));

const chat = vi.hoisted(() => ({ enviarMensaje: vi.fn(), prepararChat: vi.fn() }));
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
    cuenta.perfil = { pk: 1 };
    nav.pathname = "/home";
    chat.prepararChat.mockResolvedValue(undefined);
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
});
