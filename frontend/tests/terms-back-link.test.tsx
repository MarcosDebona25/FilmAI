import { beforeEach, describe, expect, it, vi } from "vitest";

import { TermsBackLink } from "@/components/TermsBackLink";
import { routes } from "@/lib/routes";
import en from "@/messages/en/common.json";
import { render, screen, within } from "./render";

const account = vi.hoisted(() => ({
  perfil: null as null | Record<string, unknown>,
  cargando: false,
}));
vi.mock("@/components/AccountProvider", () => ({ useAccount: () => account }));

beforeEach(() => {
  account.perfil = null;
  account.cargando = false;
});

// jsdom no aplica CSS: el enlace de celular (`md:hidden`) y el de escritorio
// (`hidden md:…`) están los dos en el DOM.
describe("regreso de Terms", () => {
  it("con sesión: en celular vuelve a Settings y en escritorio muestra la miga", () => {
    account.perfil = { nombre: "Juan" };
    render(<TermsBackLink />, { locale: "en" });

    const aSettings = screen.getAllByRole("link", { name: en.nav.main.settings });
    expect(aSettings).toHaveLength(2);
    aSettings.forEach((enlace) => expect(enlace).toHaveAttribute("href", routes.settings));
    const miga = screen.getByRole("navigation", { name: en.nav.main.breadcrumbLabel });
    expect(within(miga).getByRole("link", { name: en.nav.main.profileShort })).toHaveAttribute(
      "href",
      routes.profile
    );
    expect(within(miga).getByText(en.nav.main.terms)).toHaveAttribute("aria-current", "page");
  });

  it("sin sesión vuelve a la portada, sin miga", () => {
    render(<TermsBackLink />, { locale: "en" });

    const enlaces = screen.getAllByRole("link", { name: en.nav.main.backLanding });
    expect(enlaces).toHaveLength(2);
    enlaces.forEach((enlace) => expect(enlace).toHaveAttribute("href", routes.home));
    expect(screen.queryByRole("navigation")).toBeNull();
  });

  it("mientras carga la cuenta no muestra ningún enlace", () => {
    account.cargando = true;
    render(<TermsBackLink />, { locale: "en" });
    expect(screen.queryByRole("link")).toBeNull();
  });
});
