import { describe, expect, it, vi } from "vitest";
import { localeCookie, resolveLocale } from "@/i18n/config";

const request = vi.hoisted(() => ({
  cookie: undefined as string | undefined,
  header: null as string | null,
}));
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => (name === "filmai_locale" ? { value: request.cookie } : undefined),
  }),
  headers: async () => ({ get: () => request.header }),
}));
vi.mock("next-intl/server", () => ({ getRequestConfig: (callback: unknown) => callback }));

describe("locale de render", () => {
  it.each([
    ["es", "en", "es"],
    ["en", "es", "en"],
    ["fr", "es-AR", "es"],
    ["ES", "en-US", "en"],
    [undefined, "es-MX;q=0.8,en-US;q=0.3", "es"],
    [undefined, "es;q=0.2,en;q=0.9", "en"],
    [undefined, "fr-FR,de;q=0.9,es;q=0.4", "es"],
    [undefined, "es;q=0,en;q=0.8", "en"],
    [undefined, "es;q=0", "en"],
    [undefined, "ES-ar", "es"],
    [undefined, "es,en", "es"],
    [undefined, "*", "en"],
    [undefined, "fr", "en"],
    [undefined, "", "en"],
    [undefined, null, "en"],
    [undefined, "es;q=2", "en"],
    [undefined, "es;q=NaN", "en"],
    [undefined, "en,es;bad=1", "en"],
    [undefined, "es,", "en"],
    [undefined, "es;q=0.1234", "en"],
    [undefined, "es".repeat(251), "en"],
  ])("cookie=%s, encabezado=%s resuelve %s", (cookie, header, expected) => {
    expect(resolveLocale(cookie, header)).toBe(expected);
  });

  it("carga el catálogo del idioma resuelto para cada request", async () => {
    const { default: configure } = await import("@/i18n/request");
    for (const locale of ["es", "en"] as const) {
      request.cookie = locale;
      request.header = locale === "es" ? "en" : "es";
      const result = await configure({ requestLocale: Promise.resolve(undefined) });
      expect(result.locale).toBe(locale);
      expect(result.messages).toEqual((await import(`../messages/${locale}/common.json`)).default);
    }
    expect(localeCookie).toBe("filmai_locale");
  });
});
