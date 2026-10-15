import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parse, TYPE, type MessageFormatElement } from "@formatjs/icu-messageformat-parser";
import { describe, expect, it } from "vitest";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import codes from "../../contracts/error-codes.json";
import enums from "../../contracts/enums.json";
import { translateError, type ErrorParams } from "@/lib/errors";

function flatten(messages: Record<string, unknown>, prefix = ""): Record<string, string> {
  return Object.fromEntries(
    Object.entries(messages).flatMap(([key, value]) => {
      const path = prefix ? `${prefix}.${key}` : key;
      return typeof value === "string"
        ? [[path, value]]
        : Object.entries(flatten(value as Record<string, unknown>, path));
    })
  );
}
function contract(elements: MessageFormatElement[]): string[] {
  return elements
    .flatMap((element) => {
      if (element.type === TYPE.literal) return [];
      if (element.type === TYPE.pound) return ["pound"];
      if (element.type === TYPE.tag) return [`tag:${element.value}`, ...contract(element.children)];
      if (element.type === TYPE.plural || element.type === TYPE.select)
        return [
          `${element.type}:${element.value}:${Object.keys(element.options).sort().join(",")}`,
          ...Object.values(element.options).flatMap((option) => contract(option.value)),
        ];
      return [`${element.type}:${element.value}`];
    })
    .sort();
}

describe("contrato bilingüe completo", () => {
  it.each([[en, es]])("compara claves, argumentos, tags y ramas ICU", (english, spanish) => {
    const a = flatten(english),
      b = flatten(spanish);
    expect(Object.keys(a).sort()).toEqual(Object.keys(b).sort());
    for (const key of Object.keys(a))
      expect(contract(parse(a[key])), key).toEqual(contract(parse(b[key])));
  });
  it("cubre todos los códigos y enumera nombres reservados en ambos idiomas", () => {
    for (const messages of [en, es]) {
      for (const code of Object.keys(codes.codes))
        expect(messages.errors.codes, code).toHaveProperty(code);
      for (const gender of enums.genderValues) expect(messages.enums.gender).toHaveProperty(gender);
      for (const key of enums.defaultListKeys)
        expect(messages.enums.defaultList).toHaveProperty(key);
    }
    expect(Object.values(en.enums.defaultList)).toEqual(enums.reservedListNames.en);
    expect(Object.values(es.enums.defaultList)).toEqual(enums.reservedListNames.es);
  });
  it("los parámetros públicos alcanzan para renderizar cada código en ambos idiomas", () => {
    for (const [code, definition] of Object.entries(codes.codes)) {
      const params: ErrorParams = Object.fromEntries(
        Object.entries(definition.params).map(([key, type]) => [
          key,
          type === "integer" || type === "number"
            ? 2
            : type === "integer[]"
              ? [1, 2]
              : type === "string[]"
                ? ["movie", "tv"]
                : "value",
        ])
      );
      expect(translateError({ code, params }, "en"), code).not.toBe(en.errors.codes.unknown);
      expect(translateError({ code, params }, "es"), code).not.toBe(es.errors.codes.unknown);
    }
  });

  it("conserva la copia transitoria aprobada y corrige voseo y ayuda de contraseña", () => {
    const rows = readFileSync(
      resolve(process.cwd(), "../docs/i18n/ot70-catalogo-transitorio.csv"),
      "utf8"
    )
      .trim()
      .split("\n")
      .slice(1);
    expect(rows).toHaveLength(77);
    for (const row of rows) expect(flatten(es)).toHaveProperty(row.split(",")[0]);
    // El texto de la baja aprobado (docs/decisiones.md); Settings lo usa tal cual.
    expect(es.legacy.settings.deactivateConfirm).toBe(
      "Esta acción es irreversible. Se cerrarán todas tus sesiones y no podrás volver a iniciar sesión ni reactivar tu cuenta. Asegurate de querer dar de baja la cuenta antes de continuar."
    );
    expect(es.legacy.confirmation.loading).toBe("Confirmando tu cuenta…");
    expect(es.legacy.reset.passwordHelp).toContain("@#$%&*!");
    expect(en).not.toHaveProperty("emails");
    expect(en).not.toHaveProperty("legal");
  });
});
