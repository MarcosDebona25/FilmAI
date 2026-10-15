"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";

/**
 * Caja de los diálogos de la ficha (canvas). Usa el `<dialog>` nativo, como
 * `components/Modal.tsx`: `showModal()` deja inerte el fondo, Escape cierra y,
 * al desmontarse, el foco vuelve a quien lo abrió. En escritorio es una tarjeta
 * centrada; en celular, una hoja que sube desde abajo.
 */
export function DialogShell({
  role = "dialog",
  labelledBy,
  describedBy,
  onClose,
  busy = false,
  initialFocus,
  ancho = "md:w-[min(560px,calc(100%-2rem))]",
  children,
}: {
  role?: "dialog" | "alertdialog";
  labelledBy: string;
  describedBy?: string;
  onClose: () => void;
  busy?: boolean;
  initialFocus?: (dialog: HTMLDialogElement) => HTMLElement | null;
  ancho?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  // En un ref para que el efecto corra una sola vez aunque la función cambie.
  const foco = useRef(initialFocus);
  foco.current = initialFocus;

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
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
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
      className={`mx-0 mt-auto mb-0 flex max-h-[90dvh] w-full max-w-none flex-col gap-5 overflow-y-auto overscroll-contain rounded-t-2xl border-0 bg-raised p-5 pb-[max(20px,env(safe-area-inset-bottom))] text-foreground shadow-[0_30px_80px_rgb(0_0_0/0.5)] backdrop:bg-black/60 md:m-auto md:rounded-2xl md:p-7 ${ancho}`}
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
