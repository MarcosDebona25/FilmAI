import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import en from "@/messages/en/common.json";
import { ApiError, apiFetch } from "@/lib/api";
import { elegirPais } from "./elegir-pais";
import { fireEvent, render, screen, waitFor, within } from "./render";

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }));
const params = vi.hoisted(() => ({ key: "clave%3Aabc" }));
const consulta = vi.hoisted(() => ({ texto: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/register",
  useSearchParams: () => new URLSearchParams(consulta.texto),
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

// Catálogo público de avatares que el registro pide al montarse (GET /api/avatars/).
const catalogoAvatares = [
  { id: 1, src: "/uno.png" },
  { id: 2, src: "/dos.png" },
  { id: 3, src: "/tres.png" },
];

/** Simula la API por ruta: el catálogo responde siempre y el alta lo decide cada test. */
function simularApi(alta: () => Promise<unknown> = async () => ({})) {
  vi.mocked(apiFetch).mockImplementation(async (path) =>
    path === "/api/avatars/" ? catalogoAvatares : alta()
  );
}

/** Cuerpo que el formulario mandó al endpoint de registro. */
function cuerpoDelAlta() {
  const llamada = vi
    .mocked(apiFetch)
    .mock.calls.find(([ruta]) => ruta === "/api/auth/registration/");
  return (llamada?.[1] as { body: Record<string, unknown> }).body;
}

beforeEach(() => {
  consulta.texto = "";
  sessionStorage.clear();
  simularApi();
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

const signUp = en.auth.signUp;

function barra() {
  return screen.getByRole("progressbar", { name: signUp.progressLabel });
}

/** «Continue» a secas: «Continue with Google» también es un botón. */
function continuar() {
  return screen.getByRole("button", { name: signUp.continue });
}

async function llenarPaso1(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(en.common.fields.email), "juan@example.com");
  await user.type(
    screen.getByLabelText(en.auth.password.label, { selector: "input" }),
    "Popcorn24!"
  );
  await user.type(screen.getByLabelText(en.common.fields.passwordConfirm), "Popcorn24!");
}

async function llenarPaso2(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(en.common.fields.firstName), "Juan");
  await user.type(screen.getByLabelText(en.common.fields.lastName), "Pérez");
  await user.type(screen.getByLabelText(en.common.fields.username), "juanperez");
  // En inglés el campo va en MM/DD/YYYY: 10 de abril de 1992.
  await user.type(screen.getByLabelText(en.common.fields.birthDate), "04/10/1992");
  await user.selectOptions(screen.getByLabelText(signUp.genderLabel), "masculino");
  await elegirPais(user, screen.getByLabelText(en.common.fields.country), "Argentina");
  expect(await screen.findByText(signUp.usernameAvailable)).toBeInTheDocument();
}

async function irAlPaso2(user: ReturnType<typeof userEvent.setup>) {
  await llenarPaso1(user);
  await user.click(continuar());
  await waitFor(() => expect(barra()).toHaveAttribute("aria-valuenow", "2"));
}

async function irAlPaso3(user: ReturnType<typeof userEvent.setup>) {
  await irAlPaso2(user);
  await llenarPaso2(user);
  await user.click(continuar());
  await waitFor(() => expect(barra()).toHaveAttribute("aria-valuenow", "3"));
}

function crearCuenta() {
  return screen.getByRole("button", { name: signUp.createAccount });
}

/** Rechazo del alta con errores por campo, como los devuelve la API. */
function rechazoPorCampos(...campos: [string, string][]) {
  return async () => {
    throw new ApiError(400, {
      code: "validation_error",
      errors: campos.map(([field, code]) => ({ field, code, params: {} })),
    });
  };
}

describe("registro en pasos", () => {
  it("arranca en el paso 1: barra en 1 de 3, solo sus campos y sin «Back»", () => {
    render(<RegisterPage />, { locale: "en" });
    expect(screen.getByRole("heading", { level: 1, name: signUp.title })).toBeInTheDocument();
    expect(screen.getByText(signUp.subtitle)).toBeInTheDocument();
    expect(barra()).toHaveAttribute("aria-valuemin", "0");
    expect(barra()).toHaveAttribute("aria-valuemax", "3");
    expect(barra()).toHaveAttribute("aria-valuenow", "1");
    expect(barra()).toHaveAttribute("aria-valuetext", "Step 1 of 3");
    expect(barra().firstElementChild).toHaveStyle({ width: "33.33%" });
    expect(screen.getByLabelText(en.common.fields.email)).toBeInTheDocument();
    // Los otros pasos siguen montados (ocultos e inertes): se consulta por rol.
    expect(screen.queryByRole("textbox", { name: en.common.fields.firstName })).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
    // «Back» guarda su lugar pero no se ve ni se puede usar.
    expect(screen.queryByRole("button", { name: /^Back/ })).toBeNull();
    expect(screen.getByText(signUp.back).closest("button")).toHaveStyle({ visibility: "hidden" });
  });

  it("los tres pasos están siempre montados; los no activos quedan inertes y ocultos", async () => {
    const user = userEvent.setup();
    const { container } = render(<RegisterPage />, { locale: "en" });
    const pasos = () => [...container.querySelectorAll<HTMLElement>("[data-paso]")];
    /** Qué pasos están a la vista de teclado y lectores de pantalla. */
    const activos = () =>
      pasos()
        .filter((p) => !p.hasAttribute("inert") && p.getAttribute("aria-hidden") !== "true")
        .map((p) => p.dataset.paso);
    // Los tres comparten una celda de la grilla: mide lo que el más alto.
    expect(pasos()).toHaveLength(3);
    expect(activos()).toEqual(["1"]);
    for (const oculto of pasos().slice(1)) {
      expect(oculto).toHaveAttribute("inert");
      expect(oculto).toHaveAttribute("aria-hidden", "true");
      expect(oculto).toHaveClass("invisible");
    }
    // Solo el paso activo se alcanza por rol.
    expect(screen.getByRole("textbox", { name: en.common.fields.email })).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: en.common.fields.firstName })).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();

    await irAlPaso2(user);
    expect(activos()).toEqual(["2"]);
    expect(screen.queryByRole("textbox", { name: en.common.fields.email })).toBeNull();
    expect(screen.getByRole("textbox", { name: en.common.fields.firstName })).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("un paso inválido no avanza y muestra los errores de sus campos", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    expect(screen.queryAllByRole("alert")).toHaveLength(0);
    await user.click(continuar());
    expect(barra()).toHaveAttribute("aria-valuenow", "1");
    expect(screen.getAllByRole("alert").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByLabelText(en.common.fields.email)).toHaveAttribute("aria-invalid", "true");
  });

  it("«Continue» avanza, mueve la barra y deja el foco en el primer campo del paso", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await irAlPaso2(user);
    expect(barra()).toHaveAttribute("aria-valuetext", "Step 2 of 3");
    expect(barra().firstElementChild).toHaveStyle({ width: "66.67%" });
    expect(screen.getByLabelText(en.common.fields.firstName)).toHaveFocus();
    // Los otros pasos siguen montados (ocultos e inertes): se consulta por rol.
    expect(screen.queryByRole("textbox", { name: en.common.fields.email })).toBeNull();
    // Entrar a un paso no muestra errores de campos que nadie tocó.
    expect(screen.queryAllByRole("alert")).toHaveLength(0);

    await llenarPaso2(user);
    await user.click(continuar());
    await waitFor(() => expect(barra()).toHaveAttribute("aria-valuetext", "Step 3 of 3"));
    expect(barra().firstElementChild).toHaveStyle({ width: "100%" });
    // En el paso 3 el botón principal pasa a ser «Create account».
    expect(crearCuenta()).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: signUp.continue })).toBeNull();
    expect(screen.getByRole("button", { name: signUp.avatarChoose })).toHaveFocus();
  });

  it("«Back» retrocede un paso, conserva lo escrito y enfoca el primer campo", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await irAlPaso2(user);
    await user.type(screen.getByLabelText(en.common.fields.firstName), "Juan");
    await user.click(screen.getByRole("button", { name: "Back to step 1" }));

    expect(barra()).toHaveAttribute("aria-valuenow", "1");
    const correo = screen.getByLabelText(en.common.fields.email);
    expect(correo).toHaveFocus();
    expect(correo).toHaveValue("juan@example.com");
    expect(screen.getByLabelText(en.auth.password.label, { selector: "input" })).toHaveValue(
      "Popcorn24!"
    );
    expect(screen.getByLabelText(en.common.fields.passwordConfirm)).toHaveValue("Popcorn24!");

    await user.click(continuar());
    expect(await screen.findByLabelText(en.common.fields.firstName)).toHaveValue("Juan");
    expect(screen.getByRole("button", { name: "Back to step 1" })).toBeVisible();
  });

  it("Enter en un campo hace lo mismo que el botón principal", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await llenarPaso1(user);
    await user.type(screen.getByLabelText(en.common.fields.passwordConfirm), "{Enter}");
    await waitFor(() => expect(barra()).toHaveAttribute("aria-valuenow", "2"));
  });

  it("marca como obligatorios los campos de cada paso", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    const obligatorios = (etiquetas: string[]) => {
      for (const etiqueta of etiquetas)
        expect(
          screen.getByLabelText(etiqueta, { selector: "input, select, button" })
        ).toBeRequired();
    };
    obligatorios([
      en.common.fields.email,
      en.auth.password.label,
      en.common.fields.passwordConfirm,
    ]);
    await irAlPaso2(user);
    obligatorios([
      en.common.fields.firstName,
      en.common.fields.lastName,
      en.common.fields.username,
      en.common.fields.birthDate,
      signUp.genderLabel,
      en.common.fields.country,
    ]);
    await llenarPaso2(user);
    await user.click(continuar());
    expect(await screen.findByRole("checkbox")).toBeRequired();
  });

  it("el país arranca vacío aunque el navegador tenga región, ordenado por nombre y con error si queda vacío", async () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("es-AR");
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await irAlPaso2(user);
    const pais = screen.getByLabelText(en.common.fields.country);
    expect(pais).toHaveTextContent(en.common.country.placeholder);
    await user.click(pais);
    const nombres = within(screen.getByRole("listbox"))
      .getAllByRole("option")
      .map((option) => option.textContent!);
    expect(nombres).toHaveLength(249);
    expect(nombres).toEqual([...nombres].sort((a, b) => a.localeCompare(b, "en")));
    // Abrirlo y salir sin elegir muestra que es obligatorio.
    await user.tab();
    expect(await screen.findByText(en.common.country.required)).toBeInTheDocument();
    await elegirPais(user, pais, "Brazil");
    expect(screen.queryByText(en.common.country.required)).not.toBeInTheDocument();
  });

  it("el error de un campo aparece al escribir un valor inválido y se va al corregirlo", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    const email = screen.getByLabelText(en.common.fields.email);
    await user.type(email, "abc");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await user.type(email, "@example.com");
    await waitFor(() => expect(screen.queryAllByRole("alert")).toHaveLength(0));
  });

  it("un campo que se escribió y se vació muestra que es obligatorio", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    const email = screen.getByLabelText(en.common.fields.email);
    await user.type(email, "j");
    await user.clear(email);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("la confirmación se revalida al editar la contraseña original", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    const password = screen.getByLabelText(en.auth.password.label, { selector: "input" });
    const confirm = screen.getByLabelText(en.common.fields.passwordConfirm);
    await user.type(password, "Popcorn24!");
    await user.type(confirm, "Popcorn24!");
    await waitFor(() => expect(screen.queryAllByRole("alert")).toHaveLength(0));

    // Al cambiar la original, la confirmación ya no coincide: el error aparece.
    await user.type(password, "x");
    expect(await screen.findByText(en.errors.codes.passwords_do_not_match)).toBeInTheDocument();

    // Al volver a la contraseña original, el error desaparece sin tocar la confirmación.
    await user.type(password, "{Backspace}");
    await waitFor(() =>
      expect(screen.queryByText(en.errors.codes.passwords_do_not_match)).toBeNull()
    );
  });

  it("la confirmación sin editar no muestra error aunque cambie la contraseña", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await user.type(
      screen.getByLabelText(en.auth.password.label, { selector: "input" }),
      "Popcorn24!"
    );
    await new Promise((resolve) => setTimeout(resolve, 800));
    expect(screen.queryByText(en.errors.codes.passwords_do_not_match)).toBeNull();
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

  it("con el usuario disponible el ✓ va dentro del campo y la ayuda no se mueve (#175)", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await irAlPaso2(user);
    const input = screen.getByLabelText(en.common.fields.username);
    await user.type(input, "juanperez");
    // «Available» lo anuncia la región viva, sin un renglón visible propio.
    expect(await screen.findByText(signUp.usernameAvailable)).toHaveClass("sr-only");
    expect(input.parentElement!.querySelector("svg")).not.toBeNull();
    expect(input).not.toHaveAttribute("aria-invalid");
    const ayuda = screen.getByText(signUp.usernameHelp);
    expect(ayuda.parentElement).not.toHaveClass("invisible");
  });

  it("un usuario en uso es un error del campo y no deja avanzar (#175)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => ({ disponible: false }) }))
    );
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await irAlPaso2(user);
    const input = screen.getByLabelText(en.common.fields.username);
    await user.type(input, "juanperez");
    expect(await screen.findByText(en.errors.codes.username_already_used)).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input.parentElement!.querySelector("svg")).toBeNull();
    // La ayuda sigue en la misma celda pero invisible: el campo no cambia de alto.
    expect(screen.getByText(signUp.usernameHelp).parentElement).toHaveClass("invisible");
    await user.click(continuar());
    expect(barra()).toHaveAttribute("aria-valuenow", "2");
  });

  it("los campos sin ayuda reservan el renglón del error desde el inicio (#175)", () => {
    render(<RegisterPage />, { locale: "en" });
    for (const etiqueta of [en.common.fields.email, en.common.fields.passwordConfirm]) {
      const campo = screen.getByLabelText(etiqueta, { selector: "input" });
      const info = document.getElementById(campo.getAttribute("aria-describedby")!)!;
      expect(info.querySelector(".min-h-\\[1lh\\]") ?? info).toHaveClass("min-h-[1lh]");
    }
  });

  it("sin aceptar los términos no crea la cuenta y lo avisa en la casilla", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await irAlPaso3(user);
    const link = screen.getByRole("link", { name: /Terms and Conditions/ });
    expect(link).toHaveAttribute("href", "/terms");
    expect(link).toHaveAttribute("target", "_blank");

    await user.click(crearCuenta());
    expect(await screen.findByText(en.errors.codes.terms_not_accepted)).toBeInTheDocument();
    expect(screen.getByRole("checkbox")).toHaveAttribute("aria-invalid", "true");
    expect(
      vi.mocked(apiFetch).mock.calls.some(([ruta]) => ruta === "/api/auth/registration/")
    ).toBe(false);
    // Aceptarlos borra el aviso.
    await user.click(screen.getByRole("checkbox"));
    expect(screen.queryByText(en.errors.codes.terms_not_accepted)).toBeNull();
  });

  it("con los tres pasos completos envía el alta y muestra la bandeja de entrada", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />, { locale: "en" });
    await irAlPaso3(user);
    await user.click(screen.getByRole("checkbox"));
    await user.click(crearCuenta());
    await waitFor(() => expect(cuerpoDelAlta).not.toThrow());
    expect(cuerpoDelAlta()).toMatchObject({
      correo: "juan@example.com",
      password1: "Popcorn24!",
      password2: "Popcorn24!",
      nombre: "Juan",
      apellido: "Pérez",
      nombre_usuario: "juanperez",
      fecha_nacimiento: "1992-04-10",
      genero: "masculino",
      pais: "AR",
      acepta_terminos: true,
      // Sin abrir el diálogo viaja el primero del catálogo.
      avatar_id: 1,
    });
    expect(
      await screen.findByRole("heading", { name: en.auth.confirmation.inboxTitle })
    ).toBeInTheDocument();
    expect(sessionStorage.getItem("filmai_pending_email")).toBe("juan@example.com");
    expect(screen.getByText(/Request another in 1:00/)).toBeInTheDocument();
  });

  it("si el catálogo no carga, el paso 3 no ofrece avatar y el alta sale sin ese campo", async () => {
    const user = userEvent.setup();
    vi.mocked(apiFetch).mockImplementation(async (path) => {
      if (path === "/api/avatars/") throw new ApiError(500, { code: "unknown" });
      return {};
    });
    render(<RegisterPage />, { locale: "en" });
    await irAlPaso3(user);
    expect(screen.queryByRole("button", { name: signUp.avatarChoose })).toBeNull();
    // Sin avatar, el primer campo del paso es la casilla de los términos.
    expect(screen.getByRole("checkbox")).toHaveFocus();
    await user.click(screen.getByRole("checkbox"));
    await user.click(crearCuenta());
    await waitFor(() => expect(cuerpoDelAlta).not.toThrow());
    expect(cuerpoDelAlta()).not.toHaveProperty("avatar_id");
  });

  describe("diálogo de avatar", () => {
    async function abrir(user: ReturnType<typeof userEvent.setup>) {
      await irAlPaso3(user);
      await user.click(screen.getByRole("button", { name: signUp.avatarChoose }));
      return screen.getByRole("dialog", { name: signUp.avatarLabel });
    }
    const radio = (n: number) => screen.getByRole("radio", { name: `Avatar ${n}` });

    it("elegir solo marca; «Use this avatar» aplica, cierra y devuelve el foco a «Choose»", async () => {
      const user = userEvent.setup();
      render(<RegisterPage />, { locale: "en" });
      const dialogo = await abrir(user);
      expect(within(within(dialogo).getByRole("radiogroup")).getAllByRole("radio")).toHaveLength(3);
      expect(radio(1)).toHaveAttribute("aria-checked", "true");
      expect(radio(1)).toHaveFocus();

      await user.click(radio(3));
      expect(radio(3)).toHaveAttribute("aria-checked", "true");
      // Elegir no cierra: el diálogo sigue abierto hasta confirmar.
      expect(dialogo).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: signUp.avatarUse }));

      expect(screen.queryByRole("dialog")).toBeNull();
      expect(screen.getByRole("button", { name: signUp.avatarChoose })).toHaveFocus();
      await user.click(screen.getByRole("checkbox"));
      await user.click(crearCuenta());
      await waitFor(() => expect(cuerpoDelAlta).not.toThrow());
      expect(cuerpoDelAlta()).toMatchObject({ avatar_id: 3 });
    });

    it.each([
      [
        "«Cancel»",
        (user: ReturnType<typeof userEvent.setup>) =>
          user.click(screen.getByRole("button", { name: en.common.actions.cancel })),
      ],
      [
        "la ✕",
        (user: ReturnType<typeof userEvent.setup>) =>
          user.click(screen.getByRole("button", { name: en.common.actions.close })),
      ],
      [
        "Esc",
        async () => {
          fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
        },
      ],
      [
        "el fondo",
        async () => {
          // Un clic fuera de la caja del diálogo cae sobre el `<dialog>` mismo.
          fireEvent.click(screen.getByRole("dialog"), { clientX: 900, clientY: 900 });
        },
      ],
    ])("%s cierra sin cambiar el avatar", async (_nombre, cerrar) => {
      const user = userEvent.setup();
      render(<RegisterPage />, { locale: "en" });
      await abrir(user);
      await user.click(radio(2));
      await cerrar(user);

      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
      expect(screen.getByRole("button", { name: signUp.avatarChoose })).toHaveFocus();
      // Al reabrir, sigue marcado el avatar que estaba aplicado.
      await user.click(screen.getByRole("button", { name: signUp.avatarChoose }));
      expect(radio(1)).toHaveAttribute("aria-checked", "true");
    });
  });

  describe("rechazo del servidor", () => {
    async function enviar(user: ReturnType<typeof userEvent.setup>) {
      await irAlPaso3(user);
      await user.click(screen.getByRole("checkbox"));
      await user.click(crearCuenta());
    }

    it("un error en un campo del paso 2 vuelve a ese paso y lo muestra en el campo", async () => {
      simularApi(rechazoPorCampos(["nombre_usuario", "username_already_used"]));
      const user = userEvent.setup();
      render(<RegisterPage />, { locale: "en" });
      await enviar(user);

      await waitFor(() => expect(barra()).toHaveAttribute("aria-valuenow", "2"));
      const usuario = screen.getByLabelText(en.common.fields.username);
      expect(usuario).toHaveAttribute("aria-invalid", "true");
      expect(usuario).toHaveFocus();
      expect(screen.getByText(en.errors.codes.username_already_used)).toBeInTheDocument();
      // Lo escrito en los otros pasos sigue ahí.
      expect(usuario).toHaveValue("juanperez");
    });

    it("con errores en varios pasos vuelve al del primero en el orden de los pasos", async () => {
      simularApi(
        rechazoPorCampos(
          ["nombre_usuario", "username_already_used"],
          ["correo", "email_already_used"]
        )
      );
      const user = userEvent.setup();
      render(<RegisterPage />, { locale: "en" });
      await enviar(user);

      await waitFor(() => expect(barra()).toHaveAttribute("aria-valuenow", "1"));
      const correo = screen.getByLabelText(en.common.fields.email);
      expect(correo).toHaveAttribute("aria-invalid", "true");
      expect(correo).toHaveFocus();
      // El error del paso 2 espera en su campo.
      await user.click(continuar());
      expect(await screen.findByLabelText(en.common.fields.username)).toHaveAttribute(
        "aria-invalid",
        "true"
      );
    });

    it("el error de términos se queda en el paso 3", async () => {
      simularApi(rechazoPorCampos(["acepta_terminos", "terms_not_accepted"]));
      const user = userEvent.setup();
      render(<RegisterPage />, { locale: "en" });
      await enviar(user);
      expect(await screen.findByText(en.errors.codes.terms_not_accepted)).toBeInTheDocument();
      expect(barra()).toHaveAttribute("aria-valuenow", "3");
    });

    it("un error que no es de un campo se muestra sin cambiar de paso", async () => {
      simularApi(async () => {
        throw new ApiError(500, { code: "unknown" });
      });
      const user = userEvent.setup();
      render(<RegisterPage />, { locale: "en" });
      await enviar(user);
      expect(await screen.findByRole("alert")).toBeInTheDocument();
      expect(barra()).toHaveAttribute("aria-valuenow", "3");
    });
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

  it.each([
    ["/profile?tab=1#x", "/profile?tab=1#x"],
    ["//evil.example", "/home"],
    ["/\\evil.example", "/home"],
    ["https://evil.example", "/home"],
  ])("tras el login, next=%s lleva a %s", async (next, esperado) => {
    consulta.texto = `next=${encodeURIComponent(next)}`;
    const user = userEvent.setup();
    render(<LoginPage />, { locale: "en" });
    await user.type(screen.getByLabelText(en.auth.login.identifierLabel), "juan");
    await user.type(
      screen.getByLabelText(en.auth.password.label, { selector: "input" }),
      "Popcorn24!"
    );
    await user.click(screen.getByRole("button", { name: en.nav.account.logIn }));
    await waitFor(() => expect(router.push).toHaveBeenCalledWith(esperado));
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
