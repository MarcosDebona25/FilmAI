import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, SESION_VENCIDA } from "@/lib/api";
import {
  type EventoChat,
  cargarHistorial,
  combinarMensajes,
  enviarMensaje,
  leerEventos,
  prepararChat,
  rutaHistorial,
} from "@/lib/chat";

/**
 * Un cuerpo de respuesta que llega en pedazos, como en la red. Cada pedazo es
 * texto o bytes sueltos: así se puede cortar en cualquier lugar, incluso en
 * el medio de una letra de dos bytes.
 */
function cuerpo(pedazos: (string | Uint8Array)[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const pedazo of pedazos)
        controller.enqueue(typeof pedazo === "string" ? encoder.encode(pedazo) : pedazo);
      controller.close();
    },
  });
}

const frame = (evento: string, datos: unknown) =>
  `event: ${evento}\ndata: ${JSON.stringify(datos)}\n\n`;

const FIN = frame("fin", { id: 2, id_pregunta: 1 });

async function todos(eventos: AsyncIterable<EventoChat>) {
  const lista: EventoChat[] = [];
  for await (const evento of eventos) lista.push(evento);
  return lista;
}

describe("leerEventos: el parser SSE", () => {
  it("arma un frame que llegó partido entre dos pedazos", async () => {
    const eventos = await todos(
      leerEventos(cuerpo(['event: texto\ndata: {"del', 'ta": "hola"}\n\n', FIN]))
    );
    expect(eventos).toEqual([
      { tipo: "texto", delta: "hola" },
      { tipo: "fin", id: 2, id_pregunta: 1 },
    ]);
  });

  it("no rompe una letra cuyos bytes llegaron en pedazos distintos", async () => {
    const bytes = new TextEncoder().encode(frame("texto", { delta: "año" }));
    // «ñ» ocupa dos bytes en UTF-8: el corte cae entre los dos.
    const corte = bytes.indexOf(0xc3) + 1;
    const eventos = await todos(leerEventos(cuerpo([bytes.slice(0, corte), bytes.slice(corte)])));
    expect(eventos).toEqual([{ tipo: "texto", delta: "año" }]);
  });

  it("ignora eventos desconocidos y datos que no son JSON, y sigue", async () => {
    const eventos = await todos(
      leerEventos(
        cuerpo([
          frame("pensando", { code: "x" }),
          "event: texto\ndata: {roto\n\n",
          frame("estado", { code: "searching" }),
        ])
      )
    );
    expect(eventos).toEqual([{ tipo: "estado", code: "searching" }]);
  });

  it("acepta \\r\\n como fin de línea", async () => {
    const eventos = await todos(
      leerEventos(cuerpo([frame("texto", { delta: "a" }).replaceAll("\n", "\r\n")]))
    );
    expect(eventos).toEqual([{ tipo: "texto", delta: "a" }]);
  });

  it("no pierde el frame si el \\r\\n queda partido entre dos pedazos", async () => {
    const completo = frame("texto", { delta: "a" }).replaceAll("\n", "\r\n");
    // El corte cae entre el `\r` y el `\n` de la línea en blanco que cierra el frame.
    const corte = completo.indexOf("\r\n\r\n") + 3;
    const eventos = await todos(
      leerEventos(cuerpo([completo.slice(0, corte), completo.slice(corte)]))
    );
    expect(eventos).toEqual([{ tipo: "texto", delta: "a" }]);
  });

  it("descarta tarjetas con datos fuera del contrato", async () => {
    const valida = {
      id_tmdb: 1,
      tipo: "movie",
      titulo: "Moon",
      poster: "/m.jpg",
      anio: 2009,
    };
    const eventos = await todos(
      leerEventos(
        cuerpo([
          frame("tarjetas", {
            tarjetas: [
              valida,
              { ...valida, tipo: "/evil.com" },
              { ...valida, id_tmdb: -1 },
              { ...valida, poster: "https://otro-host/x.jpg" },
            ],
          }),
        ])
      )
    );
    expect(eventos).toEqual([{ tipo: "tarjetas", tarjetas: [valida] }]);
  });

  it("entrega las tarjetas y el error con su código", async () => {
    const tarjeta = {
      id_tmdb: 157336,
      tipo: "movie",
      titulo: "Interstellar",
      poster: "/p.jpg",
      anio: 2014,
    };
    const eventos = await todos(
      leerEventos(
        cuerpo([
          frame("tarjetas", { tarjetas: [tarjeta] }),
          frame("error", { code: "chat_unavailable", params: {}, errors: [] }),
        ])
      )
    );
    expect(eventos).toEqual([
      { tipo: "tarjetas", tarjetas: [tarjeta] },
      { tipo: "error", code: "chat_unavailable", params: {}, errors: [] },
    ]);
  });
});

