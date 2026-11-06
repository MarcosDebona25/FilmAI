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
import {
  cargarHistorial,
  combinarMensajes,
  enviarMensaje,
  prepararChat,
  type MensajeChat,
  type Tarjeta,
} from "@/lib/chat";
import type { ErrorParams } from "@/lib/errors";

export type { MensajeChat };

/**
 * Estado del historial guardado en el servidor. `sin-cargar` es antes de la
 * primera apertura; `error` conserva el código para mostrarlo traducido.
 */
export type HistorialChat = {
  estado: "sin-cargar" | "cargando" | "listo" | "error";
  /** Cursor de la página más vieja que falta; `null` si ya se trajo todo. */
  next: string | null;
  error: { code: string; params: ErrorParams } | null;
  /** Se está pidiendo una página anterior (no la primera). */
  cargandoAnteriores: boolean;
};

const HISTORIAL_INICIAL: HistorialChat = {
  estado: "sin-cargar",
  next: null,
  error: null,
  cargandoAnteriores: false,
};

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
  historial: HistorialChat;
  /** Una respuesta terminó con el panel cerrado: enciende el badge del FAB. */
  noLeido: boolean;
  /** Trae la página anterior del historial (al subir el scroll). */
  cargarAnteriores: () => void;
  /** Reintenta la carga del historial que falló. */
  reintentarHistorial: () => void;
  /** Texto de la última respuesta completa, para la región `aria-live`. */
  anuncio: string;
  borrador: string;
  setBorrador: (texto: string) => void;
  /** Sin argumento envía el borrador; con texto (una sugerencia) lo envía directo. */
  enviar: (texto?: string) => void;
  cancelar: () => void;
  /** El FAB: al cerrar el panel el foco vuelve ahí. */
  fabRef: RefObject<HTMLButtonElement | null>;
};

const ChatContext = createContext<ChatContextValue | null>(null);

