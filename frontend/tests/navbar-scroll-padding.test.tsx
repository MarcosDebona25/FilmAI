import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * El espacio que se reserva arriba para que un control enfocado no quede bajo
 * la navbar solo tiene sentido donde hay navbar: no en login ni registro.
 */
describe("scroll-padding-top de la navbar", () => {
  const css = readFileSync("app/globals.css", "utf8");

  it("solo se aplica cuando la página tiene la navbar", () => {
    expect(css).toMatch(/html:has\(header\[data-navbar\]\)\s*\{\s*scroll-padding-top:\s*5rem;/);
  });

  it("no queda un scroll-padding-top para todas las páginas", () => {
    expect(css).not.toMatch(/html\s*\{\s*scroll-padding-top/);
  });

  it("la navbar lleva la marca que usa ese selector", () => {
    const navbar = readFileSync("components/Navbar.tsx", "utf8");
    expect(navbar).toMatch(/<header[^>]*\bdata-navbar\b/);
  });
});
