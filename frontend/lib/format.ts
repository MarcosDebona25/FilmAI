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
/**
 * Fecha escrita a mano en el campo de fecha de nacimiento. El orden lo decide el
 * idioma de la app, no el del navegador: `es` → DD/MM/AAAA, `en` → MM/DD/YYYY.
 */
const ordenDateInput = { es: ["day", "month"], en: ["month", "day"] } as const;
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** Arma el ISO `YYYY-MM-DD` con componentes locales (nunca `toISOString()`, que corre un día en UTC−3). */
export function isoDeFecha(fecha: Date) {
  const dos = (n: number) => String(n).padStart(2, "0");
  return `${String(fecha.getFullYear()).padStart(4, "0")}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}`;
}
/** `true` si `año-mes-día` existe en el calendario (el 31/02 no: `new Date` lo pasaría al 3 de marzo). */
export function fechaExiste(year: number, month: number, day: number) {
  const fecha = new Date(year, month - 1, day);
  return fecha.getFullYear() === year && fecha.getMonth() === month - 1 && fecha.getDate() === day;
}
/** «1992-04-10» → «10/04/1992» (`es`) / «04/10/1992» (`en`); vacío o inválido → «». */
export function formatDateInput(iso: string, locale: AppLocale) {
  const match = ISO_DATE.exec(iso);
  if (!match) return "";
  const [, year, month, day] = match;
  const partes = { day, month };
  const [primero, segundo] = ordenDateInput[locale];
  return `${partes[primero]}/${partes[segundo]}/${year}`;
}
/**
 * Texto del campo → ISO. Devuelve `null` si faltan dígitos o si la fecha no
 * existe. Acepta también el ISO tal cual (el autocompletado del navegador).
 */
export function parseDateInput(texto: string, locale: AppLocale): string | null {
  const iso = ISO_DATE.exec(texto.trim());
  if (iso) return fechaExiste(+iso[1], +iso[2], +iso[3]) ? texto.trim() : null;
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(texto.trim());
  if (!match) return null;
  const [primero, segundo] = ordenDateInput[locale];
  const partes = { [primero]: +match[1], [segundo]: +match[2] } as Record<"day" | "month", number>;
  const year = +match[3];
  if (!fechaExiste(year, partes.month, partes.day)) return null;
  return isoDeFecha(new Date(year, partes.month - 1, partes.day));
}
/**
 * Máscara del campo: deja solo dígitos (hasta 8) y pone las barras. Una barra
 * tipeada después de un solo dígito completa con cero («4/» → «04/»). Con
 * `barraFinal`, al completar el día o el mes se agrega la barra siguiente, así
 * el cursor salta solo al próximo segmento.
 */
export function maskDateInput(texto: string, barraFinal: boolean) {
  const segmentos: string[] = [];
  let actual = "";
  for (const caracter of texto) {
    if (/\d/.test(caracter)) {
      if (segmentos.length === 2 && actual.length === 4) break;
      actual += caracter;
      if (segmentos.length < 2 && actual.length === 2) {
        segmentos.push(actual);
        actual = "";
      }
    } else if (caracter === "/" && segmentos.length < 2 && actual.length === 1) {
      segmentos.push(`0${actual}`);
      actual = "";
    }
  }
  const partes = actual ? [...segmentos, actual] : segmentos;
  let resultado = partes.join("/");
  if (barraFinal && !actual && segmentos.length > 0 && segmentos.length < 3) resultado += "/";
  return resultado;
}
/** Mes abreviado del desplegable del calendario («abr» / «Apr»), con el código del locale de date-fns. */
export function formatCalendarMonth(fecha: Date, localeCode?: string) {
  return new Intl.DateTimeFormat(localeCode, { month: "short" }).format(fecha);
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
