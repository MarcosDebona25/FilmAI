/**
 * Grilla de «Lists» y su esqueleto. Viven acá y no en `SortableListsGrid`
 * porque importar algo de ese módulo traería dnd-kit al primer JS de la página.
 * Canvas «Watching · Lists»: 4 columnas desde 73,75 rem (1180 px), 2 desde 40 rem
 * y 1 debajo, así las 4 predeterminadas llenan solas la primera fila.
 */
export const CLASE_GRILLA_LISTAS =
  "grid grid-cols-1 gap-4 min-[40rem]:grid-cols-2 min-[40rem]:gap-5 min-[73.75rem]:grid-cols-4";

export function ListsGridSkeleton({ etiqueta }: { etiqueta?: string }) {
  return (
    <ul role="status" aria-label={etiqueta} className={CLASE_GRILLA_LISTAS}>
      {[0, 1, 2].map((indice) => (
        <li key={indice} className="h-[11.75rem] rounded-2xl bg-raised md:h-[14.75rem]" />
      ))}
    </ul>
  );
}
