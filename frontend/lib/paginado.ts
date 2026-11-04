/**
 * Cuánto desplazar una fila de tarjetas para avanzar exactamente una página.
 *
 * Desde `md` la fila muestra `--cols` tarjetas enteras: el ancho visible es
 * `cols · tarjeta + (cols − 1) · gap`. Sumando un `gap` más queda `cols · (tarjeta
 * + gap)`, es decir, la distancia justa para que la tarjeta `cols + 1` quede
 * primera. Con `× 0.9` (lo de antes) la fila terminaba con una tarjeta cortada.
 */
export function desplazamientoDePagina(anchoVisible: number, gap: number) {
  return anchoVisible + (Number.isFinite(gap) ? gap : 0);
}

/** El `column-gap` calculado de un elemento, en px (0 si es `normal`). */
export function gapDeColumnas(elemento: Element) {
  return Number.parseFloat(getComputedStyle(elemento).columnGap) || 0;
}
