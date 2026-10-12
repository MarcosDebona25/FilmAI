import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import { ApiError, apiFetch } from "@/lib/api";
import { render, screen, waitFor } from "./render";

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }));
const params = vi.hoisted(() => ({ key: "clave%3Aabc" }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/register",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => params,
}));
vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}));
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}));
vi.mock("@/components/AccountProvider", () => ({
  useAccount: () => ({ recargar: vi.fn(), actualizarPreferencia: vi.fn(), perfil: null }),
}));
vi.mock("@/lib/account-locale", () => ({ synchronizeAccountLocale: vi.fn() }));
vi.mock("@/components/GoogleButton", () => ({ GoogleButton: () => null }));

import RegisterPage from "@/app/(public)/register/page";
import LoginPage from "@/app/(public)/login/page";
import ConfirmPage from "@/app/confirm-email/[key]/page";

beforeEach(() => {
  sessionStorage.clear();
  vi.mocked(apiFetch).mockResolvedValue({});
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => ({ disponible: true }) }))
  );
});
afterEach(() => {
  document.documentElement.lang = "en";
  vi.clearAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

async function fillRegister(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(en.common.fields.firstName), "Juan");
  await user.type(screen.getByLabelText(en.common.fields.lastName), "Pérez");
  await user.type(screen.getByLabelText(en.common.fields.username), "juanperez");
  await user.type(screen.getByLabelText(en.common.fields.email), "juan@example.com");
  await user.type(screen.getByLabelText(en.common.fields.birthDate), "1992-04-10");
  await user.selectOptions(screen.getByLabelText(en.auth.signUp.genderLabel), "masculino");
  await user.type(
    screen.getByLabelText(en.auth.password.label, { selector: "input" }),
    "Popcorn24!"
  );
  await user.type(screen.getByLabelText(en.common.fields.passwordConfirm), "Popcorn24!");
}

describe("registro", () => {
  it("sin aceptar los términos no envía y muestra el error del checkbox", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await fillRegister(user);
    await user.click(screen.getByRole("button", { name: en.nav.account.signUp }));
    expect(await screen.findByText(en.auth.signUp.termsRequiredError)).toBeInTheDocument();
    expect(screen.getByRole("checkbox")).toHaveAttribute("aria-invalid", "true");
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("aceptando los términos envía acepta_terminos y muestra la bandeja de entrada", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await fillRegister(user);
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: en.nav.account.signUp }));
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    const [path, options] = vi.mocked(apiFetch).mock.calls[0];
    expect(path).toBe("/api/auth/registration/");
    expect((options as { body: Record<string, unknown> }).body).toMatchObject({
      correo: "juan@example.com",
      nombre_usuario: "juanperez",
      acepta_terminos: true,
    });
    expect(
      await screen.findByRole("heading", { name: en.auth.confirmation.inboxTitle })
    ).toBeInTheDocument();
    expect(sessionStorage.getItem("filmai_pending_email")).toBe("juan@example.com");
    expect(screen.getByText(/Request another in 1:00/)).toBeInTheDocument();
  });

  it("muestra el error de términos que devuelve el backend", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError(400, {
        code: "validation_error",
        errors: [{ field: "acepta_terminos", code: "terms_not_accepted", params: {} }],
      })
    );
    document.documentElement.lang = "es";
    render(<RegisterPage />, { locale: "es" });
    await user.type(screen.getByLabelText(es.common.fields.firstName), "Juan");
    await user.type(screen.getByLabelText(es.common.fields.lastName), "Pérez");
    await user.type(screen.getByLabelText(es.common.fields.username), "juanperez");
    await user.type(screen.getByLabelText(es.common.fields.email), "juan@example.com");
    await user.type(screen.getByLabelText(es.common.fields.birthDate), "1992-04-10");
    await user.selectOptions(screen.getByLabelText(es.auth.signUp.genderLabel), "masculino");
    await user.type(
      screen.getByLabelText(es.auth.password.label, { selector: "input" }),
      "Popcorn24!"
    );
    await user.type(screen.getByLabelText(es.common.fields.passwordConfirm), "Popcorn24!");
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: es.nav.account.signUp }));
    expect(await screen.findByText(es.errors.codes.terms_not_accepted)).toBeInTheDocument();
  });

  it("marca como cumplida cada regla de contraseña a medida que se cumple", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    const input = screen.getByLabelText(en.auth.password.label, { selector: "input" });
    const rule = (text: string) => screen.getByText(text, { exact: false }).closest("li")!;
    expect(rule(en.auth.password.lengthRule)).toHaveTextContent(en.auth.password.ruleMissingLabel);
    await user.type(input, "Popcorn24");
    expect(rule(en.auth.password.lengthRule)).toHaveTextContent(
      en.auth.password.ruleSatisfiedLabel
    );
    expect(rule(en.auth.password.caseRule)).toHaveTextContent(en.auth.password.ruleSatisfiedLabel);
    expect(rule(en.auth.password.numberRule)).toHaveTextContent(
      en.auth.password.ruleSatisfiedLabel
    );
    expect(rule(en.auth.password.symbolRule)).toHaveTextContent(en.auth.password.ruleMissingLabel);
  });

  it("informa la disponibilidad del nombre de usuario", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await user.type(screen.getByLabelText(en.common.fields.username), "juanperez");
    expect(await screen.findByText(en.auth.signUp.usernameAvailable)).toBeInTheDocument();
  });

  it("el enlace a los términos abre en pestaña nueva", () => {
    render(<RegisterPage />, { locale: "en" });
    const link = screen.getByRole("link", { name: /Terms and Conditions/ });
    expect(link).toHaveAttribute("href", "/terms");
    expect(link).toHaveAttribute("target", "_blank");
  });
});

