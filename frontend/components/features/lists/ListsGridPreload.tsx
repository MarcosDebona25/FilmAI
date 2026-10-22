"use client";

import { useEffect } from "react";

import { useAccount } from "@/components/AccountProvider";

type Grilla = typeof import("@/components/features/lists/SortableListsGrid").SortableListsGrid;

let grilla: Grilla | null = null;

/** Baja (una sola vez) el chunk de la grilla con arrastre (dnd-kit) que usa `ListsView`. */
export const cargarGrilla = () =>
  import("@/components/features/lists/SortableListsGrid").then(
    (modulo) => (grilla = modulo.SortableListsGrid)
  );

/**
 * La grilla, si ya llegó. `ListsView` la dibuja directo en vez de usar
 * `next/dynamic`: ese suspende aunque el chunk ya esté, y React 19 retiene
 * hasta ~300 ms el reemplazo del esqueleto (22/10/2026).
 */
export const grillaCargada = () => grilla;

/**
 * Baja ese chunk cuando el navegador queda libre, con la sesión ya iniciada:
 * así la primera entrada a «Lists» no lo espera después del JS de la ruta.
 */
export function ListsGridPreload() {
  const { perfil } = useAccount();
  const conSesion = Boolean(perfil);

  useEffect(() => {
    if (!conSesion) return;
    if (typeof window.requestIdleCallback === "function") {
      const id = window.requestIdleCallback(() => void cargarGrilla(), { timeout: 5000 });
      return () => window.cancelIdleCallback(id);
    }
    const id = window.setTimeout(() => void cargarGrilla(), 2000);
    return () => window.clearTimeout(id);
  }, [conSesion]);

  return null;
}
