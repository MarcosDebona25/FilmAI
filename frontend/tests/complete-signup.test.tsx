import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import { ApiError, apiFetch } from "@/lib/api";
import { render, screen, waitFor } from "./render";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
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
// El botón real lo dibuja el SDK de Google; acá entrega un id_token al tocarlo.
vi.mock("@/components/GoogleButton", () => ({
  GoogleButton: ({ onSuccess }: { onSuccess: (idToken: string) => void }) => (
    <button type="button" onClick={() => onSuccess("token-fresco")}>
      google
    </button>
  ),
}));

import CompletarGooglePage from "@/app/complete-signup/page";

type Usuario = ReturnType<typeof userEvent.setup>;

beforeEach(() => {
  sessionStorage.setItem("google_signup_pending", "1");
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => ({ disponible: true }) }))
  );
});
afterEach(() => {
  sessionStorage.clear();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

function confirmacion() {
  return screen.getByTestId("google-confirm");
}

async function completar(user: Usuario, copy: typeof en | typeof es = en) {
  await user.type(screen.getByLabelText(copy.common.fields.username), "juanperez");
  await user.type(screen.getByLabelText(copy.common.fields.birthDate), "1992-04-10");
  await user.selectOptions(screen.getByLabelText(copy.auth.signUp.genderLabel), "masculino");
  await user.click(screen.getByRole("checkbox"));
  await waitFor(() => expect(confirmacion()).not.toHaveAttribute("inert"));
}

function rechazar(errores: { field: string | null; code: string }[]) {
  vi.mocked(apiFetch).mockRejectedValueOnce(
    new ApiError(400, {
      code: "validation_error",
      params: {},
      errors: errores.map((error) => ({ ...error, params: {} })),
    })
  );
}

describe("alta con Google", () => {
  it("muestra la copia del canvas en inglés", () => {
    render(<CompletarGooglePage />, { locale: "en" });

    expect(
      screen.getByRole("heading", { level: 1, name: en.auth.completeSignUp.title })
    ).toBeInTheDocument();
    expect(screen.getByText(en.auth.completeSignUp.badge)).toBeInTheDocument();
    expect(screen.getByText(en.auth.completeSignUp.description)).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: en.auth.completeSignUp.genderPlaceholder })
    ).toBeDisabled();
    expect(screen.getByRole("link", { name: en.auth.completeSignUp.cancel })).toHaveAttribute(
      "href",
      "/login"
    );
  });

  it("muestra la copia del canvas en español", () => {
    render(<CompletarGooglePage />, { locale: "es" });

    expect(
      screen.getByRole("heading", { level: 1, name: es.auth.completeSignUp.title })
    ).toBeInTheDocument();
    expect(screen.getByText(es.auth.completeSignUp.badge)).toBeInTheDocument();
    expect(screen.getByText(es.auth.signUp.submitPending)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: es.auth.completeSignUp.cancel })).toBeInTheDocument();
  });

  it("recorrer los campos no muestra errores y el botón de Google queda inerte", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await user.click(screen.getByLabelText(en.common.fields.username));
    await user.tab();
    await user.tab();
    await user.tab();

    expect(screen.queryAllByRole("alert")).toHaveLength(0);
    expect(confirmacion()).toHaveAttribute("inert");
    expect(screen.getByText(en.auth.signUp.submitPending)).toBeInTheDocument();
  });

  it("con los datos válidos, el username disponible y los términos se activa", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await completar(user);

    expect(screen.getByText(en.auth.signUp.usernameAvailable)).toBeInTheDocument();
    expect(screen.queryByText(en.auth.signUp.submitPending)).not.toBeInTheDocument();
  });

  it("si el username está ocupado el botón no se activa", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => ({ disponible: false }) }))
    );
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await user.type(screen.getByLabelText(en.common.fields.username), "juanperez");
    await user.type(screen.getByLabelText(en.common.fields.birthDate), "1992-04-10");
    await user.selectOptions(screen.getByLabelText(en.auth.signUp.genderLabel), "masculino");
    await user.click(screen.getByRole("checkbox"));

    expect(await screen.findByText(en.errors.codes.username_already_used)).toBeInTheDocument();
    expect(confirmacion()).toHaveAttribute("inert");
  });

  it("confirma con el id_token fresco y lleva al Home", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ user: { nombre_usuario: "juanperez" } });
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await completar(user);
    await user.click(screen.getByRole("button", { name: "google" }));

    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/home"));
    expect(apiFetch).toHaveBeenCalledWith("/api/auth/google/", {
      method: "POST",
      body: {
        id_token: "token-fresco",
        nombre_usuario: "juanperez",
        fecha_nacimiento: "1992-04-10",
        genero: "masculino",
        acepta_terminos: true,
      },
    });
    expect(sessionStorage.getItem("google_signup_pending")).toBeNull();
  });

  it("si el backend rechaza el username marca el campo y pide reintentar", async () => {
    rechazar([{ field: "nombre_usuario", code: "username_already_used" }]);
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "es" });

    await completar(user, es);
    await user.click(screen.getByRole("button", { name: "google" }));

    expect(await screen.findByText(es.auth.completeSignUp.fixHighlighted)).toBeInTheDocument();
    expect(screen.getByText(es.errors.codes.username_already_used)).toBeInTheDocument();
    expect(screen.getByLabelText(es.common.fields.username)).toHaveAttribute(
      "aria-invalid",
      "true"
    );
    expect(router.push).not.toHaveBeenCalled();

    // Al corregir el campo, el aviso general desaparece.
    await user.type(screen.getByLabelText(es.common.fields.username), "2");
    expect(screen.queryByText(es.auth.completeSignUp.fixHighlighted)).not.toBeInTheDocument();
  });

  it("un error sin campo se muestra sin el aviso de campos marcados", async () => {
    rechazar([{ field: null, code: "email_already_used" }]);
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await completar(user);
    await user.click(screen.getByRole("button", { name: "google" }));

    expect(await screen.findByText(en.errors.codes.email_already_used)).toBeInTheDocument();
    expect(screen.queryByText(en.auth.completeSignUp.fixHighlighted)).not.toBeInTheDocument();
  });

  it("cancelar vuelve al login y descarta el alta pendiente", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });
    // jsdom no navega: se corta la navegación después del onClick del enlace.
    document.addEventListener("click", (event) => event.preventDefault(), { once: true });

    await user.click(screen.getByRole("link", { name: en.auth.completeSignUp.cancel }));

    expect(sessionStorage.getItem("google_signup_pending")).toBeNull();
  });

  it("sin un alta con Google pendiente redirige al login", () => {
    sessionStorage.clear();
    render(<CompletarGooglePage />, { locale: "en" });

    expect(router.replace).toHaveBeenCalledWith("/login");
  });
});
