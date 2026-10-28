import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NotFoundScreen, UnexpectedErrorScreen } from "@/components/errors/ErrorScreens";
import { AccountMenu } from "@/components/AccountMenu";
import { MobileTabs } from "@/components/MobileTabs";
import { Navbar } from "@/components/Navbar";
import { ApiError, apiFetch } from "@/lib/api";
import { routes } from "@/lib/routes";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import { fireEvent, render, screen, waitFor, within } from "./render";

/** El texto del enlace dentro de la invitación del 404 (`<register>…</register>`). */
function enlaceRegistro(catalogo: { errors: { pages: { signUpInvite: string } } }) {
  return /<register>(.*)<\/register>/.exec(catalogo.errors.pages.signUpInvite)?.[1] ?? "";
}

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }));
const path = vi.hoisted(() => ({ current: "/home" }));
const account = vi.hoisted(() => ({
  perfil: null as null | Record<string, unknown>,
  cargando: false,
  limpiar: vi.fn(),
}));
const toast = vi.hoisted(() => ({ error: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => path.current,
}));
vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}));
vi.mock("sonner", () => ({ toast }));
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => ({
    perfil: account.perfil,
    avatares: [{ id: 1, src: "/avatars/a.png" }],
    cargando: account.cargando,
    limpiar: account.limpiar,
  }),
}));

const perfil = {
  nombre: "Juan",
  apellido: "Pérez",
  nombre_usuario: "juanperez",
  avatar_id: 1,
};

beforeEach(() => {
  path.current = "/home";
  account.perfil = perfil;
  account.cargando = false;
});
afterEach(() => vi.clearAllMocks());

