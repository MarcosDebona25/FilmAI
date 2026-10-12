import type { AppLocale } from "./config";
import en from "../messages/en/common.json";
import es from "../messages/es/common.json";

declare module "next-intl" {
  interface AppConfig {
    Locale: AppLocale;
    Messages: typeof en | typeof es;
  }
}
