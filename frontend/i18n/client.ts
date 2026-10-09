import { defaultLocale, isAppLocale, localeCookie, type AppLocale } from "./config";

/** El idioma del documento es la resolución SSR cuando todavía no hay cookie. */
export function currentLocale(): AppLocale {
  if (typeof document === "undefined") return defaultLocale;
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${localeCookie}=`))
    ?.split("=")[1];
  if (isAppLocale(cookie)) return cookie;
  return isAppLocale(document.documentElement.lang) ? document.documentElement.lang : defaultLocale;
}

export function persistLocale(locale: AppLocale): boolean {
  const changed = currentLocale() !== locale;
  document.cookie = `${localeCookie}=${locale}; Path=/; Max-Age=31536000; SameSite=Lax${location.protocol === "https:" ? "; Secure" : ""}`;
  document.documentElement.lang = locale;
  return changed;
}
