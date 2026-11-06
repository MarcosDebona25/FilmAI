import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import type { EventoChat } from "@/lib/chat";

const cuenta = vi.hoisted(() => ({ perfil: { pk: 1 } as object | null }));
vi.mock("@/components/AccountProvider", () => ({ useAccount: () => cuenta }));

const chat = vi.hoisted(() => ({ enviarMensaje: vi.fn(), prepararChat: vi.fn() }));
vi.mock("@/lib/chat", async (original) => ({ ...(await original()), ...chat }));

import { ChatProvider, useChat } from "@/components/ChatProvider";

/**
 * Un stream que el test maneja a mano: cada `empujar` entrega un evento
 * cuando el test lo decide. Así se puede probar el orden exacto entre un
 * clic en «Cancelar» y la llegada de `fin`.
 */
function streamControlado() {
  const cola: (EventoChat | Error)[] = [];
  let despertar: (() => void) | null = null;
  let cerrado = false;
  let senal: AbortSignal | null = null;
  return {
    empujar(evento: EventoChat | Error) {
      cola.push(evento);
      despertar?.();
    },
    cerrar() {
      cerrado = true;
      despertar?.();
    },
    get senal() {
      return senal;
    },
    async *generar(_texto: string, signal: AbortSignal): AsyncGenerator<EventoChat> {
      senal = signal;
      while (true) {
        // Como `leerEventos`: lo que ya llegó al buffer sale aunque se haya
        // cancelado; el abort recién se nota al esperar más datos de la red.
        const siguiente = cola.shift();
        if (siguiente instanceof Error) throw siguiente;
        if (siguiente) {
          yield siguiente;
          continue;
        }
        if (signal.aborted) throw new DOMException("Aborted", "AbortError");
        if (cerrado) return;
        await new Promise<void>((listo) => {
          despertar = listo;
          signal.addEventListener("abort", () => listo(), { once: true });
        });
        despertar = null;
      }
    },
  };
}

const wrapper = ({ children }: { children: ReactNode }) => <ChatProvider>{children}</ChatProvider>;
const FIN: EventoChat = { tipo: "fin", id: 2, id_pregunta: 1 };

