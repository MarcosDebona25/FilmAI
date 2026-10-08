import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { Linter, type Rule } from "eslint";
import { describe, expect, it } from "vitest";
import { legacyFiles, rules } from "../scripts/i18n/rules.mjs";
import runtimeEnums from "@/i18n/enums.json";
import enums from "../../contracts/enums.json";

function lint(code: string, rule: keyof typeof rules) {
  return new Linter().verify(code, [
    {
      languageOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        parserOptions: { ecmaFeatures: { jsx: true } },
      },
      plugins: { i18n: { rules: rules as unknown as Record<string, Rule.RuleModule> } },
      rules: { [`i18n/${rule}`]: "error" },
    },
  ]);
}
describe("puertas contra degradaciones de idioma", () => {
  it("rechaza texto JSX, atributos y toasts, pero admite claves y marca", () => {
    expect(lint("<p>Texto nuevo</p>", "no-visible-literals")).toHaveLength(1);
    expect(lint('<input placeholder="Texto nuevo" />', "no-visible-literals")).toHaveLength(1);
    expect(lint('toast.error("Error nuevo")', "no-visible-literals")).toHaveLength(1);
    expect(lint('<p>{"New text"}</p>', "no-visible-literals")).toHaveLength(1);
    expect(lint('<input aria-label={"New text"} />', "no-visible-literals")).toHaveLength(1);
    expect(lint('<p>{condition ? "New text" : t("key")}</p>', "no-visible-literals")).toHaveLength(
      1
    );
    expect(lint('<p>{t("key")}</p>', "no-visible-literals")).toHaveLength(0);
    expect(lint("<p>FilmAI</p>", "no-visible-literals")).toHaveLength(0);
  });
  it("prohíbe debug y formatos fuera del módulo autorizado", () => {
    expect(lint("error.debug", "no-debug")).toHaveLength(1);
    expect(lint('error["debug"]', "no-debug")).toHaveLength(1);
    expect(lint("const {debug} = error", "no-debug")).toHaveLength(1);
    expect(lint('new Intl.DateTimeFormat("es-AR")', "centralized-formats")).toHaveLength(1);
    expect(lint("value.toLocaleString()", "centralized-formats")).toHaveLength(1);
    expect(lint('value["toLocaleString"]()', "centralized-formats")).toHaveLength(1);
  });
  it("la lista de excepciones tiene techo y todos los archivos existen", () => {
    expect(legacyFiles.length).toBeLessThanOrEqual(13);
    expect(new Set(legacyFiles).size).toBe(legacyFiles.length);
    for (const path of legacyFiles) expect(existsSync(path), path).toBe(true);
  });
  it("catálogos y enumeraciones se reproducen desde los CSV y contratos aprobados", () => {
    expect(runtimeEnums).toEqual(enums);
    expect(() => execFileSync("python3", ["scripts/i18n/generate.py", "--check"])).not.toThrow();
    expect(() => execFileSync("node", ["scripts/i18n/check.mjs"])).not.toThrow();
  });
});
