import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createTranslator } from "next-intl";
import { describe, expect, it } from "vitest";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import { ADVERTENCIA_BAJA } from "@/lib/profile-draft";

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

describe("catálogo transitorio de OT-70", () => {
  it("mantiene las mismas 77 claves transitorias y la marca en ambos idiomas", () => {
    expect(Object.keys(flatten(es)).sort()).toEqual(Object.keys(flatten(en)).sort());
    expect(Object.keys(flatten(es))).toHaveLength(78);
    const rows = readFileSync(
      resolve(process.cwd(), "../docs/i18n/ot70-catalogo-transitorio.csv"),
      "utf8"
    )
      .trim()
      .split("\n")
      .slice(1);
    expect(rows).toHaveLength(77);
    expect(rows.map((row) => row.split(",")[0]).sort()).toEqual(
      Object.keys(flatten(es))
        .filter((key) => key.startsWith("legacy."))
        .sort()
    );
    expect(rows.every((row) => row.endsWith(",aprobado"))).toBe(true);
  });

  it("conserva el español actual de confirmación, preferencias y baja", () => {
    expect(es.legacy.confirmation.loading).toBe("Confirmando su cuenta…");
    expect(es.legacy.settings.deactivateConfirm).toBe(ADVERTENCIA_BAJA);
    expect(es.legacy.settings.futureFeatures).toBe(
      "Estas preferencias se guardan, pero todavía no cambian la visibilidad de reseñas o listas ni activan correos."
    );
    expect(es.legacy.validation.required).toBe("Campo obligatorio.");
  });

  it.each(["en", "es"] as const)(
    "todos los mensajes %s se renderizan sin errores ICU",
    (locale) => {
      const messages = locale === "en" ? en : es;
      const translate = createTranslator({
        locale,
        messages,
        onError: (error) => {
          throw error;
        },
      });
      for (const key of Object.keys(flatten(messages))) {
        expect(translate(key as Parameters<typeof translate>[0])).toBe(flatten(messages)[key]);
      }
    }
  );
});
