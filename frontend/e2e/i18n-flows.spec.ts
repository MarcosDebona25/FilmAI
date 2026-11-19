import { expect, test } from "@playwright/test";
import en from "../messages/en/common.json";
import es from "../messages/es/common.json";
import { prepararCuenta } from "./cuenta";

for (const locale of ["en", "es"] as const) {
  const messages = locale === "en" ? en : es;
  test(`registro, confirmación, login, idioma y restablecimiento en ${locale}`, async ({
    page,
    baseURL,
  }) => {
    test.setTimeout(60_000);
    await page.context().addCookies([
      { name: "filmai_locale", value: locale, url: baseURL! },
      { name: "csrftoken", value: "test", url: baseURL! },
    ]);
    await page.route("**/api/auth/username-available/**", (route) =>
      route.fulfill({ json: { disponible: true } })
    );
    await page.route("**/api/auth/registration/", async (route) => {
      expect(route.request().headers()["accept-language"]).toBe(locale);
      expect(route.request().postDataJSON().acepta_terminos).toBe(true);
      // Lo tipeado sale en el orden del idioma; al backend llega siempre ISO.
      expect(route.request().postDataJSON().fecha_nacimiento).toBe("1990-01-15");
      await route.fulfill({ status: 201, json: { code: "registration_pending_confirmation" } });
    });
    await page.goto("/register");
    // El registro va en tres pasos; el botón principal se habilita cuando React
    // ya tomó la página, así que lo escrito después no se pierde.
    const continuar = page.getByRole("button", {
      name: messages.auth.signUp.continue,
      exact: true,
    });
    await expect(continuar).toBeEnabled({ timeout: 30_000 });
    await page.locator('[name="correo"]').fill("ana@example.com");
    await page.locator('[name="password1"]').fill("Password123*");
    await page.locator('[name="password2"]').fill("Password123*");
    await continuar.click();
    await page.locator('[name="nombre"]').fill("Ana");
    await page.locator('[name="apellido"]').fill("Pérez");
    await page.locator('[name="nombre_usuario"]').fill("anaperez");
    await expect(
      page.getByText(messages.auth.signUp.usernameAvailable, { exact: true })
    ).toBeAttached();
    // Lo tipeado sale en el orden del idioma; al backend llega siempre ISO.
    await page
      .locator('[name="fecha_nacimiento"]')
      .fill(locale === "es" ? "15/01/1990" : "01/15/1990");
    await page.locator('select[name="genero"]').selectOption("no_especifica");
    await page.getByRole("combobox", { name: messages.common.fields.country }).click();
    await page.getByRole("option", { name: /^(Brasil|Brazil)$/ }).click();
    await continuar.click();
    await page.locator('[name="acepta_terminos"]').check();
    await page.getByRole("button", { name: messages.auth.signUp.createAccount }).click();
    await expect(
      page.getByRole("heading", { name: messages.auth.confirmation.inboxTitle })
    ).toBeVisible();
    await page.route("**/api/auth/registration/verify-email/", (route) =>
      route.fulfill({ json: { code: "email_confirmed" } })
    );
    await page.goto("/confirm-email/test-key");
    await expect(
      page.getByRole("heading", { name: messages.auth.confirmation.successTitle })
    ).toBeVisible();
    await page.getByRole("link", { name: messages.nav.account.logIn }).click();
    const account = await prepararCuenta(page, locale);
    await page.route("**/api/auth/login/", async (route) => {
      expect(route.request().headers()["accept-language"]).toBe(locale);
      await route.fulfill({ json: { user: { nombre_usuario: "anaperez" } } });
    });
    await page.locator('[name="username"]').fill("anaperez");
    await page.locator('[name="password"]').fill("Password123*");
    await page.getByRole("button", { name: messages.nav.account.logIn, exact: true }).click();
    await expect(page).toHaveURL(baseURL! + "/home");
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await page.goto("/settings");
    await expect(
      page.getByRole("heading", { name: messages.nav.main.settings, exact: true })
    ).toBeVisible();
    const next = locale === "en" ? "es" : "en";
    const nextMessages = next === "en" ? en : es;
    // Un clic antes de hidratar no hace nada: se repite hasta ver el cambio.
    await expect(async () => {
      await page.getByRole("radio", { name: next === "en" ? "English" : "Español" }).click();
      await expect(page.locator("html")).toHaveAttribute("lang", next, { timeout: 2_000 });
    }).toPass({ timeout: 15_000 });
    await expect(
      page.getByRole("heading", { name: nextMessages.nav.main.settings, exact: true })
    ).toBeVisible();
    expect(account.getPreferencias().idioma).toBe(next);
    expect(
      (await page.context().cookies()).find((cookie) => cookie.name === "filmai_locale")?.value
    ).toBe(next);
    await page.reload();
    await expect(
      page.getByRole("radio", { name: next === "en" ? "English" : "Español" })
    ).toBeChecked();
    await page.route("**/api/auth/password/reset/confirm/", async (route) => {
      expect(route.request().headers()["accept-language"]).toBe(next);
      await route.fulfill({ json: { code: "password_reset_completed" } });
    });
    await page.goto("/reset-password/uid/token");
    await page
      .getByLabel(nextMessages.common.password.newLabel, { exact: true })
      .fill("Password123*");
    await page
      .getByLabel(nextMessages.common.fields.passwordConfirm, { exact: true })
      .fill("Password123*");
    await page
      .getByRole("button", { name: nextMessages.auth.newPassword.save, exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: nextMessages.auth.newPassword.successTitle })
    ).toBeVisible();
  });
  test(`destinos de correo recuperan errores tipados en ${locale}`, async ({ page, baseURL }) => {
    await page.context().addCookies([
      { name: "filmai_locale", value: locale, url: baseURL! },
      { name: "csrftoken", value: "test", url: baseURL! },
    ]);
    await page.route("**/api/profile/", (route) =>
      route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
    );
    await page.route("**/api/auth/registration/verify-email/", (route) =>
      route.fulfill({ status: 400, json: { code: "link_expired", params: {}, errors: [] } })
    );
    await page.goto("/confirm-email/expired");
    await expect(
      page.getByRole("heading", { name: messages.auth.confirmation.invalidTitle })
    ).toBeVisible();
    await page.route("**/api/auth/password/reset/confirm/", (route) =>
      route.fulfill({ status: 400, json: { code: "link_invalid", params: {}, errors: [] } })
    );
    await page.goto("/reset-password/uid/invalid");
    await page.getByLabel(messages.common.password.newLabel, { exact: true }).fill("Password123!");
    await page
      .getByLabel(messages.common.fields.passwordConfirm, { exact: true })
      .fill("Password123!");
    await page.getByRole("button", { name: messages.auth.newPassword.save, exact: true }).click();
    await expect(
      page.getByRole("heading", { name: messages.auth.newPassword.invalidTitle })
    ).toBeVisible();
  });
}

