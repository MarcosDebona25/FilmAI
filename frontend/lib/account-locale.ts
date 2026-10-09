import { apiFetch } from "./api";
import { persistLocale } from "@/i18n/client";
import { isAppLocale } from "@/i18n/config";

/** El login no siempre incluye idioma: leemos la cuenta antes de navegar. */
export async function synchronizeAccountLocale() {
  const profile = await apiFetch<{ idioma: unknown }>("/api/profile/");
  if (isAppLocale(profile.idioma)) persistLocale(profile.idioma);
}
