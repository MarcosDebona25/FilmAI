"use client";

import { useEffect, useRef, type ReactNode, type RefObject } from "react";

import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";

/**
 * Caja de los diálogos de la ficha (canvas). Usa el `<dialog>` nativo, como
 * `components/Modal.tsx`: `showModal()` deja inerte el fondo, Escape cierra y,
 * al desmontarse, el foco vuelve a quien lo abrió. Con `cerrarConFondo`, un toque
 * en el fondo, fuera de la caja, también cierra (nunca en un `alertdialog` ni con
 * `busy`). Es opcional a propósito: en calificar, reseñar o renombrar, un toque sin
 * querer borraría lo escrito (19/11/2026). En escritorio
 * es una tarjeta centrada; en celular, una hoja que sube desde abajo.
 */
export function DialogShell({
  role = "dialog",
  labelledBy,
  describedBy,
  onClose,
  busy = false,
  initialFocus,
  returnFocus,
  cerrarConFondo = false,
  ancho = "md:w-[min(35rem,calc(100%-2rem))]",
  relleno = "gap-5 p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] md:p-7",
  children,
}: {
  role?: "dialog" | "alertdialog";
  labelledBy: string;
  describedBy?: string;
  onClose: () => void;
  busy?: boolean;
  initialFocus?: (dialog: HTMLDialogElement) => HTMLElement | null;
  /**
   * El elemento que recibe el foco al cerrar. Sin él, el que lo tenía al abrir:
   * en Safari un clic no enfoca el botón y ese sería el `body`.
   */
  returnFocus?: RefObject<HTMLElement | null>;
  /** Cerrar al tocar fuera de la caja. Solo para diálogos sin nada que perder. */
  cerrarConFondo?: boolean;
  ancho?: string;
  /** Separación y relleno de la caja, para los diálogos que traen el suyo. */
  relleno?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  // En un ref para que el efecto corra una sola vez aunque la función cambie.
  const foco = useRef(initialFocus);
  foco.current = initialFocus;
  const devolver = useRef(returnFocus);
  devolver.current = returnFocus;

  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    if (!dialog) return;
    dialog.showModal();
    foco.current?.(dialog)?.focus({ preventScroll: true });
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      dialog.close();
      document.body.style.overflow = overflow;
      const destino = devolver.current?.current ?? trigger;
      if (destino?.isConnected) destino.focus({ preventScroll: true });
    };
  }, []);

  return (
    <dialog
      ref={ref}
      role={role === "alertdialog" ? "alertdialog" : undefined}
      aria-modal="true"
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      onKeyDown={(event) => mantenerFocoEnDialogo(event.nativeEvent, ref.current)}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      onClick={(event) => {
        // El fondo (`::backdrop`) cuenta como un clic en el `<dialog>`, igual que
        // su propio relleno: solo es «fuera» si cae fuera de su caja.
        const dialog = ref.current;
        if (!cerrarConFondo || busy || role === "alertdialog") return;
        if (!dialog || event.target !== dialog) return;
        const caja = dialog.getBoundingClientRect();
        const { clientX: x, clientY: y } = event;
        if (x < caja.left || x > caja.right || y < caja.top || y > caja.bottom) onClose();
      }}
      className={`mx-0 mt-auto mb-0 flex max-h-[90dvh] w-full max-w-none flex-col overflow-y-auto overscroll-contain rounded-t-2xl border-0 bg-raised text-foreground shadow-[0_30px_80px_rgb(0_0_0/0.5)] backdrop:bg-black/60 md:m-auto md:rounded-2xl ${relleno} ${ancho}`}
    >
      {/* Agarre de la hoja en celular: solo decorativo. */}
      <span
        aria-hidden="true"
        className="mx-auto -mt-1 h-1 w-10 shrink-0 rounded-full bg-line md:hidden"
      />
      {children}
    </dialog>
  );
}