for (const width of [390, 1280]) {
  test(`selector y footer con y sin sesión, teclado y foco a ${width}px`, async ({
    page,
    baseURL,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.context().addCookies([{ name: "filmai_locale", value: "en", url: baseURL! }]);
    await page.route("**/api/profile/", (route) =>
      route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
    );
    await page.goto("/");
    const pill = page.getByRole("radiogroup").first();
    await expect(pill.getByRole("radio", { name: "English" })).toBeChecked();
    // Una tecla antes de hidratar se pierde. Si el idioma ya cambió no se
    // repite: otra flecha lo devolvería a `en`.
    await expect(async () => {
      if ((await page.locator("html").getAttribute("lang")) !== "es") {
        await pill.getByRole("radio", { name: "English" }).focus();
        await page.keyboard.press("ArrowRight");
      }
      await expect(page.locator("html")).toHaveAttribute("lang", "es", { timeout: 2_000 });
    }).toPass({ timeout: 15_000 });
    await expect(pill.getByRole("radio", { name: "Español" })).toBeChecked();
    // La landing ocupa toda la ventana: sin pie. El pie sin sesión vive en /terms.
    await expect(page.locator("footer")).toHaveCount(0);
    await page.goto("/terms");
    await expect(page.locator("footer").getByRole("radio", { name: "Español" })).toBeChecked();
    await prepararCuenta(page, "en");
    await page.goto("/settings");
    await expect(
      page.locator("footer").getByRole("link", { name: /Language: English/ })
    ).toBeVisible();
    await expect(page.locator("footer").getByRole("radio")).toHaveCount(0);
    await expect(page.locator("footer").getByRole("link", { name: "Sign up" })).toHaveCount(0);
    await expect(async () => {
      await page
        .locator("footer")
        .getByRole("link", { name: /Language: English/ })
        .first()
        .click();
      await expect(page).toHaveURL(/\/settings#t-idioma$/, { timeout: 2_000 });
    }).toPass({ timeout: 15_000 });
    await expect(page.locator("#t-idioma")).toBeInViewport();
    await page.screenshot({ path: `/tmp/filmai-settings-${width}.png`, fullPage: true });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    ).toBe(true);
  });
}

test("fallo de guardado deja cuenta y cookie intactas", async ({ page }) => {
  await prepararCuenta(page, "es");
  await page.goto("/settings");
  await expect(page.getByRole("main").getByRole("radio", { name: "Español" })).toBeChecked();
  await page.route("**/api/preferences/", (route) =>
    route.request().method() === "PUT"
      ? route.fulfill({ status: 500, json: { code: "server_error", params: {}, errors: [] } })
      : route.fallback()
  );
  await expect(async () => {
    await page.getByRole("main").getByRole("radio", { name: "English" }).click();
    await expect(page.getByRole("main").getByRole("alert")).toContainText(
      es.settings.language.saveError,
      { timeout: 2_000 }
    );
  }).toPass({ timeout: 15_000 });
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
  await expect(page.getByRole("radio", { name: "Español" })).toBeChecked();
});
