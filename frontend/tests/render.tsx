import { render as testingRender, type RenderOptions } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement, ReactNode } from "react";
import type { AppLocale } from "@/i18n/config";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";

export * from "@testing-library/react";

/** Español por defecto para conservar los oráculos de las pantallas actuales. */
export function render(ui: ReactElement, options: RenderOptions & { locale?: AppLocale } = {}) {
  const { locale = "es", wrapper: Wrapper, ...rest } = options;
  function Localization({ children }: { children: ReactNode }) {
    return (
      <NextIntlClientProvider locale={locale} messages={locale === "es" ? es : en}>
        {Wrapper ? <Wrapper>{children}</Wrapper> : children}
      </NextIntlClientProvider>
    );
  }
  return testingRender(ui, { ...rest, wrapper: Localization });
}
