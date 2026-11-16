import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import es from "../messages/es/common.json";
import { auditar } from "./axe";

// Registro en tres pasos (canvas, sección 16). La API está simulada: ningún
// test crea una cuenta real ni manda correos.

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 375, height: 812 },
] as const;

type Copia = typeof en | typeof es;

async function preparar(page: Page, baseURL: string, locale: "en" | "es") {
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
  // Catálogo público de avatares: el registro lo pide al abrirse.
  await page.route("**/api/avatars/", (route) =>
    route.fulfill({
      json: Array.from({ length: 26 }, (_, i) => ({
        id: i + 1,
        src: `/avatars/recortados/avatar%20(${i + 1}).png`,
      })),
    })
  );
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

function barra(page: Page, copy: Copia) {
  return page.getByRole("progressbar", { name: copy.auth.signUp.progressLabel });
}

function continuar(page: Page, copy: Copia) {
  return page.getByRole("button", { name: copy.auth.signUp.continue, exact: true });
}

/** Abre el registro y espera a que React tome la página (el botón se habilita). */
async function abrir(page: Page, copy: Copia) {
  await page.goto("/register");
  await expect(page.getByRole("heading", { name: copy.auth.signUp.title, level: 1 })).toBeVisible();
  await expect(continuar(page, copy)).toBeEnabled({ timeout: 30_000 });
}

async function llenarPaso1(page: Page) {
  await page.locator('[name="correo"]').fill("juan@example.com");
  await page.locator('[name="password1"]').fill("Popcorn24!");
  await page.locator('[name="password2"]').fill("Popcorn24!");
}

async function llenarPaso2(page: Page, copy: Copia) {
  await page.locator('[name="nombre"]').fill("Juan");
  await page.locator('[name="apellido"]').fill("Pérez");
  await page.locator('[name="nombre_usuario"]').fill("juanperez");
  await expect(page.getByText(copy.auth.signUp.usernameAvailable)).toBeAttached();
  // 10 de abril de 1992, en el orden del idioma de la app.
  await page.locator('[name="fecha_nacimiento"]').fill(copy === es ? "10/04/1992" : "04/10/1992");
  await page.locator('select[name="genero"]').selectOption("masculino");
  await page.getByRole("combobox", { name: copy.common.fields.country }).click();
  await page.getByRole("option", { name: "Argentina", exact: true }).click();
  await expect(page.locator('input[name="pais"]')).toHaveValue("AR");
}

async function irAlPaso2(page: Page, copy: Copia) {
  await abrir(page, copy);
  await llenarPaso1(page);
  await continuar(page, copy).click();
  await expect(barra(page, copy)).toHaveAttribute("aria-valuenow", "2");
}

async function irAlPaso3(page: Page, copy: Copia) {
  await irAlPaso2(page, copy);
  await llenarPaso2(page, copy);
  await continuar(page, copy).click();
  await expect(barra(page, copy)).toHaveAttribute("aria-valuenow", "3");
}

for (const viewport of viewports) {
  test.describe(`registro en pasos en ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("recorre los tres pasos, elige el avatar y crea la cuenta", async ({ page, baseURL }) => {
      test.setTimeout(90_000);
      await preparar(page, baseURL!, "en");
      let payload: Record<string, unknown> | null = null;
      await page.route("**/api/auth/registration/", async (route) => {
        payload = route.request().postDataJSON();
        await route.fulfill({ status: 201, json: { code: "registration_pending_confirmation" } });
      });
      await abrir(page, en);
      const progreso = barra(page, en);
      const atras = page.getByRole("button", { name: /^Back to step/ });

      // Paso 1: barra en 1 de 3 y «Back» oculto (guarda su lugar).
      await expect(progreso).toHaveAttribute("aria-valuenow", "1");
      await expect(progreso).toHaveAttribute("aria-valuetext", "Step 1 of 3");
      await expect(atras).toBeHidden();
      // Un paso inválido no avanza y marca sus campos.
      await continuar(page, en).click();
      await expect(progreso).toHaveAttribute("aria-valuenow", "1");
      await expect(page.locator('[name="correo"]')).toHaveAttribute("aria-invalid", "true");
      await page.locator('[name="correo"]').fill("juan@example.com");
      await page.locator('[name="password1"]').fill("Popcorn24");
      await expect(page.getByText(en.auth.password.symbolRule).locator("..")).toContainText(
        en.auth.password.ruleMissingLabel
      );
      await page.locator('[name="password1"]').fill("Popcorn24!");
      await page.locator('[name="password2"]').fill("Popcorn24!");
      await auditar(page);
      await sinDesborde(page);
      // Enter en un campo hace lo mismo que el botón principal.
      await page.locator('[name="password2"]').press("Enter");

      // Paso 2: el foco cae en el primer campo.
      await expect(progreso).toHaveAttribute("aria-valuetext", "Step 2 of 3");
      await expect(page.locator('[name="nombre"]')).toBeFocused();
      await expect(page.locator('input[name="pais"]')).toHaveValue("");
      // App en inglés con el navegador en es-AR: el formato sigue a la app.
      await expect(page.locator('[name="fecha_nacimiento"]')).toHaveAttribute(
        "placeholder",
        "MM/DD/YYYY"
      );
      await llenarPaso2(page, en);
      await auditar(page);
      await sinDesborde(page);

      // «Back» vuelve un paso y conserva lo escrito, a la ida y a la vuelta.
      await expect(atras).toHaveAccessibleName("Back to step 1");
      await atras.click();
      await expect(progreso).toHaveAttribute("aria-valuenow", "1");
      await expect(page.locator('[name="correo"]')).toBeFocused();
      await expect(page.locator('[name="correo"]')).toHaveValue("juan@example.com");
      await expect(page.locator('[name="password2"]')).toHaveValue("Popcorn24!");
      await continuar(page, en).click();
      await expect(page.locator('[name="nombre_usuario"]')).toHaveValue("juanperez");
      await expect(page.locator('input[name="pais"]')).toHaveValue("AR");
      await continuar(page, en).click();

      // Paso 3: avatar opcional y términos.
      await expect(progreso).toHaveAttribute("aria-valuetext", "Step 3 of 3");
      const elegir = page.getByRole("button", { name: en.auth.signUp.avatarChoose, exact: true });
      await expect(elegir).toBeFocused();
      await auditar(page);
      await elegir.click();
      const dialogo = page.getByRole("dialog", { name: en.auth.signUp.avatarLabel });
      await expect(dialogo).toBeVisible();
      // Páginas de 3 filas: 18 avatares en escritorio y 12 en celular.
      const porPagina = viewport.name === "escritorio" ? 18 : 12;
      const paginas = Math.ceil(26 / porPagina);
      const radios = dialogo.getByRole("radio");
      const anteriores = dialogo.getByRole("button", { name: en.auth.signUp.avatarPrevious });
      const mas = dialogo.getByRole("button", { name: en.auth.signUp.avatarMore });
      await expect(radios).toHaveCount(porPagina);
      await expect(dialogo.getByText(`1 of ${paginas}`)).toBeVisible();
      await expect(anteriores).toHaveAttribute("aria-disabled", "true");
      const avatar = (n: number) =>
        dialogo.getByRole("radio", { name: `Avatar ${n}`, exact: true });
      await expect(avatar(1)).toBeChecked();
      await expect(avatar(1)).toBeFocused();
      await avatar(3).click();
      // Elegir solo marca: el diálogo sigue abierto.
      await expect(avatar(3)).toBeChecked();
      await expect(dialogo).toBeVisible();
      await auditar(page);
      await sinDesborde(page);
      // Esc cierra sin cambios y el foco vuelve a «Choose».
      await page.keyboard.press("Escape");
      await expect(dialogo).toBeHidden();
      await expect(elegir).toBeFocused();
      await elegir.click();
      await expect(avatar(1)).toBeChecked();
      // Un clic en el fondo también cierra sin cambios.
      await page.mouse.click(4, 4);
      await expect(dialogo).toBeHidden();
      await elegir.click();
      await avatar(3).click();
      // Pasar hasta la última página no cambia la elección ni el alto del diálogo.
      const alto = (await dialogo.boundingBox())!.height;
      for (let p = 2; p <= paginas; p++) {
        await mas.click();
        await expect(dialogo.getByText(`${p} of ${paginas}`)).toBeVisible();
      }
      await expect(radios).toHaveCount(26 - porPagina * (paginas - 1));
      await expect(mas).toHaveAttribute("aria-disabled", "true");
      await expect(mas).toBeFocused();
      await expect(dialogo.getByRole("radio", { checked: true })).toHaveCount(0);
      expect((await dialogo.boundingBox())!.height).toBe(alto);
      await auditar(page);
      await sinDesborde(page);
      await anteriores.click();
      if (paginas > 2) await anteriores.click();
      await expect(avatar(3)).toBeChecked();
      // Se elige uno de la última página.
      for (let p = 2; p <= paginas; p++) await mas.click();
      await avatar(26).click();
      await expect(avatar(26)).toBeChecked();
      await dialogo.getByRole("button", { name: en.auth.signUp.avatarUse }).click();
      await expect(dialogo).toBeHidden();
      await expect(elegir).toBeFocused();

      // Sin aceptar los términos no se crea la cuenta.
      const crear = page.getByRole("button", { name: en.auth.signUp.createAccount });
      await crear.click();
      await expect(page.getByText(en.errors.codes.terms_not_accepted)).toBeVisible();
      expect(payload).toBeNull();
      await page.locator('[name="acepta_terminos"]').check();
      await crear.click();
      await expect(
        page.getByRole("heading", { name: en.auth.confirmation.inboxTitle })
      ).toBeVisible();
      expect(payload).toMatchObject({
        correo: "juan@example.com",
        nombre_usuario: "juanperez",
        pais: "AR",
        fecha_nacimiento: "1992-04-10",
        genero: "masculino",
        acepta_terminos: true,
        avatar_id: 26,
      });
      await expect(page.getByText(/Request another in 1:0\d/)).toBeVisible();
      await expect(page.getByRole("button", { name: en.common.email.resendLink })).toHaveAttribute(
        "aria-disabled",
        "true"
      );
      await sinDesborde(page);
    });

    test("si el servidor rechaza el alta, vuelve al paso del campo con error", async ({
      page,
      baseURL,
    }) => {
      await preparar(page, baseURL!, "en");
      await page.route("**/api/auth/registration/", (route) =>
        route.fulfill({
          status: 400,
          json: {
            code: "validation_error",
            params: {},
            errors: [{ field: "nombre_usuario", code: "username_already_used", params: {} }],
          },
        })
      );
      await irAlPaso3(page, en);
      await page.locator('[name="acepta_terminos"]').check();
      await page.getByRole("button", { name: en.auth.signUp.createAccount }).click();

      await expect(barra(page, en)).toHaveAttribute("aria-valuenow", "2");
      const usuario = page.locator('[name="nombre_usuario"]');
      await expect(usuario).toBeFocused();
      await expect(usuario).toHaveAttribute("aria-invalid", "true");
      await expect(page.getByText(en.errors.codes.username_already_used)).toBeVisible();
      await auditar(page);
      await sinDesborde(page);
    });

    test("un nombre reservado avisa al escribirlo", async ({ page, baseURL }) => {
      await preparar(page, baseURL!, "en");
      // Se registra después que la de `preparar`, así que gana (issue #137).
      await page.route("**/api/auth/username-available/**", (route) =>
        route.fulfill({ json: { disponible: false, motivo: "reservado" } })
      );
      await irAlPaso2(page, en);
      await page.locator('[name="nombre_usuario"]').fill("Adm1n");
      await expect(page.getByText(en.errors.codes.username_not_allowed)).toBeVisible();
      await expect(page.getByText(en.errors.codes.username_already_used)).toHaveCount(0);
    });

    for (const locale of ["es", "en"] as const) {
      test(`fecha por teclado y calendario en ${locale}`, async ({ page, baseURL }) => {
        const copy = locale === "es" ? es : en;
        await preparar(page, baseURL!, locale);
        await irAlPaso2(page, copy);
        const campo = page.getByLabel(copy.common.fields.birthDate);
        const abrirCalendario = page.getByRole("button", {
          name: copy.common.fields.openCalendar,
        });
        await expect(campo).toHaveAttribute("placeholder", copy.common.fields.dateInputPlaceholder);
        await abrirCalendario.click();
        const calendario = page.getByRole("dialog");
        await expect(calendario).toBeVisible();
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
        await abrirCalendario.click();
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

    test("el enlace de términos abre /terms en otra pestaña", async ({ page, baseURL }) => {
      await preparar(page, baseURL!, "es");
      await irAlPaso3(page, es);
      const [popup] = await Promise.all([
        page.context().waitForEvent("page"),
        page.getByRole("link", { name: /Términos y condiciones/ }).click(),
      ]);
      await expect(popup).toHaveURL(/\/terms$/);
      await expect(
        popup.getByRole("heading", { name: "Términos y Condiciones", level: 1 })
      ).toBeVisible();
    });
  });
}
