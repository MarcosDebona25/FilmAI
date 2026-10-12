import { expect, test, type Page } from "@playwright/test";

import es from "../messages/es/common.json";
import { prepararCuenta } from "./cuenta";

const viewports = [
  { name: "escritorio", width: 1440, height: 900, movil: false },
  { name: "celular", width: 390, height: 844, movil: true },
] as const;

const etiquetaMenu = es.nav.account.userMenuLabel.replace("{name}", "Juan Pérez");

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

for (const viewport of viewports) {
  test.describe(`errores y menú de cuenta en ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("404: explica el error y ofrece volver al inicio o buscar", async ({ page }) => {
      await prepararCuenta(page);
      const response = await page.goto("/esta-pagina-no-existe");
      expect(response?.status()).toBe(404);
      await expect(
        page.getByRole("heading", { name: es.errors.pages.notFoundTitle, level: 1 })
      ).toBeVisible();
      await expect(page.getByText(es.errors.pages.notFoundCode)).toBeVisible();
      await expect(page.getByText(es.errors.pages.notFoundDescription)).toBeVisible();
      await expect(
        page.getByRole("img", { name: es.errors.pages.ticketIllustrationAlt })
      ).toBeVisible();
      await expect(
        page.getByRole("main").getByRole("link", { name: es.nav.main.backHome })
      ).toHaveAttribute("href", "/home");
      await expect(
        page.getByRole("main").getByRole("link", { name: es.nav.main.search })
      ).toHaveAttribute("href", "/search");
      await sinDesborde(page);
    });

    test("404 sin sesión: invita a iniciar sesión o crear cuenta", async ({ page, baseURL }) => {
      await page.context().addCookies([{ name: "csrftoken", value: "test", url: baseURL! }]);
      await page.route("**/api/profile/", (route) =>
        route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
      );
      const response = await page.goto("/esta-pagina-no-existe");
      expect(response?.status()).toBe(404);
      await expect(
        page.getByRole("heading", { name: es.errors.pages.notFoundSignedOutTitle, level: 1 })
      ).toBeVisible();
      await expect(page.getByText(es.errors.pages.notFoundSignedOutDescription)).toBeVisible();
      const principal = page.getByRole("main");
      await expect(principal.getByRole("link", { name: es.nav.main.backHome })).toHaveAttribute(
        "href",
        "/home"
      );
      await expect(principal.getByRole("link", { name: es.nav.account.logIn })).toHaveAttribute(
        "href",
        "/login"
      );
      await expect(
        principal.getByRole("link", { name: es.errors.pages.createFreeAccount })
      ).toHaveAttribute("href", "/register");
      await expect(principal.getByRole("link", { name: es.nav.main.search })).toHaveCount(0);
      // Sin sesión no hay barra de pestañas ni enlace a Lists. El footer sí lista
      // «Mis listas» y «Mi perfil», por eso la coincidencia es exacta.
      await expect(page.getByRole("link", { name: es.nav.main.lists, exact: true })).toHaveCount(0);
      await expect(
        page.getByRole("link", { name: es.nav.main.profileShort, exact: true })
      ).toHaveCount(0);
      await sinDesborde(page);
    });

    test("error inesperado: Reintentar vuelve a pedir los datos", async ({ page }) => {
      await prepararCuenta(page);
      let fallar = true;
      await page.route("**/api/reviews/mias/**", (route) =>
        route.fulfill({
          json: fallar
            ? { total: 1, next: null, results: "roto" }
            : { total: 0, next: null, results: [] },
        })
      );
      await page.goto("/my-reviews");
      await expect(
        page.getByRole("heading", { name: es.errors.pages.unexpectedTitle, level: 1 })
      ).toBeVisible();
      await expect(page.getByText(es.errors.pages.serverTitle)).toBeVisible();
      await expect(page.getByText(es.errors.pages.unexpectedDescription)).toBeVisible();
      await expect(
        page.getByRole("main").getByRole("link", { name: es.nav.main.backHome })
      ).toHaveAttribute("href", "/home");
      await sinDesborde(page);
      fallar = false;
      await page.getByRole("button", { name: es.common.actions.retry }).click();
      await expect(
        page.getByRole("heading", { name: es.errors.pages.unexpectedTitle })
      ).toHaveCount(0);
      await expect(page.getByRole("heading", { name: es.legacy.metadata.myReviews })).toBeVisible();
    });

    test("navegación: enlaces del encabezado en escritorio, barra inferior en celular", async ({
      page,
    }) => {
      await prepararCuenta(page);
      await page.goto("/esta-pagina-no-existe");
      const principal = page.getByRole("navigation", { name: es.nav.main.mainLabel });
      await expect(principal).toHaveCount(1);
      await expect(principal.getByRole("link")).toHaveText(
        viewport.movil
          ? [es.nav.main.home, es.nav.main.search, es.nav.main.lists, es.nav.main.profileShort]
          : [es.nav.main.home, es.nav.main.search, es.nav.main.lists]
      );
      if (viewport.movil) {
        const caja = await principal.boundingBox();
        expect(caja?.y).toBeGreaterThan(viewport.height - 100);
        await principal.getByRole("link", { name: es.nav.main.profileShort }).click();
        await expect(page).toHaveURL(/\/profile$/);
      } else {
        await principal.getByRole("link", { name: es.nav.main.search }).click();
        await expect(page).toHaveURL(/\/search$/);
        await expect(
          page.getByRole("heading", { name: es.errors.pages.notFoundTitle, level: 1 })
        ).toBeVisible();
      }
    });

    test("menú de cuenta: identidad, teclado y destinos", async ({ page }) => {
      await prepararCuenta(page);
      await page.route("**/api/reviews/mias/**", (route) =>
        route.fulfill({ json: { total: 0, next: null, results: [] } })
      );
      await page.goto("/settings");
      const boton = page.getByRole("button", { name: etiquetaMenu });
      await boton.click();
      const menu = page.getByRole("menu", { name: es.nav.account.optionsLabel });
      await expect(menu.getByText("Juan Pérez")).toBeVisible();
      await expect(menu.getByText("@juanperez")).toBeVisible();
      await expect(menu.getByRole("menuitem")).toHaveText([
        es.nav.main.profile,
        es.nav.main.ratingsReviews,
        es.nav.main.settings,
        es.nav.account.logOut,
      ]);
      await expect(menu.getByRole("menuitem", { name: es.nav.main.profile })).toBeFocused();
      await sinDesborde(page);
      await page.keyboard.press("Escape");
      await expect(menu).toHaveCount(0);
      await expect(boton).toBeFocused();
      await boton.click();
      await page.getByRole("menuitem", { name: es.nav.main.ratingsReviews }).click();
      await expect(page).toHaveURL(/\/my-reviews$/);
    });

    test("cerrar sesión: confirma, cancela y sale a la landing", async ({ page }) => {
      await prepararCuenta(page);
      let cerrada = false;
      await page.route("**/api/auth/logout/", (route) => {
        cerrada = true;
        return route.fulfill({ json: {} });
      });
      await page.goto("/settings");
      await page.getByRole("button", { name: etiquetaMenu }).click();
      await page.getByRole("menuitem", { name: es.nav.account.logOut }).click();
      const dialogo = page.getByRole("alertdialog", { name: es.nav.account.logoutConfirmTitle });
      await expect(dialogo.getByText(es.nav.account.logoutConfirmDescription)).toBeVisible();
      await expect(dialogo.getByRole("button", { name: es.common.actions.cancel })).toBeFocused();
      await sinDesborde(page);
      await page.keyboard.press("Escape");
      await expect(dialogo).toHaveCount(0);
      expect(cerrada).toBe(false);
      await expect(page).toHaveURL(/\/settings$/);

      await page.getByRole("button", { name: etiquetaMenu }).click();
      await page.getByRole("menuitem", { name: es.nav.account.logOut }).click();
      await dialogo.getByRole("button", { name: es.nav.account.logOut }).click();
      await expect(page).toHaveURL(/\/$/);
      expect(cerrada).toBe(true);
      await expect(page.getByRole("heading", { name: "FilmAI", level: 1 })).toBeVisible();
    });
  });
}
