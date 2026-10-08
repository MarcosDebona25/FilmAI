import type { AppLocale } from "./config";
import messages from "../messages/en/common.json";

declare module "next-intl" {
  interface AppConfig {
    Locale: AppLocale;
    Messages: typeof messages;
  }
}
