import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";
import { ApiError, apiFetch } from "@/lib/api";
import { elegirPais } from "./elegir-pais";
import { render, screen, waitFor, within } from "./render";

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
type Copia = typeof en | typeof es;

const MARCA = "google_signup_pending";
// Catálogo público de avatares que la página pide al montarse (GET /api/avatars/).
const catalogoAvatares = [
  { id: 1, src: "/uno.png" },
  { id: 2, src: "/dos.png" },
  { id: 3, src: "/tres.png" },
];

/** Simula la API por ruta: el catálogo responde siempre y el alta lo decide cada test. */
function simularApi(
  alta: () => Promise<unknown> = async () => ({ user: { nombre_usuario: "juanperez" } }),
  avatares: unknown[] = catalogoAvatares
) {
  vi.mocked(apiFetch).mockImplementation(async (path) =>
    path === "/api/avatars/" ? avatares : alta()
  );
}

function rechazo(errores: { field: string | null; code: string }[]) {
  return async () => {
    throw new ApiError(400, {
      code: "validation_error",
      params: {},
      errors: errores.map((error) => ({ ...error, params: {} })),
    });
  };
}

/** Cuerpo que la página mandó a `/api/auth/google/`. */
function cuerpoDelAlta() {
  const llamada = vi.mocked(apiFetch).mock.calls.find(([ruta]) => ruta === "/api/auth/google/");
  return (llamada?.[1] as { body: Record<string, unknown> }).body;
}

beforeEach(() => {
  sessionStorage.setItem(MARCA, "register");
  simularApi();
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

function barra(copy: Copia = en) {
  return screen.getByRole("progressbar", { name: copy.auth.signUp.progressLabel });
}

function continuar(copy: Copia = en) {
  return screen.getByRole("button", { name: copy.auth.signUp.continue });
}

function atras(copy: Copia = en) {
  return screen.getByRole("button", { name: new RegExp(`^${copy.auth.signUp.back}`) });
}

function celda(paso: 2 | 3) {
  return document.querySelector<HTMLElement>(`[data-paso="${paso}"]`)!;
}

/** El aviso del servidor: la región `role="alert"` que está siempre en el paso 2. */
function aviso() {
  return document.querySelector<HTMLElement>("[data-aviso-servidor]")!;
}

/** Los campos del paso 2, sin esperar el resultado de la consulta del usuario. */
async function llenarCamposPaso2(user: Usuario, copy: Copia = en) {
  await user.type(screen.getByLabelText(copy.common.fields.username), "juanperez");
  // El orden sigue al idioma de la app: 10 de abril de 1992 en los dos casos.
  await user.type(
    screen.getByLabelText(copy.common.fields.birthDate),
    copy === es ? "10/04/1992" : "04/10/1992"
  );
  await user.selectOptions(screen.getByLabelText(copy.auth.signUp.genderLabel), "masculino");
  await elegirPais(user, screen.getByLabelText(copy.common.fields.country), "Argentina");
}

async function llenarPaso2(user: Usuario, copy: Copia = en) {
  await llenarCamposPaso2(user, copy);
  await screen.findByText(copy.auth.signUp.usernameAvailable);
}

/**
 * Deja la consulta de disponibilidad sin responder (el estado queda en
 * «checking») y devuelve la función que la responde cuando el test lo decide.
 */
function consultaEnEspera() {
  let responder!: (disponible: boolean) => void;
  const respuesta = new Promise((resolve) => {
    responder = (disponible) => resolve({ ok: true, json: async () => ({ disponible }) });
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(() => respuesta)
  );
  return responder;
}

async function irAlPaso3(user: Usuario, copy: Copia = en) {
  await llenarPaso2(user, copy);
  await user.click(continuar(copy));
  expect(barra(copy)).toHaveAttribute("aria-valuenow", "3");
}

/** Recorre los dos pasos, acepta los Términos y toca el botón de Google. */
async function confirmar(user: Usuario, copy: Copia = en) {
  await irAlPaso3(user, copy);
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: "google" }));
}

