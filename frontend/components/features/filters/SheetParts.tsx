"use client";

import type { ReactNode } from "react";
import { X } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

/** Título y «Cerrar» de las hojas de filtros de celular (Buscar y reseñas). */
export function SheetHeader({
  id,
  titulo,
  onClose,
}: {
  id: string;
  titulo: ReactNode;
  onClose: () => void;
}) {
  const t = useTranslations("common.actions");
  return (
    <div className="-mt-2 flex items-center justify-between">
      <h2 id={id} className="font-display text-[30px] leading-none">
        {titulo}
      </h2>
      <button
        type="button"
        onClick={onClose}
        aria-label={t("close")}
        className="-mr-2.5 grid size-11 cursor-pointer place-items-center text-fg-2 focus-visible:outline-2 focus-visible:outline-ring"
      >
        <X aria-hidden="true" className="size-5" />
      </button>
    </div>
  );
}

/**
 * Botones de opción única («Todas», «Con reseña»…): el activo va resaltado y
 * con `aria-pressed`. `null` es la opción «todas». `className` fija columnas y
 * redondeo del grupo.
 */
export function SegmentedPills<T extends string>({
  opciones,
  valor,
  onCambiar,
  etiqueta,
  etiquetaAccesible,
  className,
}: {
  opciones: (T | null)[];
  valor: T | null;
  onCambiar: (valor: T | null) => void;
  etiqueta: (opcion: T | null) => ReactNode;
  etiquetaAccesible?: (opcion: T | null) => string;
  className?: string;
}) {
  return (
    <div
      className={cn("grid gap-1 bg-background p-1 shadow-[inset_0_0_0_1px_var(--line)]", className)}
    >
      {opciones.map((opcion) => {
        const activa = valor === opcion;
        return (
          <button
            key={opcion ?? ""}
            type="button"
            aria-label={etiquetaAccesible?.(opcion)}
            aria-pressed={activa}
            onClick={() => onCambiar(opcion)}
            className={cn(
              "h-10 cursor-pointer rounded-full px-1.5 text-sm whitespace-nowrap focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
              activa
                ? "bg-selected font-semibold text-selected-foreground"
                : "font-medium text-fg-2"
            )}
          >
            {etiqueta(opcion)}
          </button>
        );
      })}
    </div>
  );
}

/** «Limpiar» y la acción principal (que solo cierra) al pie de la hoja. */
export function SheetFooter({
  onLimpiar,
  onAplicar,
  aplicar,
}: {
  onLimpiar: () => void;
  onAplicar: () => void;
  aplicar: ReactNode;
}) {
  const t = useTranslations("common.actions");
  return (
    <div className="mt-0.5 grid grid-cols-[auto_minmax(0,1fr)] gap-2.5">
      <button
        type="button"
        onClick={onLimpiar}
        className="h-[52px] cursor-pointer rounded-[10px] px-[18px] font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-ring"
      >
        {t("clear")}
      </button>
      <button
        type="button"
        onClick={onAplicar}
        className="h-[52px] cursor-pointer rounded-[10px] bg-primary font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        {aplicar}
      </button>
    </div>
  );
}
