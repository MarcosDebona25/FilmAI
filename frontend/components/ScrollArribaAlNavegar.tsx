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
 *
 * Cómo distingue los casos: guarda la última ruta que vio y la ruta a la que
 * llevó el último atrás o adelante. Compara rutas en vez de prender banderas,
 * porque una bandera puede quedar prendida (un atrás que no cambia la ruta) o
 * apagarse antes de tiempo (en desarrollo React corre cada efecto dos veces).
 */
export function ScrollArribaAlNavegar() {
  const pathname = usePathname();
  // `useRef` guarda un valor entre renders sin volver a renderizar: es como un
  // campo privado de la clase en Java. Los dos de acá se leen en el efecto.
  // La ruta del último render: `null` hasta el primero.
  const rutaAnterior = useRef<string | null>(null);
  // La ruta a la que llevó el último atrás o adelante.
  const rutaDeAtras = useRef<string | null>(null);

  useEffect(() => {
    // El navegador ya cambió la URL cuando avisa con `popstate`, antes de que
    // Next actualice `pathname`: se anota adónde fue.
    const anotar = () => {
      rutaDeAtras.current = window.location.pathname;
    };
    window.addEventListener("popstate", anotar);
    return () => window.removeEventListener("popstate", anotar);
  }, []);

  useEffect(() => {
    const anterior = rutaAnterior.current;
    rutaAnterior.current = pathname;
    // Al entrar, al recargar y en el segundo montaje de desarrollo: la ruta no
    // cambió respecto de la última vista.
    if (anterior === null || anterior === pathname) return;
    if (rutaDeAtras.current === pathname) {
      rutaDeAtras.current = null;
      return;
    }
    if (window.location.hash) return;
    // `instant`: sin animación, como una página que se abre arriba.
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname]);

  return null;
}
