import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import es from "../messages/es/common.json";

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 390, height: 844 },
] as const;

/**
 * Sustituye el SDK de Google (GIS) por uno de prueba: `renderButton` dibuja un
 * botón que entrega un id_token al tocarlo y deja a la vista las opciones con
 * las que se pidió (texto, tema y ancho).
 */
async function prepararAlta(page: Page, baseURL: string, { pendiente = true } = {}) {
  await page.context().addCookies([
    { name: "filmai_locale", value: "en", url: baseURL },
    { name: "csrftoken", value: "test", url: baseURL },
  ]);
  await page.route("**/api/profile/", (route) =>
    route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
  );
  await page.route("**/api/auth/username-available/**", (route) =>
    route.fulfill({ json: { disponible: true } })
  );
  await page.addInitScript((pendiente) => {
    if (pendiente) sessionStorage.setItem("google_signup_pending", "1");
    type Opciones = { text: string; theme: string; width: number };
    let callback: (respuesta: { credential: string }) => void = () => {};
    Object.assign(window, {
      google: {
        accounts: {
          id: {
            initialize: (config: { callback: typeof callback }) => {
              callback = config.callback;
            },
            renderButton: (contenedor: HTMLElement, opciones: Opciones) => {
              const boton = document.createElement("button");
              boton.type = "button";
              boton.textContent = "Google";
              boton.dataset.text = opciones.text;
              boton.dataset.theme = opciones.theme;
              boton.style.width = `${opciones.width}px`;
              boton.onclick = () => callback({ credential: "token-e2e" });
              contenedor.appendChild(boton);
            },
          },
        },
      },
    });
  }, pendiente);
}

async function completar(page: Page, copy: typeof en | typeof es) {
  await page.getByLabel(copy.common.fields.username).fill("juanperez");
  await expect(page.getByText(copy.auth.signUp.usernameAvailable)).toBeVisible();
  await page.getByLabel(copy.common.fields.birthDate).fill("1992-04-10");
  await page.getByLabel(copy.auth.signUp.genderLabel).selectOption("masculino");
  await page.getByRole("checkbox").check();
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

for (const viewport of viewports) {
  test.describe(`alta con Google en ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("completa los datos, confirma con Google y entra al Home", async ({ page, baseURL }) => {
      await prepararAlta(page, baseURL!);
      let cuerpo: unknown = null;
      await page.route("**/api/auth/google/", async (route) => {
        cuerpo = route.request().postDataJSON();
        await route.fulfill({ json: { user: { nombre_usuario: "juanperez" } } });
      });
      // Tras el alta hay sesión: el perfil responde y fija el idioma de la cuenta.
      await page.route("**/api/profile/", (route) =>
        cuerpo
          ? route.fulfill({ json: { nombre_usuario: "juanperez", idioma: "en" } })
          : route.fulfill({
              status: 401,
              json: { code: "not_authenticated", params: {}, errors: [] },
            })
      );
      await page.goto("/complete-signup");

      await expect(
        page.getByRole("heading", { level: 1, name: en.auth.completeSignUp.title })
      ).toBeVisible();
      await expect(page.getByText(en.auth.completeSignUp.badge)).toBeVisible();
      // Un solo logo a la vista: en el formulario (escritorio) o en la franja (celular).
      await expect(page.getByRole("link", { name: en.nav.main.brandLandingLabel })).toBeVisible();
      const confirmar = page.getByTestId("google-confirm");
      await expect(confirmar).toHaveAttribute("inert", "");
      await expect(page.getByText(en.auth.signUp.submitPending)).toBeVisible();
      const google = confirmar.getByRole("button", { name: "Google" });
      await expect(google).toHaveAttribute("data-text", "signup_with");
      await expect(google).toHaveAttribute("data-theme", "outline");
      await sinDesborde(page);

      await completar(page, en);
      await expect(confirmar).not.toHaveAttribute("inert");
      await expect(page.getByText(en.auth.signUp.submitPending)).toBeHidden();
      await google.click();

      await expect(page).toHaveURL(/\/home$/, { timeout: 20_000 });
      expect(cuerpo).toEqual({
        id_token: "token-e2e",
        nombre_usuario: "juanperez",
        fecha_nacimiento: "1992-04-10",
        genero: "masculino",
        acepta_terminos: true,
      });
      expect(await page.evaluate(() => sessionStorage.getItem("google_signup_pending"))).toBeNull();
    });

    test("username en uso: marca el campo y el error sigue al idioma", async ({
      page,
      baseURL,
    }) => {
      await prepararAlta(page, baseURL!);
      await page.route("**/api/auth/google/", (route) =>
        route.fulfill({
          status: 400,
          json: {
            code: "validation_error",
            params: {},
            errors: [{ field: "nombre_usuario", code: "username_already_used", params: {} }],
          },
        })
      );
      await page.goto("/complete-signup");
      await page.getByRole("radio", { name: "Español" }).click();
      await expect(page.locator("html")).toHaveAttribute("lang", "es");
      await expect(
        page.getByRole("heading", { level: 1, name: es.auth.completeSignUp.title })
      ).toBeVisible();

      await completar(page, es);
      await page.getByTestId("google-confirm").getByRole("button", { name: "Google" }).click();

      await expect(
        page.getByRole("alert").filter({ hasText: es.auth.completeSignUp.fixHighlighted })
      ).toBeVisible();
      await expect(page.getByText(es.errors.codes.username_already_used)).toBeVisible();
      await expect(page.getByLabel(es.common.fields.username)).toHaveAttribute(
        "aria-invalid",
        "true"
      );
      await expect(page).toHaveURL(/\/complete-signup$/);

      // El error se guarda como código: al volver a inglés se traduce de nuevo.
      await page.getByRole("radio", { name: "English" }).click();
      await expect(page.locator("html")).toHaveAttribute("lang", "en");
      await expect(page.getByText(en.auth.completeSignUp.fixHighlighted)).toBeVisible();
      await expect(page.getByText(en.errors.codes.username_already_used)).toBeVisible();
      await sinDesborde(page);
    });

    test("cancelar vuelve al login y descarta el alta", async ({ page, baseURL }) => {
      await prepararAlta(page, baseURL!);
      await page.goto("/complete-signup");
      // Con el botón de Google dibujado, la página ya hidrató y no se mueve.
      await expect(page.getByTestId("google-confirm").getByRole("button")).toBeVisible();

      await page.getByRole("link", { name: en.auth.completeSignUp.cancel }).click();

      await expect(page).toHaveURL(/\/login$/, { timeout: 20_000 });
      expect(await page.evaluate(() => sessionStorage.getItem("google_signup_pending"))).toBeNull();
    });
  });
}

test("sin un alta con Google pendiente redirige al login", async ({ page, baseURL }) => {
  await prepararAlta(page, baseURL!, { pendiente: false });
  await page.goto("/complete-signup");

  await expect(page).toHaveURL(/\/login$/, { timeout: 20_000 });
});
