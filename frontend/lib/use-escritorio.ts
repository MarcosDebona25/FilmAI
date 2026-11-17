import { useEffect, useState } from "react";

/** El corte de escritorio de Tailwind (`md`). */
export const ESCRITORIO = "(width >= 48rem)";

/** Si la pantalla es de escritorio, y se actualiza si cambia el ancho. */
export function useEscritorio() {
  const [escritorio, setEscritorio] = useState(false);
  useEffect(() => {
    // `?.`: en los tests (jsdom) `matchMedia` puede no existir.
    const consulta = window.matchMedia?.(ESCRITORIO);
    if (!consulta) return;
    const leer = () => setEscritorio(consulta.matches);
    leer();
    consulta.addEventListener?.("change", leer);
    return () => consulta.removeEventListener?.("change", leer);
  }, []);
  return escritorio;
}
