import { describe, expect, it } from "vitest";

import { parseLegalMarkdown, loadTerms } from "@/lib/legal";
import { passwordRules } from "@/lib/password-rules";
import { formatCountdown } from "@/lib/pending-email";
import { isAccessPath, routes } from "@/lib/routes";

describe("reglas de contraseña del registro", () => {
  it("evalúa cada regla por separado", () => {
    expect(passwordRules("")).toEqual({ length: false, case: false, number: false, symbol: false });
    expect(passwordRules("Popcorn24")).toEqual({
      length: true,
      case: true,
      number: true,
      symbol: false,
    });
    expect(passwordRules("popcorn24!")).toMatchObject({ case: false, symbol: true });
  });
  it("limita la longitud entre 8 y 20 caracteres", () => {
    expect(passwordRules("Aa1!aaa").length).toBe(false);
    expect(passwordRules("Aa1!aaaa").length).toBe(true);
    expect(passwordRules("Aa1!" + "a".repeat(16)).length).toBe(true);
    expect(passwordRules("Aa1!" + "a".repeat(17)).length).toBe(false);
  });
  it("solo acepta como símbolo los permitidos", () => {
    expect(passwordRules("Aaaaaaa1-").symbol).toBe(false);
    expect(passwordRules("Aaaaaaa1*").symbol).toBe(true);
  });
});

describe("cuenta regresiva de reenvío", () => {
  it("formatea m:ss", () => {
    expect(formatCountdown(60)).toBe("1:00");
    expect(formatCountdown(42)).toBe("0:42");
    expect(formatCountdown(5)).toBe("0:05");
  });
});

describe("rutas de acceso", () => {
  it("reconoce las pantallas sin barra ni pie", () => {
    for (const path of [routes.home, routes.login, routes.register, "/confirm-email/abc"])
      expect(isAccessPath(path)).toBe(true);
    for (const path of [routes.terms, routes.profile, "/settings"])
      expect(isAccessPath(path)).toBe(false);
  });
});

describe("términos y condiciones en Markdown", () => {
  it("interpreta cabecera, secciones, párrafos y listas", () => {
    const doc = parseLegalMarkdown(
      "---\nupdated: 2026-10-07\n---\n# Título\n\nIntro.\n\n## 1. Uno\n\nTexto uno.\n\n- a\n- b\n\n## 2. Dos\n\nTexto dos.\n"
    );
    expect(doc.title).toBe("Título");
    expect(doc.updated).toBe("2026-10-07");
    expect(doc.intro).toEqual([{ type: "p", text: "Intro." }]);
    expect(doc.sections.map((s) => s.heading)).toEqual(["1. Uno", "2. Dos"]);
    expect(doc.sections[0].blocks).toEqual([
      { type: "p", text: "Texto uno." },
      { type: "ul", items: ["a", "b"] },
    ]);
  });
  it.each(["en", "es"] as const)(
    "los archivos versionados en %s tienen 12 secciones",
    async (locale) => {
      const doc = await loadTerms(locale);
      expect(doc.title).not.toBe("");
      expect(doc.updated).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(doc.sections).toHaveLength(12);
      expect(doc.sections.every((s) => s.blocks.length > 0)).toBe(true);
    }
  );
});
