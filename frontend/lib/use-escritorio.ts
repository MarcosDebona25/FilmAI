import { useSyncExternalStore } from "react";

// El mismo corte que `md:` de Tailwind: donde la barra gana su fondo y los
// diálogos (`DialogShell`) pasan de hoja inferior a tarjeta centrada.
const ESCRITORIO = "(width >= 48rem)";

function suscribir(avisar: () => void) {
  // `?.`: en los tests (jsdom) `matchMedia` puede no existir.
  const consulta = window.matchMedia?.(ESCRITORIO);
  consulta?.addEventListener?.("change", avisar);
  return () => consulta?.removeEventListener?.("change", avisar);
}

const leer = () => window.matchMedia?.(ESCRITORIO).matches ?? false;
// En el servidor no hay pantalla: se asume celular, igual que el CSS sin `md:`.
const leerEnServidor = () => false;

/**
 * Si la pantalla es de escritorio, y se actualiza si cambia el ancho.
 *
 * `useSyncExternalStore` es el hook de React para leer un valor que vive fuera
 * de React (acá, el ancho de la ventana): un componente que se monta ya en el
 * navegador recibe el valor real desde el primer render, sin pasar por `false`.
 */
export function useEscritorio() {
  return useSyncExternalStore(suscribir, leer, leerEnServidor);
}
