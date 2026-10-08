import { useLocale } from "next-intl";
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
export function useFormats() {
  const locale = useLocale();
  return {
    date: (value: string | Date, style: "medium" | "long" = "medium") =>
      formatDate(value, locale, style),
    number: (value: number) => formatNumber(value, locale),
    rating: (value: number) => formatRating(value, locale),
    duration: (minutes: number) => formatDuration(minutes, locale),
  };
}
