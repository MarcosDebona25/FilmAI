import { useLocale, useTranslations } from "next-intl";
import { describe, expect, it } from "vitest";
import { render, screen } from "./render";

function LocaleProbe() {
  const locale = useLocale();
  const t = useTranslations("legacy.metadata");
  return <p lang={locale}>{t("myReviews")}</p>;
}

describe("render con el proveedor real", () => {
  it("usa español por defecto sin cambiar los selectores heredados", () => {
    render(<LocaleProbe />);
    expect(screen.getByText("Mis reseñas")).toHaveAttribute("lang", "es");
  });

  it("permite probar inglés y mantiene el envoltorio particular", () => {
    const view = render(<LocaleProbe />, {
      locale: "en",
      wrapper: ({ children }) => <section aria-label="Prueba">{children}</section>,
    });
    expect(screen.getByRole("region", { name: "Prueba" })).toHaveTextContent("My reviews");
    view.rerender(<LocaleProbe />);
    expect(screen.getByText("My reviews")).toHaveAttribute("lang", "en");
  });
});
