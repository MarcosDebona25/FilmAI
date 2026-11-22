/**
 * Estilo único del campo de texto de búsqueda (21/11/2026): lo usan la lupa de la
 * navbar (`NavbarSearch`) y la página Buscar (`SearchView`), en escritorio y en
 * celular. Son solo clases; cada uno conserva su comportamiento.
 */
export const CAMPO_BUSQUEDA = {
  /** Píldora del canvas (sección 13): con foco, borde `--fg-3` y un anillo de 2 px por fuera. */
  pildora:
    "flex h-11 items-center rounded-full bg-raised pl-3 shadow-[inset_0_0_0_1px_var(--field-border)] focus-within:shadow-[inset_0_0_0_1px_var(--fg-3),0_0_0_2px_var(--ring)]",
  icono: "mr-2 size-5 shrink-0 text-fg-3",
  input:
    "h-full min-w-0 flex-1 border-0 bg-transparent pr-1 text-[0.9375rem] font-medium text-foreground outline-none placeholder:text-fg-3",
  limpiar:
    "grid size-11 shrink-0 cursor-pointer place-items-center rounded-full text-fg-3 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
  iconoLimpiar: "size-[1.125rem]",
} as const;
