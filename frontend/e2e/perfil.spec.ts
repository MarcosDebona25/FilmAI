import { expect, test } from "@playwright/test";

import es from "../messages/es/common.json";
import { prepararCuenta } from "./cuenta";

test("edita nombre compuesto y avatar; la navbar refleja el cambio", async ({ page }) => {
  const cuenta = await prepararCuenta(page);
  await page.goto("/profile");
  // Canvas: el título de la página es el nombre de la persona.
  await expect(page.getByRole("heading", { level: 1, name: "Juan Pérez" })).toBeVisible();
  await expect(page.getByText("Pérez", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Editar perfil" }).click();
  await expect(page.getByText(es.auth.signUp.nameHelp).first()).toBeVisible();
  await page.getByLabel("Nombre", { exact: true }).fill("  Juan   Carlos  ");
  await page.getByLabel("Apellido", { exact: true }).fill(" De   la Cruz ");
  await page.getByRole("button", { name: "Cambiar avatar" }).click();
  await expect(page.getByRole("radio", { name: /^Avatar / })).toHaveCount(26);
  await page.getByRole("radio", { name: "Avatar 26" }).check();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Guardar", exact: true }).click();
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByRole("heading", { name: "Juan Carlos De la Cruz" })).toBeVisible();
  expect(cuenta.getPerfil()).toMatchObject({
    nombre: "Juan Carlos",
    apellido: "De la Cruz",
    avatar_id: 26,
  });
  await expect(
    page
      .getByRole("button", { name: "Menú de Juan Carlos De la Cruz" })
      .getByAltText(es.common.avatar.currentAlt)
  ).toBeVisible();
});

test("enfoca el dato inválido y advierte antes de perder cambios", async ({ page }) => {
  await prepararCuenta(page);
  await page.goto("/profile");
  await page.getByRole("button", { name: "Editar perfil" }).click();
  await page.getByLabel("Apellido", { exact: true }).fill("123");
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByLabel("Apellido", { exact: true })).toBeFocused();
  await expect(
    page.getByRole("alert").filter({ hasText: es.errors.codes.person_name_invalid })
  ).toBeVisible();

  await page.getByRole("banner").getByRole("link", { name: es.nav.main.brandHomeLabel }).click();
  await expect(page.getByRole("dialog", { name: "¿Salir sin guardar?" })).toBeVisible();
  await page.getByRole("button", { name: "Seguir editando" }).click();
  await expect(page).toHaveURL(/\/profile$/);
});

test("cancelar conserva el borrador o descarta solo tras confirmar", async ({ page }) => {
  const cuenta = await prepararCuenta(page);
  await page.goto("/profile");
  await page.getByRole("button", { name: "Editar perfil" }).click();
  await page.getByRole("button", { name: "Cambiar avatar" }).click();
  await page.getByRole("radio", { name: "Avatar 2", exact: true }).check();
  await page.getByRole("dialog").getByRole("button", { name: "Guardar", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  expect(cuenta.getPerfil().avatar_id).toBe(1);
  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  await page.getByRole("button", { name: "Seguir editando" }).click();
  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  await page.getByRole("button", { name: "Salir sin guardar" }).click();
  await expect(page.getByRole("button", { name: "Editar perfil" })).toBeVisible();
  expect(cuenta.getPerfil().avatar_id).toBe(1);
});
test("confirma navegación a un enlace y atrás/adelante sin perder el destino", async ({ page }) => {
  await prepararCuenta(page);
  await page.goto("/settings");
  await page.getByRole("button", { name: "Menú de Juan Pérez" }).click();
  await page.getByRole("menuitem", { name: "Mi perfil" }).click();
  await page.getByRole("button", { name: "Editar perfil" }).click();
  await page.getByLabel("Nombre", { exact: true }).fill("Pedro");
  await page.evaluate(() => history.back());
  await expect(page.getByRole("dialog", { name: "¿Salir sin guardar?" })).toBeVisible();
  await page.getByRole("button", { name: "Seguir editando" }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByLabel("Nombre", { exact: true })).toHaveValue("Pedro");
  await page.evaluate(() => history.back());
  await page.getByRole("button", { name: "Salir sin guardar" }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await page.evaluate(() => history.forward());
  await expect(page).toHaveURL(/\/profile$/);
  await page.getByRole("button", { name: "Editar perfil" }).click();
  await page.getByLabel("Nombre", { exact: true }).fill("Otro");
  await page.getByRole("banner").getByRole("link", { name: es.nav.main.brandHomeLabel }).click();
  await page.getByRole("button", { name: "Salir sin guardar" }).click();
  await expect(page).toHaveURL("http://127.0.0.1:3100/home");
});
// Solo tema oscuro desde el 15/10/2026.
for (const theme of ["oscuro"])
  test(`disponibilidad verde y roja en tema ${theme}`, async ({ page }) => {
    await prepararCuenta(page);
    await page.route("**/api/preferences/", (route) =>
      route.fulfill({ json: { tema: theme, perfil_publico: true } })
    );
    await page.route("**/api/auth/username-available/**", (route) =>
      route.fulfill({ json: { disponible: !route.request().url().includes("ocupado") } })
    );
    await page.goto("/profile");
    await page.getByRole("button", { name: "Editar perfil" }).click();
    await page.getByLabel("Nombre de usuario", { exact: true }).fill("disponible");
    // Colores del canvas: `ok` y `destructive`.
    await expect(page.getByText("Disponible", { exact: true })).toHaveClass(/text-ok/);
    await page.getByLabel("Nombre de usuario", { exact: true }).fill("ocupado");
    await expect(page.getByText("No disponible", { exact: true })).toHaveClass(/text-destructive/);
  });

test("adelante con cambios permite continuar editando o confirmar el destino", async ({ page }) => {
  await prepararCuenta(page);
  await page.goto("/profile");
  await page.getByRole("button", { name: "Menú de Juan Pérez" }).click();
  await page.getByRole("menuitem", { name: "Preferencias" }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await page.evaluate(() => history.back());
  await page.getByRole("button", { name: "Editar perfil" }).click();
  await page.getByLabel("Nombre", { exact: true }).fill("Pedro");
  await page.evaluate(() => history.forward());
  await page.getByRole("button", { name: "Seguir editando" }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByLabel("Nombre", { exact: true })).toHaveValue("Pedro");
  await page.evaluate(() => history.forward());
  await page.getByRole("button", { name: "Salir sin guardar" }).click();
  await expect(page).toHaveURL(/\/settings$/);
});
test("recargar usa aviso nativo y Escape cierra el selector sin cambiar avatar", async ({
  page,
}) => {
  const state = await prepararCuenta(page);
  await page.goto("/profile");
  await page.getByRole("button", { name: "Editar perfil" }).click();
  await page.getByRole("button", { name: "Cambiar avatar" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Cambiar avatar" })).toBeFocused();
  expect(state.getPerfil().avatar_id).toBe(1);
  await page.getByLabel("Nombre", { exact: true }).fill("Pedro");
  const warning = page.waitForEvent("dialog");
  const reload = page.evaluate(() => window.location.reload());
  const dialog = await warning;
  expect(dialog.type()).toBe("beforeunload");
  await dialog.dismiss();
  await reload;
  await expect(page.getByLabel("Nombre", { exact: true })).toHaveValue("Pedro");
});