describe("pantalla 404", () => {
  it("explica el error y ofrece volver al inicio o buscar", () => {
    render(<NotFoundScreen />, { locale: "en" });
    expect(
      screen.getByRole("heading", { level: 1, name: en.errors.pages.notFoundTitle })
    ).toBeVisible();
    expect(screen.getByText(en.errors.pages.notFoundCode)).toBeVisible();
    expect(screen.getByText(en.errors.pages.notFoundDescription)).toBeVisible();
    expect(screen.getByRole("img", { name: en.errors.pages.ticketIllustrationAlt })).toBeVisible();
    expect(screen.getByRole("link", { name: en.nav.main.backHome })).toHaveAttribute(
      "href",
      routes.explore
    );
    expect(screen.getByRole("link", { name: en.nav.main.search })).toHaveAttribute(
      "href",
      routes.search
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("sin sesión invita a iniciar sesión o crear una cuenta, sin buscar", () => {
    account.perfil = null;
    render(<NotFoundScreen />, { locale: "en" });
    expect(
      screen.getByRole("heading", { level: 1, name: en.errors.pages.notFoundSignedOutTitle })
    ).toBeVisible();
    expect(screen.getByText(en.errors.pages.notFoundSignedOutDescription)).toBeVisible();
    expect(screen.getByRole("link", { name: en.nav.main.backHome })).toHaveAttribute(
      "href",
      routes.explore
    );
    expect(screen.getByRole("link", { name: en.nav.account.logIn })).toHaveAttribute(
      "href",
      routes.login
    );
    // La frase completa del canvas, con la mención del asistente (15/10/2026).
    expect(screen.getByText(/to rate films, keep your lists/)).toHaveTextContent(
      en.errors.pages.signUpInvite.replace(/<\/?register>/g, "")
    );
    expect(screen.getByRole("link", { name: enlaceRegistro(en) })).toHaveAttribute(
      "href",
      routes.register
    );
    expect(screen.queryByRole("link", { name: en.nav.main.search })).not.toBeInTheDocument();
  });

  it("mientras se resuelve la sesión conserva la variante con sesión", () => {
    account.perfil = null;
    account.cargando = true;
    render(<NotFoundScreen />, { locale: "en" });
    expect(
      screen.getByRole("heading", { level: 1, name: en.errors.pages.notFoundTitle })
    ).toBeVisible();
  });

  it("se muestra en español", () => {
    render(<NotFoundScreen />, { locale: "es" });
    expect(
      screen.getByRole("heading", { level: 1, name: es.errors.pages.notFoundTitle })
    ).toBeVisible();
    expect(screen.getByRole("link", { name: es.nav.main.backHome })).toBeVisible();
  });
});

describe("pantalla de error inesperado", () => {
  it("Try again reintenta con reset y Back to Home lleva al inicio", async () => {
    const reset = vi.fn();
    const user = userEvent.setup();
    render(<UnexpectedErrorScreen reset={reset} />, { locale: "en" });
    expect(
      screen.getByRole("heading", { level: 1, name: en.errors.pages.unexpectedTitle })
    ).toBeVisible();
    expect(screen.getByText(en.errors.pages.serverTitle)).toBeVisible();
    await user.click(screen.getByRole("button", { name: en.common.actions.retry }));
    expect(reset).toHaveBeenCalledOnce();
    expect(screen.getByRole("link", { name: en.nav.main.backHome })).toHaveAttribute(
      "href",
      routes.explore
    );
    expect(screen.queryByRole("link", { name: en.nav.main.search })).not.toBeInTheDocument();
  });
});

describe("menú de la cuenta", () => {
  const label = es.nav.account.userMenuLabel.replace("{name}", "Juan Pérez");

  it("nombra el botón con el usuario y muestra su identidad al abrir", async () => {
    const user = userEvent.setup();
    render(<AccountMenu />);
    const button = screen.getByRole("button", { name: label });
    expect(button).toHaveAttribute("aria-expanded", "false");
    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    const menu = screen.getByRole("menu", { name: es.nav.account.optionsLabel });
    expect(within(menu).getByText("Juan Pérez")).toBeVisible();
    expect(within(menu).getByText("@juanperez")).toBeVisible();
    expect(
      within(menu)
        .getAllByRole("menuitem")
        .map((item) => item.textContent)
    ).toEqual([
      es.nav.main.profile,
      es.nav.main.ratingsReviews,
      es.nav.main.settings,
      es.nav.account.logOut,
    ]);
    expect(screen.getByRole("menuitem", { name: es.nav.main.profile })).toHaveFocus();
    expect(screen.getByRole("menuitem", { name: es.nav.main.profile })).toHaveAttribute(
      "href",
      routes.profile
    );
  });

  it("navega con flechas, Home y End y cierra con Escape devolviendo el foco", async () => {
    const user = userEvent.setup();
    render(<AccountMenu />);
    const button = screen.getByRole("button", { name: label });
    await user.click(button);
    await user.keyboard("{ArrowUp}");
    expect(screen.getByRole("menuitem", { name: es.nav.account.logOut })).toHaveFocus();
    await user.keyboard("{Home}");
    expect(screen.getByRole("menuitem", { name: es.nav.main.profile })).toHaveFocus();
    await user.keyboard("{End}");
    expect(screen.getByRole("menuitem", { name: es.nav.account.logOut })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(button).toHaveFocus();
  });

  it("la confirmación es un <dialog> nativo y Escape (cancel) la cierra devolviendo el foco", async () => {
    const user = userEvent.setup();
    render(<AccountMenu />);
    await user.click(screen.getByRole("button", { name: label }));
    await user.click(screen.getByRole("menuitem", { name: es.nav.account.logOut }));
    const dialog = screen.getByRole("alertdialog");
    expect(dialog.tagName).toBe("DIALOG");
    fireEvent(dialog, new Event("cancel", { cancelable: true }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: label })).toHaveFocus();
  });

  it("cerrar sesión pide confirmación y Cancelar conserva la sesión", async () => {
    const user = userEvent.setup();
    render(<AccountMenu />);
    await user.click(screen.getByRole("button", { name: label }));
    await user.click(screen.getByRole("menuitem", { name: es.nav.account.logOut }));
    const dialog = screen.getByRole("alertdialog", { name: es.nav.account.logoutConfirmTitle });
    expect(within(dialog).getByText(es.nav.account.logoutConfirmDescription)).toBeVisible();
    expect(within(dialog).getByRole("button", { name: es.common.actions.cancel })).toHaveFocus();
    await user.click(within(dialog).getByRole("button", { name: es.common.actions.cancel }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(apiFetch).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: label })).toHaveFocus();
  });

  it("confirmar cierra la sesión, limpia la cuenta y vuelve a la landing", async () => {
    vi.mocked(apiFetch).mockResolvedValue({});
    const user = userEvent.setup();
    render(<AccountMenu />);
    await user.click(screen.getByRole("button", { name: label }));
    await user.click(screen.getByRole("menuitem", { name: es.nav.account.logOut }));
    const dialog = screen.getByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: es.nav.account.logOut }));
    await waitFor(() => expect(router.push).toHaveBeenCalledWith(routes.home));
    expect(apiFetch).toHaveBeenCalledWith("/api/auth/logout/", { method: "POST" });
    expect(account.limpiar).toHaveBeenCalledOnce();
  });

  it("si el servidor falla avisa y mantiene la sesión para reintentar", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new ApiError(500, { code: "server_error" }));
    const user = userEvent.setup();
    render(<AccountMenu />);
    await user.click(screen.getByRole("button", { name: label }));
    await user.click(screen.getByRole("menuitem", { name: es.nav.account.logOut }));
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", { name: es.nav.account.logOut })
    );
    await waitFor(() => expect(toast.error).toHaveBeenCalledOnce());
    expect(account.limpiar).not.toHaveBeenCalled();
    expect(router.push).not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog")).toBeVisible();
  });
});