describe("ChatProvider: un turno del chat", () => {
  let stream: ReturnType<typeof streamControlado>;

  beforeEach(() => {
    cuenta.perfil = { pk: 1 };
    stream = streamControlado();
    chat.enviarMensaje.mockImplementation(stream.generar);
    chat.prepararChat.mockResolvedValue(undefined);
  });

  /** Escribe la pregunta y la envía, como el input. */
  function preguntar(result: { current: ReturnType<typeof useChat> }, texto = "¿Qué veo?") {
    act(() => result.current.setBorrador(texto));
    act(() => result.current.enviar());
  }

  it("arma la respuesta con los deltas y la cierra con fin", async () => {
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result);
    expect(result.current.borrador).toBe("");
    act(() => stream.empujar({ tipo: "estado", code: "searching" }));
    await waitFor(() => expect(result.current.enCurso?.estado).toBe("searching"));
    act(() => {
      stream.empujar({ tipo: "texto", delta: "Te dejo " });
      stream.empujar({ tipo: "texto", delta: "**Moon**" });
    });
    await waitFor(() => expect(result.current.enCurso?.respuesta).toBe("Te dejo **Moon**"));
    act(() => stream.empujar(FIN));
    await waitFor(() => expect(result.current.enCurso).toBeNull());
    expect(result.current.mensajes).toMatchObject([
      { rol: "usuario", texto: "¿Qué veo?" },
      { rol: "asistente", texto: "Te dejo **Moon**", tarjetas: [] },
    ]);
    // Se anuncia una sola vez, entera y sin los símbolos de Markdown.
    expect(result.current.anuncio).toBe("Te dejo Moon");
  });

  it("no envía un mensaje vacío ni uno de solo espacios", () => {
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result, "   ");
    expect(chat.enviarMensaje).not.toHaveBeenCalled();
  });

  it("no envía otra pregunta mientras hay una respuesta en curso", () => {
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result);
    preguntar(result, "otra");
    expect(chat.enviarMensaje).toHaveBeenCalledTimes(1);
    expect(result.current.borrador).toBe("otra");
  });

  it("cancelar aborta, descarta lo parcial y devuelve la pregunta al input", async () => {
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result);
    act(() => stream.empujar({ tipo: "texto", delta: "a medias" }));
    await waitFor(() => expect(result.current.enCurso?.respuesta).toBe("a medias"));
    act(() => result.current.cancelar());
    expect(stream.senal?.aborted).toBe(true);
    expect(result.current.enCurso).toBeNull();
    expect(result.current.mensajes).toEqual([]);
    expect(result.current.aviso).toEqual({ tipo: "cancelado" });
    expect(result.current.borrador).toBe("¿Qué veo?");
  });

  it("al cancelar no pisa lo que el usuario escribió mientras esperaba", () => {
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result);
    act(() => result.current.setBorrador("mejor otra cosa"));
    act(() => result.current.cancelar());
    expect(result.current.borrador).toBe("mejor otra cosa");
  });

  it("si Cancelar se procesa antes que fin, gana Cancelar (CU-014 2.A)", async () => {
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result);
    act(() => stream.empujar({ tipo: "texto", delta: "completa" }));
    await waitFor(() => expect(result.current.enCurso?.respuesta).toBe("completa"));
    // `fin` ya está en camino, pero el clic se procesa antes.
    act(() => {
      stream.empujar(FIN);
      result.current.cancelar();
    });
    await act(async () => {});
    expect(result.current.mensajes).toEqual([]);
    expect(result.current.aviso).toEqual({ tipo: "cancelado" });
  });

  it("si fin se procesa primero, el clic posterior no cancela nada", async () => {
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result);
    act(() => {
      stream.empujar({ tipo: "texto", delta: "lista" });
      stream.empujar(FIN);
    });
    await waitFor(() => expect(result.current.enCurso).toBeNull());
    act(() => result.current.cancelar());
    expect(result.current.mensajes).toHaveLength(2);
    expect(result.current.aviso).toBeNull();
  });

  it("un error después de algunos deltas borra lo parcial y conserva la pregunta", async () => {
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result);
    act(() => stream.empujar({ tipo: "texto", delta: "empiezo y" }));
    await waitFor(() => expect(result.current.enCurso?.respuesta).toBe("empiezo y"));
    act(() => stream.empujar({ tipo: "error", code: "chat_unavailable", params: {}, errors: [] }));
    await waitFor(() => expect(result.current.enCurso).toBeNull());
    expect(result.current.mensajes).toEqual([]);
    expect(result.current.aviso).toEqual({ tipo: "error", code: "chat_unavailable", params: {} });
    expect(result.current.borrador).toBe("¿Qué veo?");
  });

  it("un rechazo antes del stream (409) se muestra con su código", async () => {
    chat.enviarMensaje.mockImplementation(async function* () {
      yield* [];
      throw new ApiError(409, { code: "chat_request_in_progress" });
    });
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result);
    await waitFor(() =>
      expect(result.current.aviso).toEqual({
        tipo: "error",
        code: "chat_request_in_progress",
        params: {},
      })
    );
  });

  it("guarda las tarjetas con la respuesta", async () => {
    const tarjeta = {
      id_tmdb: 1,
      tipo: "movie" as const,
      titulo: "Moon",
      poster: null,
      anio: 2009,
    };
    const { result } = renderHook(useChat, { wrapper });
    preguntar(result);
    act(() => {
      stream.empujar({ tipo: "texto", delta: "Mirá" });
      stream.empujar({ tipo: "tarjetas", tarjetas: [tarjeta] });
      stream.empujar(FIN);
    });
    await waitFor(() => expect(result.current.enCurso).toBeNull());
    expect(result.current.mensajes[1]).toMatchObject({ rol: "asistente", tarjetas: [tarjeta] });
  });
});

describe("ChatProvider: abrir el panel", () => {
  beforeEach(() => {
    chat.prepararChat.mockResolvedValue(undefined);
  });

  it("cada apertura pide preparar el modelo, sin esperar la respuesta", () => {
    cuenta.perfil = { pk: 1 };
    chat.prepararChat.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(useChat, { wrapper });
    act(() => result.current.abrir());
    expect(result.current.abierto).toBe(true);
    act(() => result.current.cerrar());
    act(() => result.current.abrir());
    expect(chat.prepararChat).toHaveBeenCalledTimes(2);
  });

  it("sin sesión no abre ni pide nada", () => {
    cuenta.perfil = null;
    const { result } = renderHook(useChat, { wrapper });
    expect(result.current.habilitado).toBe(false);
    act(() => result.current.abrir());
    expect(result.current.abierto).toBe(false);
    expect(chat.prepararChat).not.toHaveBeenCalled();
  });
});
