import { describe, expect, it } from "vitest";

import { destinoSeguro } from "@/lib/safe-next";

const POR_DEFECTO = "/home";

describe("destinoSeguro (parámetro next del login)", () => {
  it("conserva una ruta propia con query y hash", () => {
    expect(destinoSeguro("/peliculas/1?x=1#y", POR_DEFECTO)).toBe("/peliculas/1?x=1#y");
    expect(destinoSeguro("/profile", POR_DEFECTO)).toBe("/profile");
  });

  it.each([
    ["protocolo relativo", "//evil.example"],
    ["barra invertida", "/\\evil.example"],
    ["tres barras", "///evil.example"],
    ["tabulación entre barras", "/\t/evil.example"],
    ["salto de línea entre barras", "/\n/evil.example"],
    ["barra invertida con tabulación", "/\t\\evil.example"],
    ["esquema completo", "https://evil.example"],
    ["esquema sin barras", "javascript:alert(1)"],
    ["sin barra inicial", "evil.example"],
    ["subida de directorio hacia //", "/..//evil.example"],
    ["subida con barra invertida", "/.\\/..//evil.example"],
  ])("rechaza %s", (_nombre, next) => {
    expect(destinoSeguro(next, POR_DEFECTO)).toBe(POR_DEFECTO);
  });

  it("usa la ruta por defecto sin next", () => {
    expect(destinoSeguro(null, POR_DEFECTO)).toBe(POR_DEFECTO);
    expect(destinoSeguro("", POR_DEFECTO)).toBe(POR_DEFECTO);
    expect(destinoSeguro(undefined, POR_DEFECTO)).toBe(POR_DEFECTO);
  });

  it("nunca devuelve algo que el navegador resuelva fuera del origen", () => {
    const hostiles = ["//a.b", "/\\a.b", "/\t/a.b", "/..//a.b", "/%2F/a.b", "/\\\\a.b"];
    for (const next of hostiles) {
      const destino = destinoSeguro(next, POR_DEFECTO);
      expect(new URL(destino, "https://filmai.invalid").origin).toBe("https://filmai.invalid");
      expect(destino.startsWith("//")).toBe(false);
    }
  });
});
