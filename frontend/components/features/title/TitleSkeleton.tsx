import { cn } from "@/lib/utils";

// `raised-2`: los bloques van sobre la franja de fondo, que ya es `raised`.
export const ESQUELETO = "rounded bg-raised-2";
export const VELO_CELULAR =
  "linear-gradient(0deg, rgb(var(--scrim)) 0%, rgb(var(--scrim) / 0.2) 60%), linear-gradient(180deg, rgb(var(--scrim) / 0.85) 0%, rgb(var(--scrim) / 0) 30%)";
export const VELO_ESCRITORIO =
  "linear-gradient(0deg, rgb(var(--scrim)) 0%, rgb(var(--scrim) / 0.85) 30%, rgb(var(--scrim) / 0.2) 70%), linear-gradient(180deg, rgb(var(--scrim) / 0.8) 0%, rgb(var(--scrim) / 0) 24%)";

/**
 * Esqueleto de la ficha (C-07). Lo comparten `TitleView`, mientras llega el
 * detalle, y los `loading.tsx` de /movie/[id] y /tv/[id], que Next muestra en
 * el instante del clic, antes de que el servidor responda la página.
 *
 * Son componentes sin estado ni hooks, a propósito: así sirven igual desde el
 * servidor (`loading.tsx`) y desde el cliente (`TitleView`), y la forma del
 * esqueleto vive en un solo lugar.
 */

/** Título, lema y metadatos. */
export function EsqueletoEncabezado() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-3 md:gap-5">
      <span className={cn(ESQUELETO, "h-12 w-3/4 md:mb-[0.9375rem] md:h-[6.75rem] md:w-2/3")} />
      <span className={cn(ESQUELETO, "hidden h-6 w-1/3 md:block")} />
      <span className={cn(ESQUELETO, "h-4 w-2/3 md:h-5 md:w-1/2")} />
    </div>
  );
}

/** Misma forma que las acciones: calificar y las cuatro listas. */
export function EsqueletoAcciones() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-3 md:flex-row md:items-center md:gap-2.5">
      <span className={cn(ESQUELETO, "h-[3.25rem] rounded-lg md:h-12 md:w-[6.5rem]")} />
      <span className="grid grid-cols-4 gap-2 md:contents">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className={cn(ESQUELETO, "h-16 rounded-lg md:h-12 md:w-32")} />
        ))}
      </span>
    </div>
  );
}

/** Géneros y sinopsis. */
export function EsqueletoDetalle() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-8 md:gap-6">
      <span className="flex gap-2">
        {["w-20", "w-24", "w-16"].map((ancho) => (
          <span key={ancho} className={cn(ESQUELETO, "h-[1.875rem] rounded-full md:h-8", ancho)} />
        ))}
      </span>
      <span className="flex flex-col gap-3 md:max-w-[45rem]">
        <span className={cn(ESQUELETO, "mb-1 h-3 w-20")} />
        {["w-full", "w-full", "w-11/12", "w-2/3"].map((ancho, i) => (
          <span key={i} className={cn(ESQUELETO, "h-4", ancho)} />
        ))}
      </span>
    </div>
  );
}

/** La ficha entera sin datos: lo que muestran los `loading.tsx`. */
export function TitleSkeleton() {
  return (
    <main id="contenido" aria-busy="true" className="pb-16">
      <div data-imagen-bajo-navbar className="relative h-[17.5rem] overflow-hidden md:h-[38.75rem]">
        <div className="absolute inset-0 bg-raised" />
        <div
          aria-hidden="true"
          className="absolute inset-0 md:hidden"
          style={{ background: VELO_CELULAR }}
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 hidden md:block"
          style={{ background: VELO_ESCRITORIO }}
        />
      </div>

      <div className="relative page-container -mt-24 flex flex-col gap-16 md:-mt-[23.75rem] md:gap-24">
        <div className="grid grid-cols-[7.25rem_minmax(0,1fr)] items-end gap-x-4 gap-y-6 md:grid-cols-[18.75rem_minmax(0,1fr)] md:items-start md:gap-x-14">
          <div className="relative aspect-[2/3] overflow-hidden rounded-[0.625rem] bg-raised-2 shadow-[0_14px_34px_rgb(0_0_0/0.5)] md:row-span-2 md:rounded-xl md:shadow-[0_24px_60px_rgb(0_0_0/0.5)]" />
          <div className="flex min-w-0 flex-col gap-1.5 pb-1 md:gap-5 md:pt-7 md:pb-0">
            <EsqueletoEncabezado />
          </div>
          <div className="col-span-2 flex min-w-0 flex-col gap-8 md:col-span-1 md:col-start-2 md:gap-6">
            <EsqueletoAcciones />
            <EsqueletoDetalle />
          </div>
        </div>
      </div>
    </main>
  );
}
