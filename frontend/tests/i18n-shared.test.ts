import { afterEach, describe, expect, it, vi } from "vitest";
import { createTranslator } from "next-intl";
import { ApiError, apiFetch } from "@/lib/api";
import { translateError, fieldErrors } from "@/lib/errors";
import { formatDate, formatNumber, formatRating, formatDuration } from "@/lib/format";
import { intlLocales, durationUnitDisplay, localeCookie } from "@/i18n/config";
import { validarNombre, validarPassword, validarConfirmacion } from "@/lib/validation";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";

afterEach(() => {
  document.cookie = `${localeCookie}=; Max-Age=0`;
  document.cookie = "csrftoken=; Max-Age=0";
  vi.unstubAllGlobals();
});

describe.each(["en", "es"] as const)("capas compartidas %s", (locale) => {
  const t = createTranslator({ locale, messages: locale === "en" ? en : es });
  it("formatea fechas, enteros, decimales y duración con las mismas opciones que Intl", () => {
    expect(formatDate("2026-09-28", locale)).toBe(
      new Intl.DateTimeFormat(intlLocales[locale], { dateStyle: "medium", timeZone: "UTC" }).format(
        new Date("2026-09-28T00:00:00Z")
      )
    );
    expect(formatDate("2026-09-28", locale, "long")).toBe(
      new Intl.DateTimeFormat(intlLocales[locale], { dateStyle: "long", timeZone: "UTC" }).format(
        new Date("2026-09-28T00:00:00Z")
      )
    );
    expect(formatNumber(41355, locale)).toBe(
      new Intl.NumberFormat(intlLocales[locale]).format(41355)
    );
    expect(formatRating(8.5, locale)).toBe(
      new Intl.NumberFormat(intlLocales[locale], {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }).format(8.5)
    );
    const unit = (value: number, unit: string) =>
      new Intl.NumberFormat(intlLocales[locale], {
        style: "unit",
        unit,
        unitDisplay: durationUnitDisplay[locale],
      }).format(value);
    expect(formatDuration(169, locale)).toBe(`${unit(2, "hour")} ${unit(49, "minute")}`);
    expect(formatDuration(0, locale)).toBe(unit(0, "minute"));
  });
  it("prefiere campo, luego código y termina con desconocido", () => {
    expect(translateError({ code: "invalid" }, locale, "correo")).toBe(
      t("errors.fields.correo.invalid")
    );
    expect(translateError({ code: "invalid" }, locale, "otro")).toBe(t("errors.codes.invalid"));
    expect(translateError({ code: "interno" }, locale)).toBe(t("errors.codes.unknown"));
    expect(
      fieldErrors(
        {
          code: "validation_error",
          errors: [
            { field: "correo", code: "invalid", params: {} },
            { field: null, code: "invalid", params: {} },
          ],
        },
        locale
      )
    ).toEqual({ correo: t("errors.fields.correo.invalid") });
  });
  it("convierte la espera del contrato a plural ICU y no expone debug ni detail", () => {
    expect(translateError({ code: "throttled", params: { retry_after_seconds: 1 } }, locale)).toBe(
      t("errors.codes.throttledWithWait", { retryAfterSeconds: 1 })
    );
    document.documentElement.lang = locale;
    const error = new ApiError(500, {
      code: "server_error",
      params: {},
      errors: [],
      detail: "PRIVATE",
      debug: { message: "PRIVATE" },
    });
    expect(error.message).toBe(t("errors.codes.server_error"));
    expect(error).not.toHaveProperty("details");
    expect(error).not.toHaveProperty("debug");
  });
  it("envía Accept-Language también para CSRF y muestra código ante un error HTTP", async () => {
    document.documentElement.lang = locale;
    const fetch = vi
      .fn()
      .mockImplementationOnce(async () => {
        document.cookie = "csrftoken=test";
        return new Response("{}");
      })
      .mockResolvedValue(
        new Response(JSON.stringify({ code: "permission_denied", params: {}, errors: [] }), {
          status: 403,
        })
      );
    vi.stubGlobal("fetch", fetch);
    await expect(
      apiFetch("/api/preferences/", { method: "PUT", body: { perfil_publico: false } })
    ).rejects.toMatchObject({
      code: "permission_denied",
      message: t("errors.codes.permission_denied"),
    });
    expect(fetch.mock.calls[0][1].headers["Accept-Language"]).toBe(locale);
    expect(fetch.mock.calls[1][1].headers["Accept-Language"]).toBe(locale);
    expect(fetch.mock.calls[1][1].headers["X-CSRFToken"]).toBe("test");
  });
});
it("validaciones puras devuelven códigos y preservan los límites del dominio", () => {
  expect(validarNombre("")).toBe("required");
  expect(validarNombre("Ana Pérez")).toBeNull();
  expect(validarPassword("Password123*")).toBeNull();
  expect(validarPassword("short")).toBe("password_too_short_or_long");
  expect(validarConfirmacion("uno", "otro")).toBe("passwords_do_not_match");
});
