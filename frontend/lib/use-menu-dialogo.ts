import { useEffect, type RefObject } from "react";

import { posicionarMenu } from "@/lib/posicion-menu";

/**
 * Pone un `<dialog>` pegado al botón que lo abrió (su contenedor, el padre del
 * diálogo). El diálogo modal vive en la capa superior, fuera del flujo: su
 * posición se calcula a mano. `scrollHeight` da el alto completo del contenido
 * aunque hoy esté recortado por el alto máximo.
 */
export function ubicarMenu(dialogo: HTMLDialogElement) {
  const ancla = dialogo.parentElement?.getBoundingClientRect();
  if (!ancla) return;
  const { x, y, altoMaximo } = posicionarMenu({
    ancla,
    ancho: dialogo.offsetWidth,
    alto: dialogo.scrollHeight,
    ventana: { ancho: window.innerWidth, alto: window.innerHeight },
  });
  dialogo.style.setProperty("--menu-x", `${x}px`);
  dialogo.style.setProperty("--menu-y", `${y}px`);
  dialogo.style.setProperty("--menu-max", `${altoMaximo}px`);
}

/**
 * Abre el `<dialog>` como modal al montarse y lo cierra al desmontarse. En
 * escritorio es un panel que sigue al botón si la página se desplaza o cambia el
 * tamaño; en celular es una hoja y la página queda quieta. Al cerrarse, el foco
 * vuelve al botón que lo abrió. `enfocar` elige qué
 * recibe el foco al abrir.
 */
export function useMenuDialogo(
  ref: RefObject<HTMLDialogElement | null>,
  enfocar: (dialogo: HTMLDialogElement) => HTMLElement | null
) {
  useEffect(() => {
    const dialogo = ref.current;
    if (!dialogo) return;
    // El botón que lo abrió va justo antes del diálogo. Se lee acá y no de
    // `document.activeElement`: Safari no enfoca un botón al hacer clic.
    const disparador = dialogo.previousElementSibling as HTMLElement | null;
    dialogo.showModal();
    ubicarMenu(dialogo);
    enfocar(dialogo)?.focus({ preventScroll: true });

    const desborde = document.body.style.overflow;
    // Girar el celular o angostar la ventana puede cambiar de panel a hoja con
    // el menú abierto: la página solo queda quieta mientras se ve la hoja.
    const ajustarBloqueo = () => {
      const esPanel = window.matchMedia?.("(min-width: 48rem)").matches;
      document.body.style.overflow = esPanel ? desborde : "hidden";
    };
    const seguirAlBoton = () => ubicarMenu(dialogo);
    const alRedimensionar = () => {
      ubicarMenu(dialogo);
      ajustarBloqueo();
    };
    ajustarBloqueo();
    window.addEventListener("scroll", seguirAlBoton, { passive: true });
    window.addEventListener("resize", alRedimensionar);
    return () => {
      dialogo.close();
      // Con el diálogo modal abierto el botón está inerte: el foco solo puede
      // volver una vez que se cerró.
      if (disparador?.isConnected) disparador.focus({ preventScroll: true });
      window.removeEventListener("scroll", seguirAlBoton);
      window.removeEventListener("resize", alRedimensionar);
      document.body.style.overflow = desborde;
    };
    // Corre una vez al abrir: `enfocar` solo se usa en ese momento.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
