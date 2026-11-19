"use client";

import { useSyncExternalStore } from "react";
import { Check, CircleAlert, LoaderCircle, Undo2 } from "lucide-react";
import { toast } from "sonner";

/** Todos los avisos de estado comparten id: el segundo reemplaza al primero. */
export const ID_AVISO_ESTADO = "estado-ficha";

/** Cuánto dura un aviso con Undo, y los demás (canvas: «Watching · title page»). */
export const MS_CON_UNDO = 6000;
export const MS_SIMPLE = 2000;

export interface AvisoEstado {
  texto: string;
  tono?: "ok" | "error";
  /** Milisegundos que se queda; por defecto, los del tipo de aviso. */
  ms?: number;
  /**
   * Una acción más, antes de Undo (en la lista Watching: «Rate it»). Quien la
   * pasa decide si cierra el aviso. Solo se muestra junto con `deshacer`.
   */
  accion?: { etiqueta: string; onClick: () => void };
  /** Con esto el aviso lleva el botón Undo y dura 6 s. */
  deshacer?: {
    etiqueta: string;
    /** Lo que se anuncia a lectores de pantalla («… Undo available for 6 seconds.»). */
    anuncio: string;
    onClick: () => void;
  };
  /**
   * Un guardado en curso: spinner y texto, sin acciones. Dura hasta que el
   * guardado termina (`cerrarAvisoEstado`).
   */
  cargando?: boolean;
}

/**
 * Mientras hay un guardado en curso, el Undo (y el «Rate it») del aviso visible
 * no se pueden pulsar: el toque se perdería. El estado vive acá, fuera de React,
 * porque el aviso se dibuja desde `toast.custom` y tiene que enterarse sin que
 * el hook que guarda lo vuelva a crear.
 */
let accionesBloqueadas = false;
const oyentes = new Set<() => void>();

function suscribir(oyente: () => void) {
  oyentes.add(oyente);
  return () => oyentes.delete(oyente);
}

/** Bloquea (o desbloquea) los botones del aviso de estado visible. */
export function bloquearAccionesDelAviso(bloqueadas: boolean) {
  if (accionesBloqueadas === bloqueadas) return;
  accionesBloqueadas = bloqueadas;
  for (const oyente of oyentes) oyente();
}

let secuencia = 0;

function Aviso({ aviso, vuelta }: { aviso: AvisoEstado; vuelta: number }) {
  const { texto, tono = "ok", deshacer, cargando = false } = aviso;
  const bloqueado = useSyncExternalStore(
    suscribir,
    () => accionesBloqueadas,
    () => false
  );
  const Icono = cargando ? LoaderCircle : tono === "error" ? CircleAlert : Check;
  return (
    <div
      role={cargando ? "status" : undefined}
      aria-live={cargando ? "polite" : undefined}
      className="relative box-border flex w-[min(22.25rem,calc(100vw-2rem))] items-center gap-3 rounded-xl bg-raised py-3 pr-3.5 pl-4 text-[0.9375rem] text-foreground shadow-[0_12px_32px_rgb(0_0_0/0.5),inset_0_0_0_1px_var(--line)]"
    >
      <Icono
        aria-hidden="true"
        strokeWidth={tono === "error" ? 2 : 2.5}
        className={`size-[1.125rem] shrink-0 ${
          cargando
            ? "motion-safe:animate-spin"
            : tono === "error"
              ? "text-destructive"
              : "text-[var(--ok)]"
        }`}
      />
      {deshacer && !cargando ? (
        <>
          <strong aria-hidden="true" className="min-w-0 flex-1 font-semibold">
            {texto}
          </strong>
          <span className="sr-only">{deshacer.anuncio}</span>
          {aviso.accion && (
            <button
              type="button"
              disabled={bloqueado}
              onClick={aviso.accion.onClick}
              className="inline-flex h-9 cursor-pointer items-center rounded-lg px-3 text-sm font-semibold text-primary focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-wait disabled:opacity-50"
            >
              {aviso.accion.etiqueta}
            </button>
          )}
          <button
            type="button"
            disabled={bloqueado}
            onClick={deshacer.onClick}
            className="inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-sm font-semibold text-primary shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-wait disabled:opacity-50"
          >
            <Undo2 aria-hidden="true" className="size-[0.9375rem]" />
            {deshacer.etiqueta}
          </button>
          {/* El tiempo que queda. `key`: cada aviso nuevo reinicia la barra. */}
          <span
            key={vuelta}
            aria-hidden="true"
            style={{ animationDuration: `${aviso.ms ?? MS_CON_UNDO}ms` }}
            className="aviso-barra absolute bottom-0 left-3.5 h-0.5 rounded-sm bg-primary opacity-85"
          />
        </>
      ) : (
        <strong className="min-w-0 flex-1 font-semibold">{texto}</strong>
      )}
    </div>
  );
}

/** Muestra (o reemplaza) el aviso de estado (ficha y lista Watching). */
export function mostrarAvisoEstado(aviso: AvisoEstado) {
  const vuelta = ++secuencia;
  toast.custom(() => <Aviso aviso={aviso} vuelta={vuelta} />, {
    id: ID_AVISO_ESTADO,
    // El de guardado no se va solo: lo cierra `terminar()` del hook compartido.
    duration: aviso.cargando ? Infinity : (aviso.ms ?? (aviso.deshacer ? MS_CON_UNDO : MS_SIMPLE)),
  });
}

/** Cierra el aviso (al salir de la página el cambio queda, sin Undo). */
export function cerrarAvisoEstado() {
  toast.dismiss(ID_AVISO_ESTADO);
}