/** Quita los símbolos de Markdown para que el lector de pantalla no los lea. */
function textoPlano(markdown: string) {
  return (
    markdown
      // De un link o una imagen queda solo su texto: la URL no se anuncia.
      .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
      .replace(/[*_`#>~]/g, "")
      .replace(/\s+/g, " ")
      .trim()
  );
}

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
  const [historial, setHistorial] = useState<HistorialChat>(HISTORIAL_INICIAL);
  const [noLeido, setNoLeido] = useState(false);
  const [borrador, setBorrador] = useState("");
  const fabRef = useRef<HTMLButtonElement>(null);

  // Lo que el loop del stream y las cargas necesitan leer sin quedar con un
  // valor viejo de la closure.
  const abiertoRef = useRef(false);
  const historialRef = useRef(HISTORIAL_INICIAL);
  /** Hubo una página reciente cargada alguna vez (con éxito). */
  const cargadoRef = useRef(false);
  /** Un cancel pudo dejar un mensaje guardado: la próxima apertura vuelve a pedir lo reciente. */
  const recargarTrasCancelarRef = useRef(false);
  /** Cuenta las sesiones: una carga que vuelve después de cerrar sesión se descarta. */
  const sesionRef = useRef(0);
  const cargandoRef = useRef(false);
  /** Qué pedido falló por última vez: «Reintentar» repite ese y no otro. */
  const fallaronAnterioresRef = useRef(false);
  /**
   * Una apertura quiso refrescar lo reciente mientras volvía una página vieja:
   * el refresco corre cuando esa carga termina, en vez de perderse.
   */
  const refrescoPendienteRef = useRef(false);
  /** `cargar` se llama a sí misma para correr el refresco pendiente. */
  const cargarRef = useRef<(anteriores: boolean) => Promise<void>>(async () => {});

  const actualizarHistorial = useCallback((cambio: Partial<HistorialChat>) => {
    historialRef.current = { ...historialRef.current, ...cambio };
    setHistorial(historialRef.current);
  }, []);

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
    // El servidor pudo guardar la respuesta antes de enterarse (CU-014):
    // la próxima apertura vuelve a pedir lo reciente para mostrarla.
    recargarTrasCancelarRef.current = true;
    terminarSinRespuesta({ tipo: "cancelado" });
    activo.control.abort();
  }, [terminarSinRespuesta]);

  const enviar = useCallback(
    (texto?: string) => {
      // Una sugerencia no pasa por el borrador: lo que el usuario escribió queda.
      const directo = typeof texto === "string";
      const pregunta = (directo ? texto : borrador).trim();
      if (!pregunta || activoRef.current || !habilitado) return;

      const turno = ++turnoRef.current;
      const control = new AbortController();
      activoRef.current = { turno, control, pregunta };
      if (!directo) setBorrador("");
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
              // Ids de la base: así el historial que se pida después no repite estos mensajes.
              setMensajes((anteriores) =>
                combinarMensajes(anteriores, [
                  { id: evento.id_pregunta, rol: "usuario", texto: pregunta },
                  { id: evento.id, rol: "asistente", texto: respuesta, tarjetas },
                ])
              );
              setAnuncio(textoPlano(respuesta));
              if (!abiertoRef.current) setNoLeido(true);
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
    },
    [borrador, habilitado, terminarSinRespuesta]
  );

  /**
   * Carga una página del historial. Sin `anteriores` es la más reciente (la
   * primera vez o tras un cancel); con `anteriores` es la que sigue hacia atrás.
   */
  const cargar = useCallback(
    async (anteriores: boolean) => {
      if (cargandoRef.current) return;
      const sesion = sesionRef.current;
      cargandoRef.current = true;
      const primera = !cargadoRef.current;
      // El refresco tras un cancel se da por hecho recién cuando arranca.
      if (!anteriores) recargarTrasCancelarRef.current = false;
      actualizarHistorial(
        anteriores
          ? { cargandoAnteriores: true, error: null }
          : { estado: primera ? "cargando" : historialRef.current.estado, error: null }
      );
      try {
        const pagina = await cargarHistorial(anteriores ? historialRef.current.next : null);
        if (sesion !== sesionRef.current) return;
        setMensajes((actuales) => combinarMensajes(actuales, pagina.mensajes));
        cargadoRef.current = true;
        actualizarHistorial({
          estado: "listo",
          cargandoAnteriores: false,
          // Al refrescar lo reciente se conserva el cursor de las páginas viejas ya pedidas.
          next: anteriores || primera ? pagina.next : historialRef.current.next,
        });
      } catch (error) {
        if (sesion !== sesionRef.current) return;
        fallaronAnterioresRef.current = anteriores;
        // Si falló el refresco tras un cancel, la próxima apertura lo vuelve a pedir.
        if (!anteriores && !primera) recargarTrasCancelarRef.current = true;
        actualizarHistorial({
          estado: cargadoRef.current ? "listo" : "error",
          cargandoAnteriores: false,
          error:
            error instanceof ApiError
              ? { code: error.code, params: error.params }
              : { code: "unknown", params: {} },
        });
      } finally {
        if (sesion === sesionRef.current) {
          cargandoRef.current = false;
          const pendiente = refrescoPendienteRef.current;
          refrescoPendienteRef.current = false;
          if (pendiente && anteriores) void cargarRef.current(false);
        }
      }
    },
    [actualizarHistorial]
  );

  useEffect(() => {
    cargarRef.current = cargar;
  }, [cargar]);

  const cargarAnteriores = useCallback(() => {
    const { next, estado } = historialRef.current;
    if (estado !== "listo" || !next) return;
    void cargar(true);
  }, [cargar]);

  const reintentarHistorial = useCallback(() => {
    // La primera carga fallida o el refresco tras un cancel piden lo reciente;
    // solo una página vieja fallida vuelve a pedir la anterior.
    void cargar(cargadoRef.current && fallaronAnterioresRef.current);
  }, [cargar]);

  const abrir = useCallback(() => {
    if (!habilitado) return;
    abiertoRef.current = true;
    setAbierto(true);
    setNoLeido(false);
    // Sin `await`: el modelo carga mientras el usuario escribe (6.3b).
    void prepararChat();
    if (!cargadoRef.current || recargarTrasCancelarRef.current) {
      // Si hay una página vieja en vuelo, `cargar` la descartaría: queda pendiente.
      if (cargandoRef.current) refrescoPendienteRef.current = true;
      else void cargar(false);
    } else if (historialRef.current.error) {
      // El aviso de una página vieja que falló no reaparece en cada apertura.
      actualizarHistorial({ error: null });
    }
  }, [habilitado, cargar, actualizarHistorial]);

  const cerrar = useCallback(() => {
    abiertoRef.current = false;
    setAbierto(false);
  }, []);

  // Al cerrar la sesión la conversación no queda a la vista del próximo usuario.
  useEffect(() => {
    if (habilitado) return;
    activoRef.current?.control.abort();
    activoRef.current = null;
    turnoRef.current += 1;
    sesionRef.current += 1;
    abiertoRef.current = false;
    cargadoRef.current = false;
    cargandoRef.current = false;
    recargarTrasCancelarRef.current = false;
    refrescoPendienteRef.current = false;
    fallaronAnterioresRef.current = false;
    historialRef.current = HISTORIAL_INICIAL;
    setHistorial(HISTORIAL_INICIAL);
    setNoLeido(false);
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
      historial,
      noLeido,
      cargarAnteriores,
      reintentarHistorial,
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
      historial,
      noLeido,
      cargarAnteriores,
      reintentarHistorial,
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
