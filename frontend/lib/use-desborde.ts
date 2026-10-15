"use client";

import { useEffect, useRef, useState } from "react";

/**
 * ¿El texto recortado con `line-clamp` se corta de verdad? Mide el elemento
 * (alto del contenido contra alto visible) y vuelve a medir si cambia de
 * tamaño. Así «Read more» aparece solo cuando hace falta, y no por una cuenta
 * de caracteres que no sabe del ancho de la pantalla. Mientras el texto está
 * desplegado no se mide: ahí nunca desborda y el botón tiene que seguir.
 */
export function useDesborde<T extends HTMLElement>(desplegado: boolean, contenido: string) {
  const ref = useRef<T>(null);
  const [desborda, setDesborda] = useState(false);

  useEffect(() => {
    const elemento = ref.current;
    if (!elemento || desplegado) return;
    const medir = () => setDesborda(elemento.scrollHeight > elemento.clientHeight + 1);
    const observador = new ResizeObserver(medir);
    observador.observe(elemento);
    medir();
    return () => observador.disconnect();
  }, [desplegado, contenido]);

  return [ref, desborda] as const;
}
