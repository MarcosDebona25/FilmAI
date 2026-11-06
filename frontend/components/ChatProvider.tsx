"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";

import { useAccount } from "@/components/AccountProvider";
import { ApiError } from "@/lib/api";
import { enviarMensaje, prepararChat, type Tarjeta } from "@/lib/chat";
import type { ErrorParams } from "@/lib/errors";

export type MensajeChat =
  | { id: string; rol: "usuario"; texto: string }
  | { id: string; rol: "asistente"; texto: string; tarjetas: Tarjeta[] };

/** La respuesta que se está escribiendo; todavía no es parte de la conversación. */
export type TurnoEnCurso = {
  pregunta: string;
  respuesta: string;
  /** Código de `estado` (hoy solo `searching`); se borra cuando llega texto. */
  estado: string | null;
};

/** Se guarda el código y no el texto: así cambia de idioma junto con la interfaz. */
export type AvisoChat =
  { tipo: "cancelado" } | { tipo: "error"; code: string; params: ErrorParams };

type ChatContextValue = {
  /** Hay sesión: sin ella el FAB está deshabilitado y no se pide nada. */
  habilitado: boolean;
  abierto: boolean;
  abrir: () => void;
  cerrar: () => void;
  mensajes: MensajeChat[];
  enCurso: TurnoEnCurso | null;
  aviso: AvisoChat | null;
  /** Texto de la última respuesta completa, para la región `aria-live`. */
  anuncio: string;
  borrador: string;
  setBorrador: (texto: string) => void;
  enviar: () => void;
  cancelar: () => void;
  /** El FAB: al cerrar el panel el foco vuelve ahí. */
  fabRef: RefObject<HTMLButtonElement | null>;
};

const ChatContext = createContext<ChatContextValue | null>(null);

/** Quita los símbolos de Markdown para que el lector de pantalla no los lea. */
function textoPlano(markdown: string) {
  return markdown
    .replace(/[*_`#>~]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

let siguienteId = 0;
const nuevoId = () => `m${++siguienteId}`;

/**
 * Estado del chat (B-04). Vive en `app/layout.tsx`, que Next no desmonta al
 * navegar: la conversación y una respuesta a medio escribir sobreviven al
 * cambio de página (spec `chat-ui`, «One chat, available everywhere»).
 */
export function ChatProvider({ children }: { children: React.ReactNode }) {
  const { perfil } = useAccount();
  const habilitado = perfil !== null;

  const [abierto, setAbierto] = useState(false);
  const [mensajes, setMensajes] = useState<MensajeChat[]>([]);
  const [enCurso, setEnCurso] = useState<TurnoEnCurso | null>(null);
  const [aviso, setAviso] = useState<AvisoChat | null>(null);
  const [anuncio, setAnuncio] = useState("");
  const [borrador, setBorrador] = useState("");
  const fabRef = useRef<HTMLButtonElement>(null);

  // Refs y no estado: se leen y cambian en el mismo instante del clic, sin
  // esperar a que React vuelva a dibujar. `turnoRef` numera cada envío; un
  // evento de un turno que ya no es el actual (porque se canceló) se descarta.
  const turnoRef = useRef(0);
  const activoRef = useRef<{ turno: number; control: AbortController; pregunta: string } | null>(
    null
  );

  /** Cierra el turno sin respuesta: la pregunta vuelve al input si está vacío. */
  const terminarSinRespuesta = useCallback((nuevoAviso: AvisoChat) => {
    const activo = activoRef.current;
    if (!activo) return;
    activoRef.current = null;
    turnoRef.current += 1;
    setEnCurso(null);
    setAviso(nuevoAviso);
    setBorrador((actual) => (actual.trim() ? actual : activo.pregunta));
  }, []);

  const cancelar = useCallback(() => {
    const activo = activoRef.current;
    if (!activo) return; // Ya llegó `fin`: no hay nada que cancelar.
    terminarSinRespuesta({ tipo: "cancelado" });
    activo.control.abort();
  }, [terminarSinRespuesta]);

  const enviar = useCallback(() => {
    const pregunta = borrador.trim();
    if (!pregunta || activoRef.current || !habilitado) return;

    const turno = ++turnoRef.current;
    const control = new AbortController();
    activoRef.current = { turno, control, pregunta };
    setBorrador("");
    setAviso(null);
    setEnCurso({ pregunta, respuesta: "", estado: null });

    void (async () => {
      let respuesta = "";
      let tarjetas: Tarjeta[] = [];
      const vigente = () => turnoRef.current === turno;
      try {
        for await (const evento of enviarMensaje(pregunta, control.signal)) {
          if (!vigente()) return;
          if (evento.tipo === "estado") {
            setEnCurso((actual) => actual && { ...actual, estado: evento.code });
          } else if (evento.tipo === "texto") {
            respuesta += evento.delta;
            const parcial = respuesta;
            setEnCurso((actual) => actual && { ...actual, respuesta: parcial, estado: null });
          } else if (evento.tipo === "tarjetas") {
            tarjetas = evento.tarjetas;
          } else if (evento.tipo === "fin") {
            activoRef.current = null;
            setEnCurso(null);
            setMensajes((anteriores) => [
              ...anteriores,
              { id: nuevoId(), rol: "usuario", texto: pregunta },
              { id: nuevoId(), rol: "asistente", texto: respuesta, tarjetas },
            ]);
            setAnuncio(textoPlano(respuesta));
            return;
          } else {
            terminarSinRespuesta({ tipo: "error", code: evento.code, params: evento.params });
            return;
          }
        }
      } catch (error) {
        if (!vigente() || control.signal.aborted) return;
        terminarSinRespuesta(
          error instanceof ApiError
            ? { tipo: "error", code: error.code, params: error.params }
            : { tipo: "error", code: "unknown", params: {} }
        );
      }
    })();
  }, [borrador, habilitado, terminarSinRespuesta]);

  const abrir = useCallback(() => {
    if (!habilitado) return;
    setAbierto(true);
    // Sin `await`: el modelo carga mientras el usuario escribe (6.3b).
    void prepararChat();
  }, [habilitado]);

  const cerrar = useCallback(() => setAbierto(false), []);

  // Al cerrar la sesión la conversación no queda a la vista del próximo usuario.
  useEffect(() => {
    if (habilitado) return;
    activoRef.current?.control.abort();
    activoRef.current = null;
    turnoRef.current += 1;
    setAbierto(false);
    setMensajes([]);
    setEnCurso(null);
    setAviso(null);
    setAnuncio("");
    setBorrador("");
  }, [habilitado]);

  const valor = useMemo<ChatContextValue>(
    () => ({
      habilitado,
      abierto,
      abrir,
      cerrar,
      mensajes,
      enCurso,
      aviso,
      anuncio,
      borrador,
      setBorrador,
      enviar,
      cancelar,
      fabRef,
    }),
    [
      habilitado,
      abierto,
      abrir,
      cerrar,
      mensajes,
      enCurso,
      aviso,
      anuncio,
      borrador,
      enviar,
      cancelar,
    ]
  );

  return <ChatContext.Provider value={valor}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) throw new Error("useChat requires ChatProvider");
  return context;
}
