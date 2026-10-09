import { cookies, headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { localeCookie, resolveLocale } from "./config";

export default getRequestConfig(async () => {
  const [cookieStore, requestHeaders] = await Promise.all([cookies(), headers()]);
  const locale = resolveLocale(
    cookieStore.get(localeCookie)?.value,
    requestHeaders.get("accept-language")
  );
  return {
    locale,
    messages: (await import(`../messages/${locale}/common.json`)).default,
  };
});
