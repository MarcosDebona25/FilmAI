"use client";

import { Toaster } from "sonner";

import { useEscritorio } from "@/lib/use-escritorio";

/**
 * Dónde salen los avisos. En escritorio, arriba al centro. En celular, todos
 * abajo, 12 px sobre la barra de pestañas (`MobileTabs`, 4,75 rem de alto): así
 * ninguno la tapa. Sonner pasa a «móvil» con 600 px, pero la barra de pestañas
 * está hasta 768 px, por eso la separación va en `offset` y en `mobileOffset`.
 */
const SOBRE_LA_BARRA = { bottom: "calc(4.75rem + 12px)" };

export function AppToaster() {
  const escritorio = useEscritorio();
  // Un solo `<Toaster>`: cambiar de medida no pierde los avisos que ya salieron.
  return (
    <Toaster
      position={escritorio ? "top-center" : "bottom-center"}
      offset={escritorio ? undefined : SOBRE_LA_BARRA}
      mobileOffset={escritorio ? undefined : SOBRE_LA_BARRA}
    />
  );
}
