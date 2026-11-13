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
      // Catálogo público de avatares: el registro lo pide al abrirse.
      await page.route("**/api/avatars/", (route) =>
        route.fulfill({
          json: Array.from({ length: 26 }, (_, i) => ({
            id: i + 1,
            src: `/avatars/recortados/avatar%20(${i + 1}).png`,
          })),
        })
      );
      await page.route("**/api/auth/registration/", async (route) => {
        payload = route.request().postDataJSON();
        await route.fulfill({ status: 201, json: { code: "registration_pending_confirmation" } });
      });
      await page.goto("/register");
      await expect(
        page.getByRole("heading", { name: en.nav.account.signUp, level: 1 })
      ).toBeVisible();
      // El título se ve antes de hidratar y lo escrito entonces se pierde: se
      // repone hasta ver «Disponible», que solo llega con la página hidratada.
      const nombres = { nombre: "Juan", apellido: "Pérez", nombre_usuario: "juanperez" };
      await expect(async () => {
        for (const [name, value] of Object.entries(nombres)) {
          const campo = page.locator(`[name="${name}"]`);
          if ((await campo.inputValue()) !== value) await campo.fill(value);
        }
        await expect(page.getByText(en.auth.signUp.usernameAvailable)).toBeVisible({
          timeout: 2_000,
        });
        for (const [name, value] of Object.entries(nombres))
          await expect(page.locator(`[name="${name}"]`)).toHaveValue(value, { timeout: 1_000 });
      }).toPass({ timeout: 20_000 });
      // Arranca vacío, aunque el navegador tenga región.
      await expect(page.locator('input[name="pais"]')).toHaveValue("");
      await page.getByRole("combobox", { name: en.common.fields.country }).click();
      await page.getByRole("option", { name: "Argentina", exact: true }).click();
      await expect(page.locator('input[name="pais"]')).toHaveValue("AR");
      await page.locator('[name="correo"]').fill("juan@example.com");
      // App en inglés con el navegador en es-AR: el formato sigue a la app (MM/DD/YYYY).
      const fecha = page.locator('[name="fecha_nacimiento"]');
      await expect(fecha).toHaveAttribute("placeholder", "MM/DD/YYYY");
      await fecha.fill("04/10/1992");
      await page.locator('select[name="genero"]').selectOption("masculino");
      await page.locator('[name="password1"]').fill("Popcorn24");
      await expect(page.getByText(en.auth.password.symbolRule).locator("..")).toContainText(
        en.auth.password.ruleMissingLabel
      );
      await page.locator('[name="password1"]').fill("Popcorn24!");
      await page.locator('[name="password2"]').fill("Popcorn24!");
      // El avatar 1 viene preseleccionado; se elige el 3 con el teclado (flechas).
      const grupoAvatares = page.getByRole("radiogroup", { name: en.common.avatar.optionsLabel });
      await expect(
        grupoAvatares.getByRole("radio", { name: "Avatar 1", exact: true })
      ).toBeChecked();
      await grupoAvatares.getByRole("radio", { name: "Avatar 1", exact: true }).focus();
      await page.keyboard.press("ArrowRight");
      await page.keyboard.press("ArrowRight");
      await expect(
        grupoAvatares.getByRole("radio", { name: "Avatar 3", exact: true })
      ).toBeChecked();

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
        fecha_nacimiento: "1992-04-10",
        acepta_terminos: true,
        avatar_id: 3,
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
      // Un valor escrito antes de hidratar se pierde: se reescribe hasta que
      // aparezca el aviso, que solo llega con la página ya hidratada.
      const campo = page.locator('[name="nombre_usuario"]');
      await expect(async () => {
        if ((await campo.inputValue()) !== "Adm1n") await campo.fill("Adm1n");
        await expect(page.getByText(en.errors.codes.username_not_allowed)).toBeVisible({
          timeout: 2_000,
        });
      }).toPass({ timeout: 20_000 });
      await expect(page.getByText(en.errors.codes.username_already_used)).toHaveCount(0);
    });

    for (const locale of ["es", "en"] as const) {
      test(`registro: fecha por teclado y calendario en ${locale}`, async ({ page, baseURL }) => {
        const copy = locale === "es" ? es : en;
        await prepararIdioma(page, baseURL!, locale);
        await page.goto("/register");
        const campo = page.getByLabel(copy.common.fields.birthDate);
        const abrir = page.getByRole("button", { name: copy.common.fields.openCalendar });
        await expect(campo).toHaveAttribute("placeholder", copy.common.fields.dateInputPlaceholder);
        // Antes de hidratar el clic se pierde: se reintenta hasta ver el calendario.
        await expect(async () => {
          await abrir.click();
          await expect(page.getByRole("dialog")).toBeVisible({ timeout: 2_000 });
        }).toPass({ timeout: 20_000 });
        const calendario = page.getByRole("dialog");
        // Navegador en es-AR: la semana y los textos siguen al idioma de la app.
        await expect(calendario.locator("th").first()).toHaveAttribute(
          "aria-label",
          locale === "es" ? "lunes" : "Sunday"
        );
        await calendario.getByRole("combobox").nth(1).selectOption("1992");
        await calendario.getByRole("combobox").nth(0).selectOption({ index: 3 });
        await calendario.locator('button[data-day="1992-04-10"]').click();
        await expect(calendario).toBeHidden();
        await expect(campo).toBeFocused();
        await expect(campo).toHaveValue(locale === "es" ? "10/04/1992" : "04/10/1992");
        // Escape cierra y devuelve el foco al campo.
        await abrir.click();
        await expect(calendario).toBeVisible();
        await page.keyboard.press("Escape");
        await expect(calendario).toBeHidden();
        await expect(campo).toBeFocused();
        // 31/02 no existe: error específico, sin esperar a salir del campo.
        await campo.fill(locale === "es" ? "31/02/1992" : "02/31/1992");
        await expect(page.getByText(copy.errors.codes.date_inexistent)).toBeVisible();
        await sinDesborde(page);
      });
    }

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
      await expect(popup.locator("main section:not(#credits)")).toHaveCount(12);
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
  await expect(page.locator("main section:not(#credits)")).toHaveCount(12);
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
