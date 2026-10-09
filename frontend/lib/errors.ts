import { createTranslator } from "next-intl";
import { currentLocale } from "@/i18n/client";
import type { AppLocale } from "@/i18n/config";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";

export type ErrorParams = Record<string, string | number | string[] | number[]>;
export type FieldError = { field: string | null; code: string; params: ErrorParams };
export type CodedError = { code: string; params?: ErrorParams; errors?: FieldError[] };

export function translateError(
  error: CodedError,
  locale: AppLocale = currentLocale(),
  field?: string | null
): string {
  const t = createTranslator({
    locale,
    messages: locale === "es" ? es : en,
    onError: (error) => {
      throw error;
    },
  });
  const params = { ...error.params };
  if (typeof params.retry_after_seconds === "number")
    params.retryAfterSeconds = params.retry_after_seconds;
  const keys = [
    field ? `errors.fields.${field}.${error.code}` : "",
    error.code === "throttled" && params.retryAfterSeconds !== undefined
      ? "errors.codes.throttledWithWait"
      : "",
    `errors.codes.${error.code}`,
    "errors.codes.unknown",
  ];
  const key = keys.find((key) => key && t.has(key as Parameters<typeof t.has>[0]))!;
  try {
    return t(key as Parameters<typeof t>[0], params as never);
  } catch {
    return t("errors.codes.unknown");
  }
}

export function fieldErrors(
  error: CodedError,
  locale: AppLocale = currentLocale()
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const entry of error.errors ?? []) {
    if (entry.field && result[entry.field] === undefined)
      result[entry.field] = translateError(entry, locale, entry.field);
  }
  return result;
}
