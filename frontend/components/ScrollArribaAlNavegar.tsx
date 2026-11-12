"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

/**
 * Al ir a otra página, la deja arriba de todo.
 *
 * Next ya lo intenta, pero con una regla que la navbar fija de escritorio
 * rompe: si el comienzo de la página nueva sigue a la vista, no mueve nada
 * (`layout-router.js`, `topOfElementInViewport`). Con la barra fija ocupando
 * los primeros 84 px, bajar menos que eso y tocar un enlace dejaba el
 * principio de la página nueva tapado por la barra.
 *
 * No hace nada en tres casos:
 * - al entrar o recargar: el navegador restaura el scroll;
 * - con atrás o adelante (`popstate`): Next y el navegador devuelven el scroll
 *   que había;
 * - con un ancla (`/settings#t-idioma`): el navegador salta a la sección.
 *
 * Un cambio solo de búsqueda (`?q=`, los filtros de Buscar) no cambia
 * `pathname`, así que tampoco mueve la página.
 */
export function ScrollArribaAlNavegar() {
  const pathname = usePathname();
  // `useRef` guarda un valor entre renders sin volver a renderizar: es como un
  // campo privado de la clase en Java. Los dos de acá se leen en el efecto.
  const primeraVez = useRef(true);
  const vieneDeAtras = useRef(false);

  useEffect(() => {
    // `popstate` llega antes de que Next cambie `pathname`: alcanza con anotarlo.
    const anotar = () => {
      vieneDeAtras.current = true;
    };
    window.addEventListener("popstate", anotar);
    return () => window.removeEventListener("popstate", anotar);
  }, []);

  useEffect(() => {
    if (primeraVez.current) {
      primeraVez.current = false;
      return;
    }
    if (vieneDeAtras.current) {
      vieneDeAtras.current = false;
      return;
    }
    if (window.location.hash) return;
    // `instant`: sin animación, como una página que se abre arriba.
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname]);

  return null;
}
