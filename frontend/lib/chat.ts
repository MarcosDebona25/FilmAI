/**
 * El chat con el asistente (B-04): el `POST` que devuelve la respuesta como
 * stream SSE y el parser que la convierte en eventos. El contrato está en
 * `openspec/changes/chatbot/design.md`, «The SSE contract».
 *
 * No se usa `EventSource` (el lector SSE del navegador) porque solo hace
 * `GET`, sin cuerpo y sin headers: el chat necesita `POST` con el texto y el
 * header `X-CSRFToken`. Se usa `fetch` y se lee `res.body` a mano.
 */
import { ApiError, apiFetch, pedirConSesion } from "@/lib/api";
import type { ErrorParams, FieldError } from "@/lib/errors";

/** Tope de caracteres de un mensaje: el mismo que valida el backend (09/10/2026). */
export const MAX_MENSAJE = 500;

/** Una producción recomendada, igual en el evento `tarjetas` y en el historial. */
export type Tarjeta = {
  id_tmdb: number;
  tipo: "movie" | "tv";
  titulo: string;
  /** Ruta de TMDB (`/abc.jpg`); la URL la arma `tmdbImage`. */
  poster: string | null;
  anio: number | null;
  /** Promedio de TMDB. Opcional: las tarjetas guardadas antes de sumarlo no lo traen. */
  nota_tmdb?: number | null;
};

export type EventoChat =
  | { tipo: "estado"; code: string }
  | { tipo: "texto"; delta: string }
  | { tipo: "tarjetas"; tarjetas: Tarjeta[] }
  | { tipo: "fin"; id: number; id_pregunta: number }
  | { tipo: "error"; code: string; params: ErrorParams; errors: FieldError[] };

type Datos = Record<string, unknown>;

/** Una tarjeta tal como la puede usar el front: `href` y `src` salen de acá. */
function esTarjeta(valor: unknown): valor is Tarjeta {
  if (!valor || typeof valor !== "object") return false;
  const tarjeta = valor as Record<string, unknown>;
  return (
    (tarjeta.tipo === "movie" || tarjeta.tipo === "tv") &&
    typeof tarjeta.id_tmdb === "number" &&
    Number.isInteger(tarjeta.id_tmdb) &&
    tarjeta.id_tmdb > 0 &&
    typeof tarjeta.titulo === "string" &&
    (tarjeta.poster === null ||
      (typeof tarjeta.poster === "string" && tarjeta.poster.startsWith("/"))) &&
    (tarjeta.anio === null ||
      (typeof tarjeta.anio === "number" && Number.isInteger(tarjeta.anio))) &&
    (tarjeta.nota_tmdb === undefined ||
      tarjeta.nota_tmdb === null ||
      typeof tarjeta.nota_tmdb === "number")
  );
}

/** Convierte un frame (`event: x` + `data: {...}`) en un evento; `null` si no se reconoce. */
function parsearFrame(frame: string): EventoChat | null {
  let nombre = "";
  const lineasDeDatos: string[] = [];
  for (const linea of frame.split("\n")) {
    if (linea.startsWith("event:")) nombre = linea.slice(6).trim();
    else if (linea.startsWith("data:")) lineasDeDatos.push(linea.slice(5).trimStart());
  }
  let datos: Datos;
  try {
    datos = JSON.parse(lineasDeDatos.join("\n"));
  } catch {
    return null;
  }
  if (!datos || typeof datos !== "object") return null;
  switch (nombre) {
    case "estado":
      return typeof datos.code === "string" ? { tipo: "estado", code: datos.code } : null;
    case "texto":
      return typeof datos.delta === "string" ? { tipo: "texto", delta: datos.delta } : null;
    case "tarjetas": {
      if (!Array.isArray(datos.tarjetas)) return null;
      const tarjetas = datos.tarjetas.filter(esTarjeta);
      return tarjetas.length ? { tipo: "tarjetas", tarjetas } : null;
    }
    case "fin":
      return typeof datos.id === "number" && typeof datos.id_pregunta === "number"
        ? { tipo: "fin", id: datos.id, id_pregunta: datos.id_pregunta }
        : null;
    case "error":
      return {
        tipo: "error",
        code: typeof datos.code === "string" ? datos.code : "unknown",
        params:
          datos.params && typeof datos.params === "object" ? (datos.params as ErrorParams) : {},
        errors: Array.isArray(datos.errors) ? (datos.errors as FieldError[]) : [],
      };
    default:
      // Un evento que este panel no conoce se ignora: el backend puede sumar
      // eventos sin romper a los paneles viejos.
      return null;
  }
}

/**
 * Lee un cuerpo SSE y entrega los eventos de a uno (`for await`).
 *
 * La red corta los bytes donde quiere, no donde termina un frame. Por eso se
 * acumula texto en `buffer` y solo se procesa hasta la última línea en blanco;
 * lo que queda es un frame incompleto que espera al próximo pedazo. El
 * `TextDecoder` con `stream: true` hace lo mismo con las letras: si una «ñ»
 * (dos bytes) quedó partida, guarda el primer byte hasta que llegue el otro.
 */
