// Clases compartidas: viven fuera de un módulo "use client" para poder usarse
// también desde componentes de servidor.
export const primaryButtonClass =
  "flex h-[52px] w-full items-center justify-center rounded-[10px] bg-primary text-base font-semibold text-primary-foreground no-underline hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-wait disabled:opacity-70";

export const secondaryButtonClass =
  "flex h-[52px] w-full items-center justify-center gap-3 rounded-[10px] bg-secondary text-base font-semibold text-foreground no-underline hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring";