describe("login", () => {
  it("muestra el mensaje de credenciales incorrectas del diseño", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError(400, { code: "invalid_credentials", errors: [] })
    );
    render(<LoginPage />, { locale: "en" });
    await user.type(screen.getByLabelText(en.auth.login.identifierLabel), "juan");
    await user.type(screen.getByLabelText(en.auth.password.label, { selector: "input" }), "mala");
    await user.click(screen.getByRole("button", { name: en.nav.account.logIn }));
    expect(await screen.findByText(en.auth.login.invalidCredentials)).toBeInTheDocument();
  });

  it("recuperar contraseña abre el diálogo y confirma sin revelar la cuenta", async () => {
    const user = userEvent.setup();
    render(<LoginPage />, { locale: "en" });
    await user.click(screen.getByRole("button", { name: en.auth.password.forgot }));
    const dialog = await screen.findByRole("dialog", { name: en.auth.passwordReset.title });
    await user.type(dialog.querySelector("input")!, "juan@example.com");
    await user.click(screen.getByRole("button", { name: en.common.passwordReset.sendLink }));
    expect(await screen.findByText(/If juan@example.com has an account/)).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/api/auth/password/reset/", {
      method: "POST",
      body: { email: "juan@example.com" },
    });
  });
});

describe("confirmación", () => {
  it("cuenta confirmada ofrece iniciar sesión", async () => {
    render(<ConfirmPage />, { locale: "en" });
    expect(
      await screen.findByRole("heading", { name: en.auth.confirmation.successTitle })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: en.nav.account.logIn })).toHaveAttribute(
      "href",
      "/login"
    );
  });

  it("enlace vencido reenvía al correo guardado en este navegador", async () => {
    const user = userEvent.setup();
    sessionStorage.setItem("filmai_pending_email", "juan@example.com");
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiError(400, { code: "link_expired" }));
    vi.mocked(apiFetch).mockResolvedValue({});
    render(<ConfirmPage />, { locale: "en" });
    expect(
      await screen.findByRole("heading", { name: en.auth.confirmation.invalidTitle })
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: en.common.email.resendLink }));
    expect(
      await screen.findByRole("heading", { name: en.auth.confirmation.inboxTitle })
    ).toBeInTheDocument();
    expect(apiFetch).toHaveBeenLastCalledWith("/api/auth/registration/resend-email/", {
      method: "POST",
      body: { email: "juan@example.com" },
    });
  });

  it("enlace vencido sin correo guardado lo pide antes de reenviar", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiError(400, { code: "link_expired" }));
    vi.mocked(apiFetch).mockResolvedValue({});
    render(<ConfirmPage />, { locale: "en" });
    await user.click(await screen.findByRole("button", { name: en.common.email.resendLink }));
    await user.type(screen.getByLabelText(en.common.fields.email), "ana@example.com");
    await user.click(screen.getByRole("button", { name: en.common.email.resendLink }));
    expect(
      await screen.findByRole("heading", { name: en.auth.confirmation.inboxTitle })
    ).toBeInTheDocument();
  });
});
