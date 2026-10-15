"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";

/** Antes de esto no se muestra: una navegación rápida no tiene por qué parpadear. */
const DEMORA_MS = 120;
/** Si la página nunca llega (error de red), la barra no queda colgada. */
const TOPE_MS = 15_000;

type Estado = "quieta" | "cargando" | "terminando";

/**
 * Barra fina dorada arriba de todo mientras se navega (16/10/2026). El App
 * Router no avisa cuándo empieza una navegación, así que se detecta el clic en
 * un enlace interno y se da por terminada cuando cambian la ruta o la query.
 *
 * Escucha en `window`, en la fase de burbuja: si `NavigationGuard` frena el
 * clic (cambios sin guardar), corta la propagación y la barra no arranca.
 */
export function NavigationProgress() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [estado, setEstado] = useState<Estado>("quieta");
  const demora = useRef<number | undefined>(undefined);
  const tope = useRef<number | undefined>(undefined);

  function terminar() {
    window.clearTimeout(demora.current);
    window.clearTimeout(tope.current);
    setEstado((actual) => (actual === "cargando" ? "terminando" : "quieta"));
  }

  useEffect(() => {
    function alHacerClic(evento: MouseEvent) {
      if (
        evento.button !== 0 ||
        evento.metaKey ||
        evento.ctrlKey ||
        evento.shiftKey ||
        evento.altKey
      )
        return;
      const enlace = (evento.target as Element | null)?.closest<HTMLAnchorElement>("a[href]");
      if (!enlace || enlace.download || (enlace.target && enlace.target !== "_self")) return;
      const destino = new URL(enlace.href);
      const actual = window.location;
      // Otro sitio, la misma página o solo un ancla (#…): no hay navegación que esperar.
      if (
        destino.origin !== actual.origin ||
        (destino.pathname === actual.pathname && destino.search === actual.search)
      )
        return;
      window.clearTimeout(demora.current);
      window.clearTimeout(tope.current);
      demora.current = window.setTimeout(() => setEstado("cargando"), DEMORA_MS);
      tope.current = window.setTimeout(terminar, TOPE_MS);
    }
    window.addEventListener("click", alHacerClic);
    return () => window.removeEventListener("click", alHacerClic);
  }, []);

  // Llegó la página nueva.
  useEffect(terminar, [pathname, searchParams]);

  // Después de completarse, la barra se desvanece y vuelve a cero.
  useEffect(() => {
    if (estado !== "terminando") return;
    const fin = window.setTimeout(() => setEstado("quieta"), 400);
    return () => window.clearTimeout(fin);
  }, [estado]);

  useEffect(
    () => () => {
      window.clearTimeout(demora.current);
      window.clearTimeout(tope.current);
    },
    []
  );

  return (
    <div
      aria-hidden="true"
      data-estado={estado}
      className="pointer-events-none fixed inset-x-0 top-0 z-[100] h-[3px]"
    >
      <div
        className="h-full bg-primary shadow-[0_0_8px_var(--primary)] motion-reduce:transition-none"
        style={{
          width: estado === "quieta" ? "0%" : estado === "cargando" ? "85%" : "100%",
          opacity: estado === "terminando" ? 0 : 1,
          // Avanza rápido al principio y se frena cerca del final (nunca llega
          // sola al 100 %); al terminar completa y se desvanece.
          transition:
            estado === "cargando"
              ? "width 8s cubic-bezier(0.1, 0.7, 0.3, 1)"
              : estado === "terminando"
                ? "width 150ms ease-out, opacity 250ms ease 150ms"
                : "none",
        }}
      />
    </div>
  );
}
