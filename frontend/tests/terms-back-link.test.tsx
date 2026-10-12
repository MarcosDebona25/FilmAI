import { beforeEach, describe, expect, it, vi } from "vitest";

import { TermsBackLink } from "@/components/TermsBackLink";
import { routes } from "@/lib/routes";
import en from "@/messages/en/common.json";
import { render, screen } from "./render";

const account = vi.hoisted(() => ({
  perfil: null as null | Record<string, unknown>,
  cargando: false,
}));
vi.mock("@/components/AccountProvider", () => ({ useAccount: () => account }));

beforeEach(() => {
  account.perfil = null;
  account.cargando = false;
});

describe("enlace de regreso de Terms en celular", () => {
  it("con sesión vuelve a Settings", () => {
    account.perfil = { nombre: "Juan" };
    render(<TermsBackLink />, { locale: "en" });
    expect(screen.getByRole("link", { name: en.nav.main.settings })).toHaveAttribute(
      "href",
      routes.settings
    );
  });

  it("sin sesión vuelve a la portada", () => {
    render(<TermsBackLink />, { locale: "en" });
    expect(screen.getByRole("link", { name: en.nav.main.backLanding })).toHaveAttribute(
      "href",
      routes.home
    );
  });

  it("mientras carga la cuenta no muestra ningún enlace", () => {
    account.cargando = true;
    render(<TermsBackLink />, { locale: "en" });
    expect(screen.queryByRole("link")).toBeNull();
  });
});
