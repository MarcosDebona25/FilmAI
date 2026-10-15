"use client";

import { useId, useRef, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";

import { DialogShell } from "@/components/features/title/DialogShell";
import { mensajeDeError } from "@/components/features/title/RatingDialog";
import { useDesborde } from "@/lib/use-desborde";

/**
 * Confirmación antes de una acción que no se puede deshacer (borrar el texto,
 * quitar la calificación, quitar de Vistas una producción calificada). Es un
 * `alertdialog`: el foco arranca en Cancelar, así Enter no borra nada por
 * error. Si `onConfirm` falla, el error queda a la vista.
 */
export function ConfirmDialog({
  titulo,
  descripcion,
  preview,
  confirmar,
  onConfirm,
  onCancel,
}: {
  titulo: string;
  descripcion?: ReactNode;
  preview?: string | null;
  confirmar: string;
  onConfirm: () => Promise<void>;
  onCancel: () => void;
}) {
  const t = useTranslations("common");
  const tituloId = useId();
  const descripcionId = useId();
  const cancelar = useRef<HTMLButtonElement>(null);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completa, setCompleta] = useState(false);
  const [vistaPrevia, desborda] = useDesborde<HTMLQuoteElement>(completa, preview ?? "");

  async function aceptar() {
    setEnviando(true);
    setError(null);
    try {
      await onConfirm();
    } catch (motivo) {
      setError(mensajeDeError(motivo));
      setEnviando(false);
    }
  }

  return (
    <DialogShell
      role="alertdialog"
      labelledBy={tituloId}
      describedBy={descripcion ? descripcionId : undefined}
      onClose={onCancel}
      busy={enviando}
      initialFocus={() => cancelar.current}
      ancho="md:w-[min(520px,calc(100%-2rem))]"
    >
      <h2 id={tituloId} className="font-display text-[30px] leading-none md:text-[34px]">
        {titulo}
      </h2>
      {descripcion && (
        <p id={descripcionId} className="leading-[1.6] text-pretty">
          {descripcion}
        </p>
      )}
      {preview && (
        <div className="flex flex-col items-start gap-1">
          <blockquote
            ref={vistaPrevia}
            className={`rounded-[10px] bg-background px-4 py-3 text-[15px] leading-[1.55] text-fg-2 ${completa ? "" : "line-clamp-2"}`}
          >
            {preview}
          </blockquote>
          {(desborda || completa) && (
            <button
              type="button"
              aria-expanded={completa}
              onClick={() => setCompleta(!completa)}
              className="cursor-pointer text-sm font-semibold text-fg-2 hover:text-foreground"
            >
              {completa ? t("text.readLess") : t("text.readMore")}
            </button>
          )}
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="mt-2 grid grid-cols-2 gap-2.5 md:flex md:justify-end">
        <button
          ref={cancelar}
          type="button"
          onClick={onCancel}
          disabled={enviando}
          className="h-[52px] cursor-pointer rounded-lg px-4 font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring md:h-12 md:font-medium md:shadow-none"
        >
          {t("actions.cancel")}
        </button>
        <button
          type="button"
          onClick={aceptar}
          disabled={enviando}
          className="h-[52px] cursor-pointer rounded-lg bg-destructive px-[22px] md:h-12 font-semibold text-on-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-60"
        >
          {confirmar}
        </button>
      </div>
    </DialogShell>
  );
}