export async function* leerEventos(cuerpo: ReadableStream<Uint8Array>): AsyncGenerator<EventoChat> {
  const lector = cuerpo.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await lector.read();
      if (done) break;
      buffer = (buffer + decoder.decode(value, { stream: true })).replaceAll("\r\n", "\n");
      let corte: number;
      while ((corte = buffer.indexOf("\n\n")) !== -1) {
        const evento = parsearFrame(buffer.slice(0, corte));
        buffer = buffer.slice(corte + 2);
        if (evento) yield evento;
      }
    }
  } finally {
    // Si quien lee corta antes (llegó `fin`, o se canceló), se suelta el stream.
    lector.cancel().catch(() => {});
  }
}

/**
 * Manda un mensaje y entrega los eventos de la respuesta a medida que llegan.
 *
 * - Antes del stream, un rechazo (400, 401, 403, 409, 429) llega como
 *   `ApiError`, igual que en `apiFetch`. Un 401 (Unauthorized) renueva la
 *   sesión una vez (`pedirConSesion`).
 * - Durante el stream, el error llega como evento `error` (el status 200 (OK)
 *   ya se mandó y no se puede cambiar).
 * - Si el stream se corta sin `fin` ni `error`, es un error de red: no se sabe
 *   si la respuesta estaba completa (09/10/2026).
 * - Cancelar (`signal`) rechaza con el `AbortError` del navegador, nunca con
 *   un `ApiError`: quien llama lo distingue y no muestra un error.
 */
export async function* enviarMensaje(
  texto: string,
  signal: AbortSignal
): AsyncGenerator<EventoChat> {
  const res = await pedirConSesion("/api/chat/messages/", {
    method: "POST",
    body: JSON.stringify({ texto }),
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    signal,
  });
  if (!res.ok || !res.body) {
    const datos = await res.json().catch(() => null);
    throw new ApiError(res.status, datos);
  }
  try {
    for await (const evento of leerEventos(res.body)) {
      yield evento;
      if (evento.tipo === "fin" || evento.tipo === "error") return;
    }
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiError(0, { code: "network_error" });
  }
  throw new ApiError(0, { code: "network_error" });
}

/**
 * Pide que el modelo se cargue mientras el usuario escribe (6.3b). No se
 * espera ni se muestra nada: si falla, la pregunta igual funciona, solo que
 * la primera respuesta puede tardar más.
 */
export async function prepararChat(): Promise<void> {
  await pedirConSesion("/api/chat/preparar/", { method: "POST" }).catch(() => {});
}

/** Un mensaje de la conversación, del historial o recién terminado. El `id` es el de la base. */
export type MensajeChat =
  | { id: number; rol: "usuario"; texto: string }
  | { id: number; rol: "asistente"; texto: string; tarjetas: Tarjeta[] };

export type PaginaHistorial = {
  /** De más viejo a más nuevo, listos para mostrar en orden. */
  mensajes: MensajeChat[];
  /** Cursor de la página anterior (más vieja); `null` si no quedan más. */
  next: string | null;
};

type MensajeApi = {
  id: number;
  autor: "usuario" | "chatbot";
  texto: string;
  tarjetas?: unknown;
};

const RUTA_HISTORIAL = "/api/chat/messages/";

/**
 * Del cursor `next` que manda la API solo se reutiliza la query: nunca se
 * pide a un origen recibido de la red (se mandarían las cookies de sesión).
 */
export function rutaHistorial(next?: string | null) {
  if (!next) return RUTA_HISTORIAL;
  return `${RUTA_HISTORIAL}${new URL(next, "http://filmai.local").search}`;
}

/**
 * Una página del historial (`GET /api/chat/messages/`). La API la entrega de
 * más nuevo a más viejo; acá se invierte para que el panel la dibuje en orden.
 * Las tarjetas pasan por el mismo filtro que las del stream.
 */
export async function cargarHistorial(next?: string | null): Promise<PaginaHistorial> {
  const pagina = await apiFetch<{ next: string | null; results: MensajeApi[] }>(
    rutaHistorial(next)
  );
  const mensajes = pagina.results
    .map((m): MensajeChat => {
      if (m.autor === "usuario") return { id: m.id, rol: "usuario", texto: m.texto };
      const tarjetas = Array.isArray(m.tarjetas) ? m.tarjetas.filter(esTarjeta) : [];
      return { id: m.id, rol: "asistente", texto: m.texto, tarjetas };
    })
    .reverse();
  return { mensajes, next: pagina.next };
}

/** Une mensajes por id (los de `nuevos` pisan a los repetidos) y deja el orden por id. */
export function combinarMensajes(actuales: MensajeChat[], nuevos: MensajeChat[]) {
  const porId = new Map(actuales.map((m) => [m.id, m]));
  for (const m of nuevos) porId.set(m.id, m);
  return [...porId.values()].sort((a, b) => a.id - b.id);
}
