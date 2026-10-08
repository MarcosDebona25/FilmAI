export const locales = ["en", "es"] as const;
export type AppLocale = (typeof locales)[number];
export const defaultLocale: AppLocale = "en";
export const localeCookie = "filmai_locale";

export function isAppLocale(value: unknown): value is AppLocale {
  return value === "en" || value === "es";
}

/** La cookie admite solo códigos de la aplicación; el encabezado admite regiones. */
export function resolveLocale(cookie?: string, acceptLanguage?: string | null): AppLocale {
  if (isAppLocale(cookie)) return cookie;
  if (!acceptLanguage || acceptLanguage.length > 500) return defaultLocale;

  const preferences: { language: string; quality: number }[] = [];
  for (const preference of acceptLanguage.split(",")) {
    const match = preference
      .trim()
      .match(/^(\*|[a-z]{1,8}(?:-[a-z0-9]{1,8})*)(?:\s*;\s*q=(0(?:\.\d{0,3})?|1(?:\.0{0,3})?))?$/i);
    if (!match) return defaultLocale;
    preferences.push({ language: match[1].toLowerCase(), quality: Number(match[2] ?? 1) });
  }
  preferences.sort((a, b) => b.quality - a.quality);
  for (const { language, quality } of preferences) {
    const base = language.split("-")[0];
    if (quality > 0 && isAppLocale(base)) return base;
  }
  return defaultLocale;
}

export const intlLocales = { en: "en-US", es: "es-AR" } as const;
export const durationUnitDisplay = { en: "narrow", es: "short" } as const;
