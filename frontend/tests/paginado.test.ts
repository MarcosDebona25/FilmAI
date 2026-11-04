import { describe, expect, it } from "vitest";

import { desplazamientoDePagina, gapDeColumnas } from "@/lib/paginado";

describe("desplazamientoDePagina", () => {
  it("avanza el ancho visible más un gap: la tarjeta cols + 1 queda primera", () => {
    // 6 tarjetas de 180 px con 5 gaps de 20 px: 1180 visibles. Una página son
    // 6 · (180 + 20) = 1200 px.
    const tarjeta = 180;
    const gap = 20;
    const cols = 6;
    const visible = cols * tarjeta + (cols - 1) * gap;
    expect(desplazamientoDePagina(visible, gap)).toBe(cols * (tarjeta + gap));
  });

  it("con anchos fraccionarios no redondea (el snap corrige el último píxel)", () => {
    expect(desplazamientoDePagina(1353.6, 22.5)).toBeCloseTo(1376.1);
  });

  it("sin gap válido avanza solo el ancho visible", () => {
    expect(desplazamientoDePagina(800, Number.NaN)).toBe(800);
  });
});

describe("gapDeColumnas", () => {
  it("lee el column-gap calculado en px", () => {
    const ul = document.createElement("ul");
    ul.style.columnGap = "20px";
    document.body.append(ul);
    expect(gapDeColumnas(ul)).toBe(20);
    ul.remove();
  });

  it("con `normal` (sin gap) devuelve 0", () => {
    const ul = document.createElement("ul");
    document.body.append(ul);
    expect(gapDeColumnas(ul)).toBe(0);
    ul.remove();
  });
});
