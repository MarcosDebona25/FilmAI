import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("tokens de globals.css", () => {
  it("define --radius en :root (sin él los botones y campos quedan rectos)", () => {
    const css = readFileSync("app/globals.css", "utf8");
    const raiz = css.slice(css.indexOf(":root {"));
    expect(raiz.slice(0, raiz.indexOf("\n}"))).toMatch(/--radius:\s*[\d.]+rem/);
  });
});
