import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Footer } from "@/components/Footer";
import { routes } from "@/lib/routes";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import { render, screen, within } from "./render";

const path = vi.hoisted(() => ({ current: "/terms" }));
const account = vi.hoisted(() => ({
  perfil: null as null | Record<string, unknown>,
  cargando: false,
  actualizarPreferencia: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }),
  usePathname: () => path.current,
}));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => account,
}));

beforeEach(() => {
  path.current = "/terms";
  account.perfil = null;
  account.cargando = false;
});
afterEach(() => vi.clearAllMocks());

const links = (container: HTMLElement) =>
  Object.fromEntries(
    within(container)
      .getAllByRole("link")
      .map((link) => [link.getAttribute("aria-label") ?? link.textContent, link])
  );

describe("footer del canvas", () => {
  it("con sesión: columnas, idioma hacia Preferencias y avisos legales", () => {
    account.perfil = { nombre: "Juan" };
    render(<Footer />, { locale: "en" });
    const footer = screen.getByRole("contentinfo");
    const found = links(footer);

    expect(found[en.nav.main.brandHomeLabel]).toHaveAttribute("href", routes.explore);
    expect(found[en.nav.main.home]).toHaveAttribute("href", routes.explore);
    expect(found[en.nav.main.search]).toHaveAttribute("href", routes.search);
    expect(found[en.footer.main.myLists]).toHaveAttribute("href", routes.lists);
    expect(found[en.nav.main.ratingsReviews]).toHaveAttribute("href", routes.myReviews);
    expect(found[en.nav.main.profile]).toHaveAttribute("href", routes.profile);
    expect(found[en.nav.main.settings]).toHaveAttribute("href", routes.settings);
    expect(found[en.nav.main.terms]).toHaveAttribute("href", routes.terms);

    const language = en.footer.main.languageLink.replace("{language}", "English");
    expect(screen.getAllByRole("link", { name: language })).toHaveLength(2);
    for (const link of screen.getAllByRole("link", { name: language }))
      expect(link).toHaveAttribute("href", routes.language);

    expect(within(footer).queryByRole("radio")).toBeNull();
    expect(within(footer).queryByText(en.nav.account.signUp)).toBeNull();
    expect(within(footer).getByText(en.footer.main.tmdbAttribution)).toBeVisible();
    expect(
      within(footer).getByText(
        en.footer.main.copyright.replace("{year}", String(new Date().getFullYear()))
      )
    ).toBeVisible();
  });

  it("sin sesión: ofrece registro, ingreso y el selector de idioma", () => {
    render(<Footer />, { locale: "es" });
    const footer = screen.getByRole("contentinfo");
    const found = links(footer);

    expect(found[es.nav.account.signUp]).toHaveAttribute("href", routes.register);
    expect(found[es.nav.account.logIn]).toHaveAttribute("href", routes.login);
    expect(within(footer).getAllByRole("radiogroup").length).toBeGreaterThan(0);
    expect(within(footer).queryByRole("link", { name: /Preferencias\./ })).toBeNull();
  });

  it("la marca va a Home y la descripción cambia de escritorio a celular", () => {
    render(<Footer />, { locale: "en" });
    expect(screen.getByText(en.footer.main.descriptionDesktop)).toHaveClass("hidden", "md:block");
    expect(screen.getByText(en.footer.main.descriptionMobile)).toHaveClass("md:hidden");
  });

  it("no aparece en pantallas de acceso ni mientras carga la cuenta", () => {
    path.current = routes.login;
    const view = render(<Footer />, { locale: "en" });
    expect(view.container).toBeEmptyDOMElement();
    view.unmount();

    path.current = "/terms";
    account.cargando = true;
    const loading = render(<Footer />, { locale: "en" });
    expect(loading.container).toBeEmptyDOMElement();
  });
});
