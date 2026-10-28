import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import es from "../messages/es/common.json";

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 390, height: 844 },
] as const;

async function prepararIdioma(page: Page, baseURL: string, locale: "en" | "es") {
  await page.context().addCookies([
    { name: "filmai_locale", value: locale, url: baseURL },
    { name: "csrftoken", value: "test", url: baseURL },
  ]);
  await page.route("**/api/profile/", (route) =>
    route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
  );
  await page.route("**/api/auth/username-available/**", (route) =>
    route.fulfill({ json: { disponible: true } })
  );
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

for (const viewport of viewports) {
  test.describe(`acceso en ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("landing: CTA, selector de idioma y términos", async ({ page, baseURL }) => {
      await prepararIdioma(page, baseURL!, "en");
      await page.goto("/");
      await expect(page.getByRole("heading", { name: "FilmAI", level: 1 })).toBeVisible();
      await expect(page.getByText(en.auth.landing.description)).toBeVisible();
      await expect(page.getByRole("link", { name: en.auth.landing.explore })).toBeVisible();
      await expect(page.getByRole("link", { name: en.nav.account.signUp })).toHaveAttribute(
        "href",
        "/register"
      );
      await expect(page.getByRole("link", { name: en.nav.account.logIn })).toHaveAttribute(
        "href",
        "/login"
      );
      await expect(page.getByRole("link", { name: en.nav.main.terms })).toHaveAttribute(
        "href",
        "/terms"
      );
      await page.getByRole("radio", { name: "Español" }).click();
      await expect(page.locator("html")).toHaveAttribute("lang", "es");
      await expect(page.getByText(es.auth.landing.description)).toBeVisible();
      await sinDesborde(page);
    });

    test("login: credenciales incorrectas y recuperación de contraseña", async ({
      page,
      baseURL,
    }) => {
      await prepararIdioma(page, baseURL!, "en");
      await page.route("**/api/auth/login/", (route) =>
        route.fulfill({
          status: 400,
          json: { code: "invalid_credentials", params: {}, errors: [] },
        })
      );
      await page.route("**/api/auth/password/reset/", (route) =>
        route.fulfill({ json: { code: "password_reset_requested" } })
      );
      await page.goto("/login");
      await expect(
        page.getByRole("heading", { name: en.nav.account.logIn, level: 1 })
      ).toBeVisible();
      await page.getByLabel(en.auth.login.identifierLabel).fill("juanperez");
      await page.locator('[name="password"]').fill("incorrecta");
      await page.getByRole("button", { name: en.nav.account.logIn, exact: true }).click();
      await expect(
        page.getByRole("alert").filter({ hasText: en.auth.login.invalidCredentials })
      ).toBeVisible();

      await page.getByRole("button", { name: en.auth.password.forgot }).click();
      const dialog = page.getByRole("dialog", { name: en.auth.passwordReset.title });
      await expect(dialog).toBeVisible();
      await dialog.getByLabel(en.common.fields.email).fill("juan@example.com");
      await dialog.getByRole("button", { name: en.common.passwordReset.sendLink }).click();
      await expect(dialog).toContainText("juan@example.com");
      await dialog.getByRole("button", { name: en.common.passwordReset.backToLogin }).click();
      await expect(dialog).toBeHidden();
      await sinDesborde(page);
    });

    test("registro: términos obligatorios, reglas y confirmación", async ({ page, baseURL }) => {
      await prepararIdioma(page, baseURL!, "en");
      let payload: Record<string, unknown> | null = null;
      await page.route("**/api/auth/registration/", async (route) => {
        payload = route.request().postDataJSON();
        await route.fulfill({ status: 201, json: { code: "registration_pending_confirmation" } });
      });
      await page.goto("/register");
      await expect(
        page.getByRole("heading", { name: en.nav.account.signUp, level: 1 })
      ).toBeVisible();
      await page.locator('[name="nombre"]').fill("Juan");
      await page.locator('[name="apellido"]').fill("Pérez");
      await page.locator('[name="nombre_usuario"]').fill("juanperez");
      await expect(page.getByText(en.auth.signUp.usernameAvailable)).toBeVisible();
      // Arranca vacío, aunque el navegador tenga región.
      await expect(page.locator('select[name="pais"]')).toHaveValue("");
      await page.locator('select[name="pais"]').selectOption("AR");
      await page.locator('[name="correo"]').fill("juan@example.com");
      await page.locator('[name="fecha_nacimiento"]').fill("1992-04-10");
      await page.locator('select[name="genero"]').selectOption("masculino");
      await page.locator('[name="password1"]').fill("Popcorn24");
      await expect(page.getByText(en.auth.password.symbolRule).locator("..")).toContainText(
        en.auth.password.ruleMissingLabel
      );
      await page.locator('[name="password1"]').fill("Popcorn24!");
      await page.locator('[name="password2"]').fill("Popcorn24!");

      // Sin aceptar los términos el botón sigue deshabilitado.
      const submit = page.getByRole("button", { name: en.nav.account.signUp, exact: true });
      await expect(submit).toBeDisabled();
      expect(payload).toBeNull();

      await page.locator('[name="acepta_terminos"]').check();
      await expect(submit).toBeEnabled();
      await submit.click();
      await expect(
        page.getByRole("heading", { name: en.auth.confirmation.inboxTitle })
      ).toBeVisible();
      expect(payload).toMatchObject({
        correo: "juan@example.com",
        pais: "AR",
        acepta_terminos: true,
      });
      await expect(page.getByText(/Request another in 1:0\d/)).toBeVisible();
      await expect(page.getByRole("button", { name: en.common.email.resendLink })).toHaveAttribute(
        "aria-disabled",
        "true"
      );
      await sinDesborde(page);
    });

    test("registro: un nombre reservado avisa al escribirlo", async ({ page, baseURL }) => {
      await prepararIdioma(page, baseURL!, "en");
      // Se registra después que la de `prepararIdioma`, así que gana (issue #137).
      await page.route("**/api/auth/username-available/**", (route) =>
        route.fulfill({ json: { disponible: false, motivo: "reservado" } })
      );
      await page.goto("/register");
      await page.locator('[name="nombre_usuario"]').fill("Adm1n");

      await expect(page.getByText(en.errors.codes.username_not_allowed)).toBeVisible();
      await expect(page.getByText(en.errors.codes.username_already_used)).toHaveCount(0);
    });

    test("registro: el enlace de términos abre /terms en otra pestaña", async ({
      page,
      baseURL,
    }) => {
      await prepararIdioma(page, baseURL!, "es");
      await page.goto("/register");
      const [popup] = await Promise.all([
        page.context().waitForEvent("page"),
        page.getByRole("link", { name: /Términos y condiciones/ }).click(),
      ]);
      await expect(popup).toHaveURL(/\/terms$/);
      await expect(
        popup.getByRole("heading", { name: "Términos y Condiciones", level: 1 })
      ).toBeVisible();
      await expect(popup.locator("main section")).toHaveCount(12);
    });

    test("confirmación: cuenta confirmada y enlace vencido con reenvío", async ({
      page,
      baseURL,
    }) => {
      await prepararIdioma(page, baseURL!, "en");
      await page.route("**/api/auth/registration/verify-email/", async (route) => {
        const key = route.request().postDataJSON().key;
        await route.fulfill(
          key === "buena"
            ? { json: { code: "email_confirmed" } }
            : { status: 400, json: { code: "link_expired", params: {}, errors: [] } }
        );
      });
      await page.route("**/api/auth/registration/resend-email/", (route) =>
        route.fulfill({ json: { code: "confirmation_email_sent" } })
      );
      await page.goto("/confirm-email/buena");
      await expect(
        page.getByRole("heading", { name: en.auth.confirmation.successTitle })
      ).toBeVisible();
      await expect(page.getByRole("link", { name: en.nav.account.logIn })).toHaveAttribute(
        "href",
        "/login"
      );

      await page.goto("/confirm-email/vencida");
      await expect(
        page.getByRole("heading", { name: en.auth.confirmation.invalidTitle })
      ).toBeVisible();
      await page.getByRole("button", { name: en.common.email.resendLink }).click();
      await page.getByLabel(en.common.fields.email).fill("juan@example.com");
      await page.getByRole("button", { name: en.common.email.resendLink }).click();
      await expect(
        page.getByRole("heading", { name: en.auth.confirmation.inboxTitle })
      ).toBeVisible();
      await sinDesborde(page);
    });
  });
}

test("terminos: se sirve en el idioma elegido y sin sesión", async ({ page, baseURL }) => {
  await prepararIdioma(page, baseURL!, "en");
  await page.goto("/terms");
  await expect(page.getByRole("heading", { name: "Terms and Conditions", level: 1 })).toBeVisible();
  await expect(page.locator("main section")).toHaveCount(12);
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("terminos en celular: índice plegable y regreso a la portada", async ({ page, baseURL }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await prepararIdioma(page, baseURL!, "en");
  await page.route("**/api/profile/", (route) =>
    route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
  );
  await page.goto("/terms");
  await expect(page.getByRole("link", { name: en.nav.main.backLanding })).toBeVisible();
  const index = page.locator("details");
  await expect(index).not.toHaveAttribute("open", "");
  await index.locator("summary").click();
  await index.getByRole("link", { name: /Your account/ }).click();
  await expect(page).toHaveURL(/#s-3$/);
  await sinDesborde(page);
});