describe("alta con Google en los pasos 2 y 3", () => {
  // Los dos idiomas: la estructura es la del registro con correo, con la línea
  // de Google en lugar del subtítulo.
  it.each([
    ["en", en],
    ["es", es],
  ] as const)("llega en el paso 2 de 3 con la copia del canvas (%s)", (locale, copy) => {
    render(<CompletarGooglePage />, { locale });

    expect(
      screen.getByRole("heading", { level: 1, name: copy.auth.signUp.title })
    ).toBeInTheDocument();
    expect(screen.getByText(copy.auth.completeSignUp.googleLine)).toBeInTheDocument();
    expect(barra(copy)).toHaveAttribute("aria-valuemin", "0");
    expect(barra(copy)).toHaveAttribute("aria-valuemax", "3");
    expect(barra(copy)).toHaveAttribute("aria-valuenow", "2");
    expect(barra(copy)).toHaveAttribute(
      "aria-valuetext",
      copy.auth.signUp.stepOf.replace("{step}", "2").replace("{total}", "3")
    );
    expect(continuar(copy)).toBeInTheDocument();
    // «Back» está a la vista desde el paso 2 (el paso 1 fue Google) y la fila
    // no ofrece «Log in»: una cuenta de Google que ya existe no llega acá.
    expect(atras(copy)).toHaveAccessibleName(copy.auth.completeSignUp.backToSignUp);
    expect(screen.queryByRole("link", { name: copy.nav.account.logIn })).toBeNull();
  });

  it("los dos pasos están siempre montados; el no activo queda inerte y oculto", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    expect(celda(2)).not.toHaveAttribute("inert");
    expect(celda(2)).not.toHaveAttribute("aria-hidden");
    expect(celda(3)).toHaveAttribute("inert");
    expect(celda(3)).toHaveAttribute("aria-hidden", "true");

    await irAlPaso3(user);

    expect(celda(2)).toHaveAttribute("inert");
    expect(celda(2)).toHaveAttribute("aria-hidden", "true");
    expect(celda(3)).not.toHaveAttribute("inert");
    expect(celda(3)).not.toHaveAttribute("aria-hidden");
  });

  it("recorrer los campos no muestra errores", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await user.click(screen.getByLabelText(en.common.fields.username));
    await user.tab();
    await user.tab();
    await user.tab();

    expect(aviso()).toBeEmptyDOMElement();
    expect(within(celda(2)).getAllByRole("alert")).toEqual([aviso()]);
  });

  it("«Continue» con el paso inválido se queda y muestra los errores de sus campos", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await user.click(continuar());

    expect(barra()).toHaveAttribute("aria-valuenow", "2");
    for (const campo of [
      en.common.fields.username,
      en.common.fields.birthDate,
      en.auth.signUp.genderLabel,
      en.common.fields.country,
    ]) {
      expect(screen.getByLabelText(campo)).toHaveAttribute("aria-invalid", "true");
    }
    expect(screen.getByText(en.common.country.required)).toBeInTheDocument();
    // El aviso del servidor no es un error de validación del paso.
    expect(aviso()).toBeEmptyDOMElement();
  });

  it("si el username está ocupado, «Continue» no avanza", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => ({ disponible: false }) }))
    );
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await user.type(screen.getByLabelText(en.common.fields.username), "juanperez");
    await user.type(screen.getByLabelText(en.common.fields.birthDate), "04/10/1992");
    await user.selectOptions(screen.getByLabelText(en.auth.signUp.genderLabel), "masculino");
    await elegirPais(user, screen.getByLabelText(en.common.fields.country), "Argentina");
    expect(await screen.findByText(en.errors.codes.username_already_used)).toBeInTheDocument();
    await user.click(continuar());

    expect(barra()).toHaveAttribute("aria-valuenow", "2");
  });

  describe("«Continue» mientras se verifica el usuario", () => {
    /** Paso 2 completo, con la consulta ya enviada y todavía sin respuesta. */
    async function tocarContinuarVerificando(user: Usuario) {
      await llenarCamposPaso2(user);
      await waitFor(() => expect(fetch).toHaveBeenCalled());
      await user.click(continuar());
    }

    it("el clic queda pendiente y avanza cuando el usuario resulta disponible", async () => {
      const responder = consultaEnEspera();
      const user = userEvent.setup();
      render(<CompletarGooglePage />, { locale: "en" });
      await tocarContinuarVerificando(user);
      // Sigue en el paso 2, con el botón en su estado de carga.
      expect(barra()).toHaveAttribute("aria-valuenow", "2");
      expect(continuar()).toHaveAttribute("aria-busy", "true");
      expect(continuar()).toBeDisabled();

      responder(true);
      await waitFor(() => expect(barra()).toHaveAttribute("aria-valuenow", "3"));
      expect(screen.getByRole("button", { name: en.auth.signUp.avatarChoose })).toHaveFocus();
    });

    it("si el usuario resulta en uso se queda en el paso con el error en el campo", async () => {
      const responder = consultaEnEspera();
      const user = userEvent.setup();
      render(<CompletarGooglePage />, { locale: "en" });
      await tocarContinuarVerificando(user);

      responder(false);
      expect(await screen.findByText(en.errors.codes.username_already_used)).toBeInTheDocument();
      expect(barra()).toHaveAttribute("aria-valuenow", "2");
      // El error sale del estado del usuario; el pendiente se limpia en el render siguiente.
      await waitFor(() => expect(continuar()).not.toHaveAttribute("aria-busy"));
      expect(continuar()).toBeEnabled();
    });

    it("editar el usuario cancela el clic pendiente", async () => {
      const responder = consultaEnEspera();
      const user = userEvent.setup();
      render(<CompletarGooglePage />, { locale: "en" });
      await tocarContinuarVerificando(user);

      await user.type(screen.getByLabelText(en.common.fields.username), "2");
      expect(continuar()).not.toHaveAttribute("aria-busy");
      responder(true);
      expect(await screen.findByText(en.auth.signUp.usernameAvailable)).toBeInTheDocument();
      expect(barra()).toHaveAttribute("aria-valuenow", "2");
    });

    it("si la verificación falla con 429 (Too Many Requests) deja avanzar", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => ({ ok: false, status: 429, json: async () => ({}) }))
      );
      const user = userEvent.setup();
      render(<CompletarGooglePage />, { locale: "en" });
      await llenarCamposPaso2(user);
      await waitFor(() => expect(fetch).toHaveBeenCalled());
      await user.click(continuar());
      // El usuario lo valida el backend al enviar el alta.
      await waitFor(() => expect(barra()).toHaveAttribute("aria-valuenow", "3"));
    });
  });

  it("el país arranca vacío, sin elegir por el navegador, y es obligatorio", async () => {
    vi.spyOn(navigator, "language", "get").mockReturnValue("es-AR");
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });
    const pais = screen.getByLabelText(en.common.fields.country);

    expect(pais).toHaveTextContent(en.common.country.placeholder);
    await user.click(pais);
    await user.tab();
    expect(await screen.findByText(en.common.country.required)).toBeInTheDocument();
    expect(pais).toHaveAttribute("aria-invalid", "true");
    await elegirPais(user, pais, "Argentina");
    expect(screen.queryByText(en.common.country.required)).not.toBeInTheDocument();
  });

  it("«Continue» con el paso válido pasa al 3 y enfoca su primer campo; Enter hace lo mismo", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await llenarPaso2(user);
    await user.type(screen.getByLabelText(en.common.fields.username), "{Enter}");

    expect(barra()).toHaveAttribute("aria-valuenow", "3");
    expect(barra()).toHaveAttribute("aria-valuetext", "Step 3 of 3");
    expect(screen.getByRole("button", { name: en.auth.signUp.avatarChoose })).toHaveFocus();
    // En el paso 3 la acción es el botón de Google, no «Continue».
    expect(screen.queryByRole("button", { name: en.auth.signUp.continue })).toBeNull();
    expect(atras()).toHaveAccessibleName(en.auth.signUp.backToStep.replace("{step}", "2"));
  });

  it("sin catálogo de avatares el paso 3 arranca en los Términos", async () => {
    simularApi(undefined, []);
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await irAlPaso3(user);

    expect(screen.queryByRole("button", { name: en.auth.signUp.avatarChoose })).toBeNull();
    expect(screen.getByRole("checkbox")).toHaveFocus();
  });

  it("«Back» en el paso 3 vuelve al 2, conserva lo escrito y enfoca el usuario", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });
    await irAlPaso3(user);
    await user.click(screen.getByRole("checkbox"));

    await user.click(atras());

    expect(barra()).toHaveAttribute("aria-valuenow", "2");
    const usuario = screen.getByLabelText(en.common.fields.username);
    expect(usuario).toHaveValue("juanperez");
    expect(usuario).toHaveFocus();
    expect(screen.getByLabelText(en.auth.signUp.genderLabel)).toHaveValue("masculino");
    expect(sessionStorage.getItem(MARCA)).toBe("register");
    expect(router.push).not.toHaveBeenCalled();
    // Y al volver al 3 los Términos siguen aceptados.
    await user.click(continuar());
    expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it.each([
    ["register", "/register", en.auth.completeSignUp.backToSignUp],
    ["login", "/login", en.auth.completeSignUp.backToLogIn],
    // Marca de una pestaña abierta antes de este cambio: se trata como Log in.
    ["1", "/login", en.auth.completeSignUp.backToLogIn],
  ])(
    "«Back» en el paso 2 descarta el alta y vuelve al origen (%s)",
    async (marca, ruta, nombre) => {
      sessionStorage.setItem(MARCA, marca);
      const user = userEvent.setup();
      render(<CompletarGooglePage />, { locale: "en" });
      await waitFor(() => expect(atras()).toHaveAccessibleName(nombre));

      await user.click(atras());

      expect(sessionStorage.getItem(MARCA)).toBeNull();
      expect(router.push).toHaveBeenCalledWith(ruta);
    }
  );

  it("el botón de Google queda inerte hasta aceptar los Términos", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });
    await irAlPaso3(user);
    const ayuda = screen.getByText(en.auth.completeSignUp.termsPending);

    expect(confirmacion()).toHaveAttribute("inert");
    expect(confirmacion()).toHaveClass("opacity-40");
    expect(ayuda).not.toHaveClass("invisible");

    await user.click(screen.getByRole("checkbox"));

    expect(confirmacion()).not.toHaveAttribute("inert");
    expect(confirmacion()).not.toHaveClass("opacity-40");
    // El renglón sigue en su lugar: solo deja de verse.
    expect(ayuda).toHaveClass("invisible");

    await user.click(screen.getByRole("checkbox"));
    expect(confirmacion()).toHaveAttribute("inert");
  });

  it("confirma con el id_token fresco, manda el avatar elegido y lleva al Home", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });
    await irAlPaso3(user);

    await user.click(screen.getByRole("button", { name: en.auth.signUp.avatarChoose }));
    await user.click(screen.getByRole("radio", { name: "Avatar 3" }));
    await user.click(screen.getByRole("button", { name: en.auth.signUp.avatarUse }));
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "google" }));

    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/home"));
    expect(cuerpoDelAlta()).toEqual({
      id_token: "token-fresco",
      nombre_usuario: "juanperez",
      pais: "AR",
      fecha_nacimiento: "1992-04-10",
      genero: "masculino",
      acepta_terminos: true,
      avatar_id: 3,
    });
    expect(sessionStorage.getItem(MARCA)).toBeNull();
  });

  it("sin catálogo de avatares el alta no manda `avatar_id`", async () => {
    simularApi(undefined, []);
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await confirmar(user);

    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/home"));
    expect(cuerpoDelAlta()).not.toHaveProperty("avatar_id");
  });

  it("la región del aviso existe vacía desde el principio (los lectores la anuncian al llenarse)", () => {
    render(<CompletarGooglePage />, { locale: "en" });

    expect(aviso()).toHaveAttribute("role", "alert");
    expect(aviso()).toBeEmptyDOMElement();
    expect(celda(2)).toContainElement(aviso());
    // El texto que guarda el alto no llega a los lectores de pantalla.
    expect(screen.getByText(en.auth.completeSignUp.fixHighlighted)).toHaveAttribute(
      "aria-hidden",
      "true"
    );
  });

  it("si el servidor rechaza el username vuelve al paso 2 con el aviso y el error en el campo", async () => {
    simularApi(rechazo([{ field: "nombre_usuario", code: "username_already_used" }]));
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "es" });

    await confirmar(user, es);

    await waitFor(() => expect(barra(es)).toHaveAttribute("aria-valuenow", "2"));
    expect(aviso()).toHaveTextContent(es.auth.completeSignUp.fixHighlighted);
    const usuario = screen.getByLabelText(es.common.fields.username);
    expect(screen.getByText(es.errors.codes.username_already_used)).toBeInTheDocument();
    expect(usuario).toHaveAttribute("aria-invalid", "true");
    expect(usuario).toHaveFocus();
    expect(router.push).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(MARCA)).toBe("register");

    // Al corregir el campo, el aviso se vacía (su lugar queda).
    await user.type(usuario, "2");
    expect(aviso()).toBeEmptyDOMElement();
  });

  it("un error de otro campo del paso 2 también vuelve a ese campo", async () => {
    simularApi(rechazo([{ field: "fecha_nacimiento", code: "minimum_age" }]));
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await confirmar(user);

    await waitFor(() => expect(barra()).toHaveAttribute("aria-valuenow", "2"));
    expect(aviso()).toHaveTextContent(en.auth.completeSignUp.fixHighlighted);
    expect(screen.getByLabelText(en.common.fields.birthDate)).toHaveFocus();
  });

  it("un error sin campo se queda en el paso 3, sin el aviso de campos marcados", async () => {
    simularApi(rechazo([{ field: null, code: "email_already_used" }]));
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await confirmar(user);

    const mensaje = await screen.findByText(en.errors.codes.email_already_used);
    expect(celda(3)).toContainElement(mensaje);
    expect(barra()).toHaveAttribute("aria-valuenow", "3");
    expect(aviso()).toBeEmptyDOMElement();
  });

  it.each([
    ["acepta_terminos", "terms_not_accepted"],
    ["avatar_id", "avatar_invalid"],
  ])("un error de %s se queda en el paso 3", async (field, code) => {
    simularApi(rechazo([{ field, code }]));
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await confirmar(user);

    await waitFor(() => expect(within(celda(3)).getAllByRole("alert")).toHaveLength(1));
    expect(barra()).toHaveAttribute("aria-valuenow", "3");
    expect(aviso()).toBeEmptyDOMElement();
  });

  it("un error general del paso 3 no sigue a la vista al volver al paso 2 y avanzar de nuevo", async () => {
    simularApi(rechazo([{ field: null, code: "email_already_used" }]));
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await confirmar(user);
    expect(await screen.findByText(en.errors.codes.email_already_used)).toBeInTheDocument();

    await user.click(atras());
    expect(barra()).toHaveAttribute("aria-valuenow", "2");
    await user.click(continuar());
    expect(barra()).toHaveAttribute("aria-valuenow", "3");
    expect(screen.queryByText(en.errors.codes.email_already_used)).toBeNull();
  });

  it("«Continue» con errores enfoca el primer campo inválido", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await user.click(continuar());
    expect(screen.getByLabelText(en.common.fields.username)).toHaveFocus();

    await user.type(screen.getByLabelText(en.common.fields.username), "juanperez");
    await user.click(continuar());
    expect(barra()).toHaveAttribute("aria-valuenow", "2");
    expect(screen.getByLabelText(en.common.fields.birthDate)).toHaveFocus();
  });

  it("el error del género queda vinculado al <select> con aria-describedby", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });

    await user.click(continuar());
    const genero = screen.getByLabelText(en.auth.signUp.genderLabel);
    expect(genero).toHaveAttribute("aria-invalid", "true");
    expect(genero).toHaveAccessibleDescription(en.errors.codes.required);
  });

  it("anuncia «Step N of 3» en una región viva al cambiar de paso", async () => {
    const user = userEvent.setup();
    render(<CompletarGooglePage />, { locale: "en" });
    const anuncio = screen.getByText("Step 2 of 3");
    expect(anuncio).toHaveAttribute("aria-live", "polite");

    await irAlPaso3(user);
    expect(anuncio).toHaveTextContent("Step 3 of 3");
  });

  // El aviso aparece en el paso 2, donde el botón de Google no está.
  it.each([
    ["en", en, /step 3/],
    ["es", es, /paso 3/],
  ] as const)(
    "el aviso de campos marcados manda al paso 3, no a un botón (%s)",
    (_, copy, paso) => {
      expect(copy.auth.completeSignUp.fixHighlighted).toMatch(paso);
      expect(copy.auth.completeSignUp.fixHighlighted).not.toMatch(/button|botón/i);
    }
  );

  it("sin un alta con Google pendiente redirige al login", () => {
    sessionStorage.clear();
    render(<CompletarGooglePage />, { locale: "en" });

    expect(router.replace).toHaveBeenCalledWith("/login");
  });
});
