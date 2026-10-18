import { useLocale, useTranslations } from "next-intl";
import { describe, expect, it } from "vitest";
import { render, screen } from "./render";

function LocaleProbe() {
  const locale = useLocale();
  const t = useTranslations("nav.main");
  return <p lang={locale}>{t("profile")}</p>;
}

describe("render con el proveedor real", () => {
  it("usa español por defecto sin cambiar los selectores heredados", () => {
    render(<LocaleProbe />);
    expect(screen.getByText("Mi perfil")).toHaveAttribute("lang", "es");
  });

  it("permite probar inglés y mantiene el envoltorio particular", () => {
    const view = render(<LocaleProbe />, {
      locale: "en",
      wrapper: ({ children }) => <section aria-label="Prueba">{children}</section>,
    });
    expect(screen.getByRole("region", { name: "Prueba" })).toHaveTextContent("My profile");
    view.rerender(<LocaleProbe />);
    expect(screen.getByText("My profile")).toHaveAttribute("lang", "en");
  });
});
