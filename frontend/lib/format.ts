import { useLocale } from "next-intl";
import enums from "@/i18n/enums.json";
import { intlLocales, durationUnitDisplay, type AppLocale } from "@/i18n/config";

function asDate(value: string | Date) {
  return typeof value === "string"
    ? new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00Z` : value)
    : value;
}
export function formatDate(
  value: string | Date,
  locale: AppLocale,
  style: "medium" | "long" = "medium"
) {
  return new Intl.DateTimeFormat(intlLocales[locale], { dateStyle: style, timeZone: "UTC" }).format(
    asDate(value)
  );
}
/** Fecha numérica compacta («18/10/2026» / «10/18/2026»), en la zona horaria del navegador. */
export function formatDateShort(value: string | Date, locale: AppLocale) {
  return new Intl.DateTimeFormat(intlLocales[locale], {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(asDate(value));
}
export function formatNumber(value: number, locale: AppLocale) {
  return new Intl.NumberFormat(intlLocales[locale]).format(value);
}
export function formatRating(value: number, locale: AppLocale) {
  return new Intl.NumberFormat(intlLocales[locale], {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}
export function formatDuration(minutes: number, locale: AppLocale) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  const unit = (value: number, unit: "hour" | "minute") =>
    new Intl.NumberFormat(intlLocales[locale], {
      style: "unit",
      unit,
      unitDisplay: durationUnitDisplay[locale],
    }).format(value);
  return [hours ? unit(hours, "hour") : "", remainder || !hours ? unit(remainder, "minute") : ""]
    .filter(Boolean)
    .join(" ");
}
/** «Thriller, Drama, and Crime» / «Suspense, Drama y Crimen». */
export function formatList(values: string[], locale: AppLocale) {
  return new Intl.ListFormat(intlLocales[locale], { style: "long", type: "conjunction" }).format(
    values
  );
}
/** Nombre de un país (código ISO 3166-1 alfa-2) en el idioma activo; sin soporte, el código. */
export function formatPais(code: string, locale: AppLocale) {
  try {
    return new Intl.DisplayNames(intlLocales[locale], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}
/** Todos los países ordenados por nombre en el idioma activo. */
export function paisesOrdenados(locale: AppLocale) {
  return enums.paisCodes
    .map((code) => ({ code, name: formatPais(code, locale) }))
    .sort((a, b) => a.name.localeCompare(b.name, intlLocales[locale]));
}
/** Región del navegador (`es-AR` -> `AR`) si es un país de la lista; si no, `null`. */
export function regionDelNavegador(): string | null {
  if (typeof navigator === "undefined") return null;
  for (const tag of navigator.languages?.length ? navigator.languages : [navigator.language]) {
    try {
      const region = new Intl.Locale(tag).region;
      if (region && enums.paisCodes.includes(region)) return region;
    } catch {
      // Etiqueta inválida: se prueba la siguiente.
    }
  }
  return null;
}
export function useFormats() {
  const locale = useLocale();
  return {
    date: (value: string | Date, style: "medium" | "long" = "medium") =>
      formatDate(value, locale, style),
    dateShort: (value: string | Date) => formatDateShort(value, locale),
    number: (value: number) => formatNumber(value, locale),
    rating: (value: number) => formatRating(value, locale),
    duration: (minutes: number) => formatDuration(minutes, locale),
    list: (values: string[]) => formatList(values, locale),
    country: (code: string) => formatPais(code, locale),
  };
}
