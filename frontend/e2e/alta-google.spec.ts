import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import es from "../messages/es/common.json";
import { auditar } from "./axe";

// Alta con Google en los pasos 2 y 3 (canvas, sección 16). La API y el SDK de
// Google están simulados: ningún test crea una cuenta real ni manda correos.

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 375, height: 812 },
] as const;

type Copia = typeof en | typeof es;

/**
 * Sustituye el SDK de Google (GIS) por uno de prueba: `renderButton` dibuja un
 * botón que entrega un id_token al tocarlo y deja a la vista las opciones con
 * las que se pidió (texto, tema y ancho).
 */
async function prepararAlta(
  page: Page,
  baseURL: string,
  {
    origen = "register",
    locale = "en",
  }: { origen?: "register" | "login" | null; locale?: "en" | "es" } = {}
) {
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
  // Catálogo público de avatares: la página lo pide al abrirse.
  await page.route("**/api/avatars/", (route) =>
    route.fulfill({
      json: Array.from({ length: 26 }, (_, i) => ({
        id: i + 1,
        src: `/avatars/recortados/avatar%20(${i + 1}).png`,
      })),
    })
  );
  await page.addInitScript((origen) => {
    // Solo al entrar a la pantalla: «Back» en el paso 2 borra la marca y la
    // página siguiente no debe volver a ponerla.
    if (origen && location.pathname === "/complete-signup")
      sessionStorage.setItem("google_signup_pending", origen);
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
  }, origen);
}

function barra(page: Page, copy: Copia) {
  return page.getByRole("progressbar", { name: copy.auth.signUp.progressLabel });
}

function continuar(page: Page, copy: Copia) {
  return page.getByRole("button", { name: copy.auth.signUp.continue, exact: true });
}

function atras(page: Page, copy: Copia) {
  return page.locator("form:has([data-paso])").getByText(copy.auth.signUp.back, { exact: true });
}

function googleDe(page: Page) {
  return page.getByTestId("google-confirm").getByRole("button", { name: "Google" });
}

/** Abre el alta y espera a que React tome la página (el botón se habilita). */
async function abrir(page: Page, copy: Copia) {
  await page.goto("/complete-signup");
  await expect(page.getByRole("heading", { name: copy.auth.signUp.title, level: 1 })).toBeVisible();
  await expect(continuar(page, copy)).toBeEnabled({ timeout: 30_000 });
}

async function llenarPaso2(page: Page, copy: Copia, usuario = "juanperez") {
  await page.locator('[name="nombre_usuario"]').fill(usuario);
  await expect(page.getByText(copy.auth.signUp.usernameAvailable)).toBeVisible();
  // 10 de abril de 1992 en el orden del idioma de la app, no del navegador (es-AR).
  const fecha = page.locator('[name="fecha_nacimiento"]');
  await expect(fecha).toHaveAttribute("placeholder", copy.common.fields.dateInputPlaceholder);
  await fecha.fill(copy === es ? "10/04/1992" : "04/10/1992");
  await page.locator('select[name="genero"]').selectOption("masculino");
  await page.getByRole("combobox", { name: copy.common.fields.country }).click();
  await page.getByRole("option", { name: "Argentina", exact: true }).click();
  await expect(page.locator('input[name="pais"]')).toHaveValue("AR");
}

