"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

const BOTON = {
  // Ficha, Buscar, Perfil y Ajustes.
  cuadrado:
    "inline-flex h-12 cursor-pointer items-center rounded-lg bg-raised-2 px-[22px] font-semibold focus-visible:outline-2 focus-visible:outline-ring",
  // «Calificaciones y reseñas», con los botones redondos del canvas.
  pildora:
    "h-11 cursor-pointer rounded-full bg-raised-2 px-[18px] font-semibold focus-visible:outline-2 focus-visible:outline-ring",
};

/**
 * Un error de carga con «Retry». `alertaEnTexto` anuncia solo el mensaje (sin
 * el botón): así lo hacían la ficha y Buscar, y el resto anuncia el bloque.
 */
export function ErrorRetry({
  mensaje,
  onReintentar,
  boton = "cuadrado",
  alertaEnTexto = false,
  className,
}: {
  mensaje: ReactNode;
  onReintentar: () => void;
  boton?: keyof typeof BOTON;
  alertaEnTexto?: boolean;
  className?: string;
}) {
  const t = useTranslations("common.actions");
  return (
    <div
      role={alertaEnTexto ? undefined : "alert"}
      className={cn("flex flex-col items-start gap-3", className)}
    >
      <p role={alertaEnTexto ? "alert" : undefined} className="text-fg-2">
        {mensaje}
      </p>
      <button type="button" onClick={onReintentar} className={BOTON[boton]}>
        {t("retry")}
      </button>
    </div>
  );
}
