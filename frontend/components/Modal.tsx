"use client";

import { useEffect, useId, useRef, type ReactNode, type RefObject } from "react";
import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";

/** El diálogo nativo aísla el fondo; la utilidad de foco mantiene Tab dentro. */
export function Modal({
  title,
  children,
  onClose,
  busy = false,
  initialFocusRef,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  busy?: boolean;
  initialFocusRef?: RefObject<HTMLElement | null>;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    dialog?.showModal();
    initialFocusRef?.current?.focus({ preventScroll: true });
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      dialog?.close();
      document.body.style.overflow = previousOverflow;
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    };
  }, [initialFocusRef]);
  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-modal="true"
      onKeyDown={(event) => mantenerFocoEnDialogo(event.nativeEvent, ref.current)}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      className="fixed inset-0 m-auto max-h-[85dvh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto overscroll-contain rounded-xl bg-card p-6 text-foreground shadow-xl backdrop:bg-black/70"
    >
      <h2 id={titleId} className="break-words text-xl font-semibold">
        {title}
      </h2>
      {children}
    </dialog>
  );
}
