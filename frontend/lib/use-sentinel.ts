import { useEffect, useRef, type RefObject } from "react";

/** Distancia al final de la lista a la que se pide la página siguiente. */
export const ANTICIPO = "600px";

/**
 * Avisa cuando un nodo centinela (el final de una lista) se acerca a la
 * pantalla, con un anticipo de `margen` para pedir la página antes de llegar.
 *
 * - `activo`: sin él no se observa nada (no hay más páginas, o ya se está pidiendo una).
 * - `alVer`: se llama con la versión más reciente, así que puede leer el
 *   estado de ese render sin que haya que recrear el observador.
 * - `reiniciar`: al cambiar, el observador se recrea. `IntersectionObserver`
 *   avisa una vez al empezar a observar: si tras cargar una página el
 *   centinela sigue a la vista, recrearlo pide la siguiente.
 */
export function useSentinel(
  nodo: RefObject<Element | null>,
  {
    activo,
    alVer,
    margen = ANTICIPO,
    reiniciar,
  }: { activo: boolean; alVer: () => void; margen?: string; reiniciar?: string | number }
) {
  const ultimo = useRef(alVer);
  useEffect(() => {
    ultimo.current = alVer;
  });

  useEffect(() => {
    const elemento = nodo.current;
    if (!activo || !elemento || typeof IntersectionObserver === "undefined") return;
    const observador = new IntersectionObserver(
      (entradas) => {
        if (entradas.some((entrada) => entrada.isIntersecting)) ultimo.current();
      },
      { rootMargin: margen }
    );
    observador.observe(elemento);
    return () => observador.disconnect();
  }, [nodo, activo, margen, reiniciar]);
}
