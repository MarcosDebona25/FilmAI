"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

/** La URL sin el ancla: identifica la página en el mapa de scrolls. */
function claveActual() {
  return window.location.pathname + window.location.search;
}

/**
 * Al ir a otra página, la deja arriba de todo.
 *
 * Next ya lo intenta, pero con una regla que la navbar fija de escritorio
 * rompe: si el comienzo de la página nueva sigue a la vista, no mueve nada
 * (`layout-router.js`, `topOfElementInViewport`). Con la barra fija ocupando
 * los primeros 84 px, bajar menos que eso y tocar un enlace dejaba el
 * principio de la página nueva tapado por la barra.
 *
 * No hace nada en dos casos:
 * - al entrar o recargar: el navegador restaura el scroll;
 * - con un ancla (`/settings#t-idioma`): el navegador salta a la sección.
 *
 * Con atrás o adelante (`popstate`) devuelve el scroll que había en esa página.
 * El navegador solo no alcanza: restaura apenas cambia la URL, cuando todavía
 * se ve la página de la que se sale, y si esa es más corta el scroll queda
 * recortado a su alto (bajar 900 px en /terms, ir a /search y volver dejaba
 * ~530). Por eso se anota el último scroll de cada URL y se aplica cuando
 * vuelve la página anterior, reintentando hasta que tenga el alto necesario.
 *
 * Un cambio solo de búsqueda (`?q=`, los filtros de Buscar) no cambia
 * `pathname`, así que tampoco mueve la página.
 */
/** Lo que hace la persona para mover la página por su cuenta. */
const EVENTOS_DE_LA_PERSONA = ["wheel", "touchstart", "keydown", "mousedown"] as const;

/** Hasta cuántos cuadros (~1 s a 60 por segundo) se reintenta devolver el scroll. */
const CUADROS_MAXIMOS = 60;

/**
 * Lleva la página a `top` y reintenta en cada cuadro hasta llegar. `pathname`
 * cambia antes de que esté todo el contenido de la página anterior (Next lo
 * pinta en un render posterior), y mientras la página sea más corta el
 * navegador recorta el scroll. Si la persona mueve la página, deja de insistir.
 * Devuelve la función que corta los reintentos (la limpieza del efecto).
 */
function devolverScroll(top: number) {
  let cuadro = 0;
  let pedido = 0;
  const cortar = () => {
    cancelAnimationFrame(pedido);
    for (const evento of EVENTOS_DE_LA_PERSONA) window.removeEventListener(evento, cortar);
  };
  const intentar = () => {
    window.scrollTo({ top, left: 0, behavior: "instant" });
    cuadro += 1;
    if (Math.abs(window.scrollY - top) < 1 || cuadro >= CUADROS_MAXIMOS) cortar();
    else pedido = requestAnimationFrame(intentar);
  };
  for (const evento of EVENTOS_DE_LA_PERSONA)
    window.addEventListener(evento, cortar, { passive: true });
  intentar();
  return cortar;
}

export function ScrollArribaAlNavegar() {
  const pathname = usePathname();
  // `useRef` guarda un valor entre renders sin volver a renderizar: es como un
  // campo privado de la clase en Java. Los de acá se leen en los efectos.
  const primeraVez = useRef(true);
  // Con atrás o adelante: el scroll a devolver (0 si no se había anotado).
  const volverA = useRef<number | null>(null);
  // Último scroll de cada URL visitada, como un `Map<String, Integer>` de Java.
  const scrolls = useRef(new Map<string, number>());
  // La ruta que ya se procesó, para saber si un `popstate` cambia de página.
  const rutaVista = useRef(pathname);

  useEffect(() => {
    // Cada scroll se anota en la URL que está en la barra en ese momento.
    const anotarScroll = () => {
      scrolls.current.set(claveActual(), window.scrollY);
    };
    // `popstate` llega con la URL ya cambiada y antes de que Next cambie
    // `pathname`. Se lee el valor ahora, antes de que el scroll recortado del
    // navegador lo pise.
    // Si atrás solo cambia la búsqueda (`?q=`), `pathname` no cambia y no hay
    // nada que devolver: la página no se movió.
    const alVolver = () => {
      if (window.location.pathname === rutaVista.current) return;
      volverA.current = scrolls.current.get(claveActual()) ?? 0;
    };
    window.addEventListener("scroll", anotarScroll, { passive: true });
    window.addEventListener("popstate", alVolver);
    return () => {
      window.removeEventListener("scroll", anotarScroll);
      window.removeEventListener("popstate", alVolver);
    };
  }, []);

  useEffect(() => {
    rutaVista.current = pathname;
    if (primeraVez.current) {
      primeraVez.current = false;
      return;
    }
    if (volverA.current !== null) {
      const top = volverA.current;
      volverA.current = null;
      return devolverScroll(top);
    }
    if (window.location.hash) return;
    // `instant`: sin animación, como una página que se abre arriba.
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname]);

  return null;
}