describe("enviarMensaje: el POST con stream", () => {
  let pedidos: string[];
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    pedidos = [];
    document.cookie = "csrftoken=abc";
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "csrftoken=; Max-Age=0";
  });

  const stream = (...pedazos: string[]) =>
    new Response(cuerpo(pedazos), {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });
  const json = (status: number, datos: unknown) => new Response(JSON.stringify(datos), { status });

  /** `fetch` simulado: cada ruta contesta, en orden, lo que arma su función. */
  function backend(rutas: Record<string, (() => Response)[]>) {
    fetchMock.mockImplementation(async (url: string) => {
      const ruta = new URL(url).pathname;
      pedidos.push(ruta);
      const siguiente = rutas[ruta]?.shift();
      return siguiente ? siguiente() : json(200, {});
    });
  }

  it("manda el texto con CSRF, cookies y la señal para cancelar", async () => {
    backend({ "/api/chat/messages/": [() => stream(frame("texto", { delta: "hola" }), FIN)] });
    const control = new AbortController();
    const eventos = await todos(enviarMensaje("¿qué veo?", control.signal));
    expect(eventos.map((evento) => evento.tipo)).toEqual(["texto", "fin"]);
    const [, opciones] = fetchMock.mock.calls[0];
    expect(opciones).toMatchObject({
      method: "POST",
      credentials: "include",
      signal: control.signal,
      body: JSON.stringify({ texto: "¿qué veo?" }),
    });
    expect(opciones.headers["X-CSRFToken"]).toBe("abc");
  });

  it("un stream que se corta sin fin ni error es un error de red", async () => {
    backend({ "/api/chat/messages/": [() => stream(frame("texto", { delta: "a medias" }))] });
    const vistos: EventoChat[] = [];
    const leer = async () => {
      for await (const evento of enviarMensaje("hola", new AbortController().signal))
        vistos.push(evento);
    };
    await expect(leer()).rejects.toMatchObject({ code: "network_error" });
    expect(vistos).toEqual([{ tipo: "texto", delta: "a medias" }]);
  });

  it.each([
    [409, { code: "chat_request_in_progress", params: {}, errors: [] }],
    [429, { code: "throttled", params: { retry_after_seconds: 120 }, errors: [] }],
  ])("un %i antes del stream llega como ApiError con su código", async (status, datos) => {
    backend({ "/api/chat/messages/": [() => json(status, datos)] });
    const error = await todos(enviarMensaje("hola", new AbortController().signal)).catch(
      (e: unknown) => e
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status, code: datos.code, params: datos.params });
  });

  it("un 401 antes del stream renueva la sesión una vez y repite el pedido", async () => {
    backend({
      "/api/chat/messages/": [() => json(401, { code: "not_authenticated" }), () => stream(FIN)],
      "/api/auth/token/refresh/": [() => json(200, {})],
    });
    const eventos = await todos(enviarMensaje("hola", new AbortController().signal));
    expect(eventos).toEqual([{ tipo: "fin", id: 2, id_pregunta: 1 }]);
    expect(pedidos).toEqual([
      "/api/chat/messages/",
      "/api/auth/token/refresh/",
      "/api/chat/messages/",
    ]);
  });

  it("si la sesión no se puede renovar, avisa que venció", async () => {
    const vencida = vi.fn();
    window.addEventListener(SESION_VENCIDA, vencida);
    backend({
      "/api/chat/messages/": [
        () => json(401, { code: "not_authenticated" }),
        () => json(401, { code: "not_authenticated" }),
      ],
      "/api/auth/token/refresh/": [() => json(401, {})],
    });
    await expect(todos(enviarMensaje("hola", new AbortController().signal))).rejects.toMatchObject({
      status: 401,
      code: "not_authenticated",
    });
    expect(vencida).toHaveBeenCalledOnce();
    window.removeEventListener(SESION_VENCIDA, vencida);
  });

  it("cancelar no se confunde con un error de red", async () => {
    const control = new AbortController();
    fetchMock.mockImplementation(async () => {
      control.abort();
      throw new DOMException("Aborted", "AbortError");
    });
    const error = await todos(enviarMensaje("hola", control.signal)).catch((e: unknown) => e);
    expect(error).not.toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ name: "AbortError" });
  });
});

