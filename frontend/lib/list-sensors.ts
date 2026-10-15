import { PointerSensor, TouchSensor } from "@dnd-kit/core";

/** Espera de la pulsación larga que inicia el arrastre en celular. */
export const ESPERA_ARRASTRE_MS = 250;
/** Cuánto puede moverse el dedo durante la espera: más que eso es scroll. */
export const TOLERANCIA_ARRASTRE_PX = 8;
/** Distancia que debe recorrer el puntero desde la manija para empezar a arrastrar. */
export const DISTANCIA_MANIJA_PX = 4;

/**
 * Arrastre desde la manija (escritorio): solo arranca si el puntero se apoyó
 * en un elemento con `data-drag-handle`, así el resto de la tarjeta (enlace,
 * menú) conserva su comportamiento.
 */
export class ManijaSensor extends PointerSensor {
  static activators = [
    {
      eventName: "onPointerDown" as const,
      handler: ({ nativeEvent: event }: { nativeEvent: PointerEvent }) =>
        event.isPrimary &&
        event.button === 0 &&
        event.target instanceof Element &&
        event.target.closest("[data-drag-handle]") !== null,
    },
  ];
}

/**
 * Pulsación larga (celular): el arrastre empieza tras `ESPERA_ARRASTRE_MS`
 * quieto sobre la tarjeta. Si el dedo se mueve antes, `TouchSensor` cancela la
 * activación y el gesto queda como scroll.
 */
export class PulsacionLargaSensor extends TouchSensor {}
