import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync("app/globals.css", "utf8");
const token = (nombre: string) => new RegExp(`--${nombre}:\\s*(#[0-9a-fA-F]{6})`).exec(css)![1];

function luminancia(hex: string) {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const contraste = (a: string, b: string) => {
  const [claro, oscuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro + 0.05) / (oscuro + 0.05);
};

describe("borde de los campos (WCAG 1.4.11)", () => {
  // Fondos reales sobre los que se apoya un campo: página, tarjeta y fila elevada.
  for (const fondo of ["background", "card", "raised-2"]) {
    it(`--field-border tiene al menos 3:1 sobre --${fondo}`, () => {
      expect(contraste(token("field-border"), token(fondo))).toBeGreaterThanOrEqual(3);
    });
  }
  it("los bordes de tarjetas siguen con --line", () => {
    expect(token("line")).toBe("#262636");
  });
});