describe("prepararChat", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "csrftoken=; Max-Age=0";
  });

  it("pide la carga del modelo con CSRF", async () => {
    document.cookie = "csrftoken=abc";
    const fetchMock = vi.fn(async () => new Response(null, { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    await prepararChat();
    const [url, opciones] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(new URL(url).pathname).toBe("/api/chat/preparar/");
    expect(opciones).toMatchObject({ method: "POST", credentials: "include" });
    expect((opciones.headers as Record<string, string>)["X-CSRFToken"]).toBe("abc");
  });

  it("si falla, no lanza nada", async () => {
    document.cookie = "csrftoken=abc";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      })
    );
    await expect(prepararChat()).resolves.toBeUndefined();
  });
});

describe("cargarHistorial", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "csrftoken=; Max-Age=0";
  });

  const pagina = (results: unknown[], next: string | null = null) =>
    new Response(JSON.stringify({ next, results }), { status: 200 });

  it("invierte la página (la API manda lo más nuevo primero) y mapea el autor", async () => {
    const tarjeta = { id_tmdb: 1, tipo: "movie", titulo: "Moon", poster: "/p.jpg", anio: 2009 };
    const fetchMock = vi.fn(async () =>
      pagina(
        [
          { id: 4, autor: "chatbot", texto: "Mirá", tarjetas: [tarjeta], fecha_hora: "x" },
          { id: 3, autor: "usuario", texto: "algo", tarjetas: [], fecha_hora: "x" },
        ],
        "https://api.example/api/chat/messages/?cursor=abc"
      )
    );
    vi.stubGlobal("fetch", fetchMock);
    const resultado = await cargarHistorial();
    expect(new URL((fetchMock.mock.calls[0] as unknown as [string])[0]).pathname).toBe(
      "/api/chat/messages/"
    );
    expect(resultado.mensajes).toEqual([
      { id: 3, rol: "usuario", texto: "algo" },
      { id: 4, rol: "asistente", texto: "Mirá", tarjetas: [tarjeta] },
    ]);
    expect(resultado.next).toContain("cursor=abc");
  });

  it("descarta las tarjetas inválidas igual que las del stream", async () => {
    const valida = { id_tmdb: 1, tipo: "movie", titulo: "Moon", poster: null, anio: 2009 };
    const externa = { ...valida, id_tmdb: 2, poster: "https://atacante.example/x.jpg" };
    const rara = { ...valida, id_tmdb: 3, tipo: "game" };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        pagina([{ id: 1, autor: "chatbot", texto: "t", tarjetas: [valida, externa, rara] }])
      )
    );
    const { mensajes } = await cargarHistorial();
    expect(mensajes[0]).toMatchObject({ tarjetas: [valida] });
  });

  it("conserva una tarjeta sin título (el título ya no está en TMDB) para que el panel la marque", async () => {
    const sinTitulo = {
      id_tmdb: 1,
      tipo: "movie",
      titulo: null,
      poster: null,
      anio: null,
      nota_tmdb: null,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => pagina([{ id: 1, autor: "chatbot", texto: "t", tarjetas: [sinTitulo] }]))
    );
    const { mensajes } = await cargarHistorial();
    expect(mensajes[0]).toMatchObject({ tarjetas: [sinTitulo] });
  });

  it("del cursor next solo usa la query: nunca pide a otro origen", async () => {
    expect(rutaHistorial()).toBe("/api/chat/messages/");
    expect(rutaHistorial("https://atacante.example/otra/ruta/?cursor=a%3D")).toBe(
      "/api/chat/messages/?cursor=a%3D"
    );
    const fetchMock = vi.fn(async () => pagina([]));
    vi.stubGlobal("fetch", fetchMock);
    await cargarHistorial("https://atacante.example/x/?cursor=zz");
    const url = new URL((fetchMock.mock.calls[0] as unknown as [string])[0]);
    expect(url.pathname).toBe("/api/chat/messages/");
    expect(url.search).toBe("?cursor=zz");
    expect(url.hostname).not.toBe("atacante.example");
  });

  it("un rechazo llega como ApiError con su código", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () => new Response(JSON.stringify({ code: "not_authenticated" }), { status: 401 })
      )
    );
    await expect(cargarHistorial()).rejects.toMatchObject({ status: 401 });
  });
});

describe("combinarMensajes", () => {
  it("une por id, ordena y no repite", () => {
    const m = (id: number) => ({ id, rol: "usuario" as const, texto: String(id) });
    expect(combinarMensajes([m(3), m(4)], [m(1), m(2), m(3)]).map((x) => x.id)).toEqual([
      1, 2, 3, 4,
    ]);
  });
});