describe("encabezado y barra inferior", () => {
  it("con sesión: marca, enlaces reales y menú de cuenta", () => {
    render(<Navbar />, { locale: "en" });
    expect(screen.getByRole("link", { name: en.nav.main.brandHomeLabel })).toHaveAttribute(
      "href",
      routes.explore
    );
    const nav = screen.getByRole("navigation", { name: en.nav.main.mainLabel });
    expect(within(nav).getByRole("link", { name: en.nav.main.home })).toHaveAttribute(
      "href",
      routes.explore
    );
    expect(within(nav).getByRole("link", { name: en.nav.main.search })).toHaveAttribute(
      "href",
      routes.search
    );
    expect(within(nav).getByRole("link", { name: en.nav.main.lists })).toHaveAttribute(
      "href",
      routes.lists
    );
    expect(screen.getByRole("button", { name: /Juan Pérez/ })).toBeVisible();
    expect(screen.queryByRole("link", { name: en.nav.account.logIn })).not.toBeInTheDocument();
  });

  it("marca la página actual", () => {
    path.current = routes.search;
    render(<Navbar />, { locale: "en" });
    expect(screen.getByRole("link", { name: en.nav.main.search })).toHaveAttribute(
      "aria-current",
      "page"
    );
    expect(screen.getByRole("link", { name: en.nav.main.home })).not.toHaveAttribute(
      "aria-current"
    );
  });

  it("sin sesión ofrece iniciar sesión y registrarse", () => {
    account.perfil = null;
    render(<Navbar />, { locale: "en" });
    expect(screen.getByRole("link", { name: en.nav.account.logIn })).toHaveAttribute(
      "href",
      routes.login
    );
    expect(screen.getByRole("link", { name: en.nav.account.signUp })).toHaveAttribute(
      "href",
      routes.register
    );
    expect(screen.queryByRole("button", { name: /menu/i })).not.toBeInTheDocument();
  });

  it("no aparece en las pantallas de acceso", () => {
    path.current = routes.login;
    const view = render(
      <>
        <Navbar />
        <MobileTabs />
      </>
    );
    expect(view.container).toBeEmptyDOMElement();
  });

  it("la barra inferior móvil enlaza Home, Search, Lists y Profile", () => {
    path.current = routes.lists;
    render(<MobileTabs />, { locale: "en" });
    const nav = screen.getByRole("navigation", { name: en.nav.main.mainLabel });
    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      routes.explore,
      routes.search,
      routes.lists,
      routes.profile,
    ]);
    expect(within(nav).getByRole("link", { name: en.nav.main.profileShort })).toBeVisible();
    expect(within(nav).getByRole("link", { name: en.nav.main.lists })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  it("la barra inferior no se muestra sin sesión", () => {
    account.perfil = null;
    const view = render(<MobileTabs />);
    expect(view.container).toBeEmptyDOMElement();
  });
});
