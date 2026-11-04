/** Distancia entre el botón y el panel. */
const SEPARACION = 8;
/** Distancia mínima entre el panel y el borde de la ventana. */
const MARGEN = 16;
/** Con menos lugar que esto el panel no se achica más: se deja cortar. */
const ALTO_MINIMO = 160;

/**
 * Dónde ubicar un panel flotante respecto de su botón. Se abre hacia abajo si
 * entra; si no, hacia el lado con más lugar. Cuando no entra en ninguno, el alto
 * máximo lo achica y el panel se desplaza por dentro.
 */
export function posicionarMenu({
  ancla,
  ancho,
  alto,
  ventana,
}: {
  ancla: { left: number; top: number; bottom: number };
  ancho: number;
  alto: number;
  ventana: { ancho: number; alto: number };
}) {
  const lugarAbajo = ventana.alto - ancla.bottom - SEPARACION - MARGEN;
  const lugarArriba = ancla.top - SEPARACION - MARGEN;
  const haciaArriba = alto > lugarAbajo && lugarArriba > lugarAbajo;

  const altoMaximo = Math.max(haciaArriba ? lugarArriba : lugarAbajo, ALTO_MINIMO);
  const y = haciaArriba
    ? ancla.top - SEPARACION - Math.min(alto, altoMaximo)
    : ancla.bottom + SEPARACION;
  const x = Math.max(MARGEN, Math.min(ancla.left, ventana.ancho - ancho - MARGEN));

  return { x, y, altoMaximo };
}