async function irAlPaso3(page: Page, copy: Copia) {
  await llenarPaso2(page, copy);
  await continuar(page, copy).click();
  await expect(barra(page, copy)).toHaveAttribute("aria-valuenow", "3");
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

function rechazo(errores: { field: string | null; code: string }[]) {
  return {
    status: 400,
    json: {
      code: "validation_error",
      params: {},
      errors: errores.map((error) => ({ ...error, params: {} })),
    },
  };
}

for (const viewport of viewports) {
  test.describe(`alta con Google en ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("llega en el paso 2, elige el avatar, confirma con Google y entra al Home", async ({
      page,
      baseURL,
    }) => {
      test.setTimeout(90_000);
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
      await abrir(page, en);
      const progreso = barra(page, en);

      // Paso 2 de 3: la barra se llena desde el 33 % del paso 1 hasta el 67 %.
      await expect(progreso).toHaveAttribute("aria-valuenow", "2");
      await expect(progreso).toHaveAttribute("aria-valuetext", "Step 2 of 3");
      await expect(progreso).toHaveAttribute("aria-valuemax", "3");
      await expect(progreso.locator("span")).toHaveAttribute("style", /width:\s*66\.67%/);
      await expect(page.getByText(en.auth.completeSignUp.googleLine)).toBeVisible();
      await expect(page.getByRole("link", { name: en.nav.main.brandLandingLabel })).toBeVisible();
      // Sin «Log in» en la fila de «Back».
      await expect(
        page.locator("form:has([data-paso])").getByRole("link", { name: en.nav.account.logIn })
      ).toHaveCount(0);
      await expect(
        page.getByRole("button", { name: en.auth.completeSignUp.backToSignUp })
      ).toBeVisible();
      await auditar(page);
      await sinDesborde(page);

      // Un paso inválido no avanza y marca sus campos.
      await continuar(page, en).click();
      await expect(progreso).toHaveAttribute("aria-valuenow", "2");
      await expect(page.locator('[name="nombre_usuario"]')).toHaveAttribute("aria-invalid", "true");
      await llenarPaso2(page, en);
      // Enter en un campo hace lo mismo que el botón principal.
      await page.locator('[name="nombre_usuario"]').press("Enter");

      // Paso 3: foco en «Choose» y el botón de Google inerte hasta los Términos.
      await expect(progreso).toHaveAttribute("aria-valuetext", "Step 3 of 3");
      await expect(progreso.locator("span")).toHaveAttribute("style", /width:\s*100%/);
      await expect(
        page.getByRole("button", { name: en.auth.signUp.avatarChoose, exact: true })
      ).toBeFocused();
      const confirmar = page.getByTestId("google-confirm");
      await expect(confirmar).toHaveAttribute("inert", "");
      await expect(confirmar).toHaveCSS("opacity", "0.4");
      await expect(page.getByText(en.auth.completeSignUp.termsPending)).toBeVisible();
      await expect(googleDe(page)).toHaveAttribute("data-text", "signup_with");
      await expect(googleDe(page)).toHaveAttribute("data-theme", "outline");
      await auditar(page);
      await sinDesborde(page);

      await page.getByRole("button", { name: en.auth.signUp.avatarChoose, exact: true }).click();
      const dialogo = page.getByRole("dialog", { name: en.auth.signUp.avatarLabel });
      await dialogo.getByRole("radio", { name: "Avatar 3" }).click();
      await auditar(page);
      await dialogo.getByRole("button", { name: en.auth.signUp.avatarUse }).click();
      await expect(dialogo).toBeHidden();

      await page.getByRole("checkbox").check();
      await expect(confirmar).not.toHaveAttribute("inert");
      await expect(confirmar).toHaveCSS("opacity", "1");
      await expect(page.getByText(en.auth.completeSignUp.termsPending)).toBeHidden();
      await googleDe(page).click();

      await expect(page).toHaveURL(/\/home$/, { timeout: 20_000 });
      expect(cuerpo).toEqual({
        id_token: "token-e2e",
        nombre_usuario: "juanperez",
        pais: "AR",
        fecha_nacimiento: "1992-04-10",
        genero: "masculino",
        acepta_terminos: true,
        avatar_id: 3,
      });
      expect(await page.evaluate(() => sessionStorage.getItem("google_signup_pending"))).toBeNull();
    });

    for (const locale of ["en", "es"] as const) {
      test(`nada salta entre pasos, con errores, con el aviso del servidor ni con el diálogo en ${locale}`, async ({
        page,
        baseURL,
      }, testInfo) => {
        test.setTimeout(120_000);
        const copy = locale === "es" ? es : en;
        await prepararAlta(page, baseURL!, { locale });
        // Primero el username quedó tomado; después, un error sin campo.
        let intentos = 0;
        await page.route("**/api/auth/google/", (route) =>
          route.fulfill(
            rechazo([
              intentos++ === 0
                ? { field: "nombre_usuario", code: "username_already_used" }
                : { field: null, code: "email_already_used" },
            ])
          )
        );
        await abrir(page, copy);
        /** Posición dentro del documento (no de la ventana: el foco puede desplazarla). */
        const medir = () =>
          page.evaluate(() => {
            const caja = (selector: string) => {
              const r = document.querySelector(selector)!.getBoundingClientRect();
              return { x: r.left + window.scrollX, y: r.top + window.scrollY, alto: r.height };
            };
            return {
              // «Continue» en el paso 2 y la fila de 52 px del botón de Google en el 3.
              boton: caja("form:has([data-paso]) [data-accion]"),
              fila: caja("form:has([data-paso]) [data-accion] + div > button"),
              alto: document.documentElement.scrollHeight,
            };
          });
        const base = await medir();
        const medidas: Record<string, number[]> = {};
        const igual = async (momento: string) => {
          const ahora = await medir();
          medidas[momento] = [ahora.boton.y, ahora.fila.y];
          for (const parte of ["boton", "fila"] as const) {
            expect(
              Math.abs(ahora[parte].y - base[parte].y),
              `${momento}: ${parte} (y)`
            ).toBeLessThanOrEqual(1);
            expect(
              Math.abs(ahora[parte].x - base[parte].x),
              `${momento}: ${parte} (x)`
            ).toBeLessThanOrEqual(1);
          }
          expect(ahora.boton.alto, `${momento}: alto de la acción`).toBe(52);
          expect(
            Math.abs(ahora.alto - base.alto),
            `${momento}: alto de la página`
          ).toBeLessThanOrEqual(1);
        };
        medidas["paso 2"] = [base.boton.y, base.fila.y];
        const paso2 = page.locator('[data-paso="2"]');
        const aviso = page.locator("[data-aviso-servidor]");
        // La región del aviso ya está en la página, vacía.
        await expect(aviso).toHaveAttribute("role", "alert");
        await expect(aviso).toBeEmpty();

        // Paso 2 con errores de validación.
        await continuar(page, copy).click();
        await expect(paso2.locator("[aria-invalid='true']")).toHaveCount(4);
        await igual("paso 2 con errores");
        await auditar(page);
        await llenarPaso2(page, copy);
        await igual("paso 2 completo");
        await continuar(page, copy).click();
        await expect(barra(page, copy)).toHaveAttribute("aria-valuenow", "3");
        await igual("paso 3");

        // El diálogo de avatar no mueve la página al abrir, paginar ni cerrar.
        await page
          .getByRole("button", { name: copy.auth.signUp.avatarChoose, exact: true })
          .click();
        const dialogo = page.getByRole("dialog", { name: copy.auth.signUp.avatarLabel });
        await expect(dialogo).toBeVisible();
        await igual("diálogo abierto");
        await dialogo.getByRole("button", { name: copy.auth.signUp.avatarMore }).click();
        await igual("diálogo en la página 2");
        await page.keyboard.press("Escape");
        await expect(dialogo).toBeHidden();
        await igual("diálogo cerrado");

        // Aceptar los Términos esconde la ayuda sin mover nada.
        await page.getByRole("checkbox").check();
        await expect(page.getByText(copy.auth.completeSignUp.termsPending)).toBeHidden();
        await igual("paso 3 con los Términos");

        // El servidor rechaza el username: vuelve al paso 2 con el aviso, el
        // error en el campo y el foco en él.
        await googleDe(page).click();
        await expect(barra(page, copy)).toHaveAttribute("aria-valuenow", "2");
        await expect(aviso).toHaveText(copy.auth.completeSignUp.fixHighlighted);
        await expect(aviso).toBeVisible();
        await expect(paso2.getByText(copy.errors.codes.username_already_used)).toBeVisible();
        await expect(page.locator('[name="nombre_usuario"]')).toBeFocused();
        await igual("paso 2 con el aviso del servidor");
        await auditar(page);
        await sinDesborde(page);

        // Al corregir el campo el aviso se vacía y su lugar queda.
        await page.locator('[name="nombre_usuario"]').fill("juanperez2");
        await expect(aviso).toBeEmpty();
        await expect(page.getByText(copy.auth.signUp.usernameAvailable)).toBeVisible();
        await igual("paso 2 corregido");
        await continuar(page, copy).click();
        await expect(barra(page, copy)).toHaveAttribute("aria-valuenow", "3");

        // Un error sin campo se queda en el paso 3, en su renglón.
        await googleDe(page).click();
        await expect(
          page.locator('[data-paso="3"]').getByText(copy.errors.codes.email_already_used)
        ).toBeVisible();
        await expect(barra(page, copy)).toHaveAttribute("aria-valuenow", "3");
        await igual("paso 3 con un error general");
        await auditar(page);

        // «Back» vuelve al paso 2 y conserva lo escrito.
        await atras(page, copy).click();
        await expect(barra(page, copy)).toHaveAttribute("aria-valuenow", "2");
        await expect(page.locator('[name="nombre_usuario"]')).toHaveValue("juanperez2");
        await expect(page.locator('[name="nombre_usuario"]')).toBeFocused();
        await igual("vuelta al paso 2");
        await sinDesborde(page);
        await testInfo.attach("posiciones", {
          body: JSON.stringify(medidas),
          contentType: "application/json",
        });
      });
    }

    test("el error del servidor se guarda como código y sigue al idioma", async ({
      page,
      baseURL,
    }) => {
      await prepararAlta(page, baseURL!);
      await page.route("**/api/auth/google/", (route) =>
        route.fulfill(rechazo([{ field: "nombre_usuario", code: "username_already_used" }]))
      );
      await abrir(page, en);
      await page.getByRole("radio", { name: "Español" }).click();
      await expect(page.locator("html")).toHaveAttribute("lang", "es");
      await expect(
        page.getByRole("heading", { level: 1, name: es.auth.signUp.title })
      ).toBeVisible();

      await irAlPaso3(page, es);
      await page.getByRole("checkbox").check();
      await googleDe(page).click();

      await expect(
        page.getByRole("alert").filter({ hasText: es.auth.completeSignUp.fixHighlighted })
      ).toBeVisible();
      await expect(page.getByText(es.errors.codes.username_already_used)).toBeVisible();
      await expect(page).toHaveURL(/\/complete-signup$/);

      // Al volver a inglés se traduce de nuevo.
      await page.getByRole("radio", { name: "English" }).click();
      await expect(page.locator("html")).toHaveAttribute("lang", "en");
      await expect(
        page.getByRole("alert").filter({ hasText: en.auth.completeSignUp.fixHighlighted })
      ).toBeVisible();
      await expect(page.getByText(en.errors.codes.username_already_used)).toBeVisible();
      await sinDesborde(page);
    });

    for (const [origen, ruta, nombre] of [
      ["register", /\/register$/, en.auth.completeSignUp.backToSignUp],
      ["login", /\/login$/, en.auth.completeSignUp.backToLogIn],
    ] as const) {
      test(`«Back» en el paso 2 vuelve a ${origen} y descarta el alta`, async ({
        page,
        baseURL,
      }) => {
        await prepararAlta(page, baseURL!, { origen });
        await abrir(page, en);

        await page.getByRole("button", { name: nombre }).click();

        await expect(page).toHaveURL(ruta, { timeout: 20_000 });
        expect(
          await page.evaluate(() => sessionStorage.getItem("google_signup_pending"))
        ).toBeNull();
      });
    }
  });
}

test("sin un alta con Google pendiente redirige al login", async ({ page, baseURL }) => {
  await prepararAlta(page, baseURL!, { origen: null });
  await page.goto("/complete-signup");

  await expect(page).toHaveURL(/\/login$/, { timeout: 20_000 });
});
