/**
 * Grilla de «Lists» y su esqueleto. Viven acá y no en `SortableListsGrid`
 * porque importar algo de ese módulo traería dnd-kit al primer JS de la página.
 */
export const CLASE_GRILLA_LISTAS =
  "grid grid-cols-1 gap-4 md:grid-cols-[repeat(auto-fill,minmax(min(380px,100%),1fr))] md:gap-5";

export function ListsGridSkeleton({ etiqueta }: { etiqueta?: string }) {
  return (
    <ul role="status" aria-label={etiqueta} className={CLASE_GRILLA_LISTAS}>
      {[0, 1, 2].map((indice) => (
        <li key={indice} className="h-[188px] rounded-2xl bg-raised md:h-[236px]" />
      ))}
    </ul>
  );
}
