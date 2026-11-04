import { describe, expect, it } from "vitest";

import { posicionarMenu } from "@/lib/posicion-menu";

const ventana = { ancho: 1280, alto: 800 };

describe("posicionarMenu", () => {
  it("se abre hacia abajo si el panel entra", () => {
    const ancla = { left: 100, top: 200, bottom: 250 };

    const { y } = posicionarMenu({ ancla, ancho: 340, alto: 320, ventana });

    expect(y).toBe(258);
  });

  it("se abre hacia arriba si abajo no entra y arriba hay más lugar", () => {
    const ancla = { left: 100, top: 640, bottom: 690 };

    const { y, altoMaximo } = posicionarMenu({ ancla, ancho: 340, alto: 320, ventana });

    expect(y).toBe(312);
    expect(altoMaximo).toBe(616);
  });

  it("sigue abajo si no entra en ningún lado pero abajo hay más lugar", () => {
    const ancla = { left: 100, top: 300, bottom: 350 };

    const { y, altoMaximo } = posicionarMenu({ ancla, ancho: 340, alto: 900, ventana });

    expect(y).toBe(358);
    expect(altoMaximo).toBe(426);
  });

  it("hacia arriba, un panel más alto que el lugar queda pegado al margen", () => {
    const ancla = { left: 100, top: 500, bottom: 550 };

    const { y } = posicionarMenu({ ancla, ancho: 340, alto: 900, ventana });

    expect(y).toBe(16);
  });

  it("no deja que el panel se salga por la derecha", () => {
    const ancla = { left: 1100, top: 200, bottom: 250 };

    const { x } = posicionarMenu({ ancla, ancho: 340, alto: 320, ventana });

    expect(x).toBe(924);
  });
});
