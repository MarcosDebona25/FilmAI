import { expect, test } from "@playwright/test";

import { prepararCuenta } from "./cuenta";

test("edita nombre compuesto y avatar; la navbar refleja el cambio", async ({ page }) => {
  const cuenta = await prepararCuenta(page);
  await page.goto("/perfil");
  await expect(page.getByRole("heading", { name: "Mi perfil" })).toBeVisible();
  await expect(page.getByText("Pérez", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Editar perfil" }).click();
  await expect(
    page
      .getByText("Solo letras y espacios entre palabras; máximo 50 caracteres.", { exact: false })
      .first()
  ).toBeVisible();
  await page.getByLabel("Nombre", { exact: true }).fill("  Juan   Carlos  ");
  await page.getByLabel("Apellido", { exact: true }).fill(" De   la Cruz ");
  await page.getByRole("button", { name: "Cambiar avatar" }).click();
  await expect(page.getByRole("radio", { name: /^Avatar / })).toHaveCount(26);
  await page.getByRole("radio", { name: "Avatar 26" }).check();
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByRole("heading", { name: "Juan Carlos De la Cruz" })).toBeVisible();
  expect(cuenta.getPerfil()).toMatchObject({
    nombre: "Juan Carlos",
    apellido: "De la Cruz",
    avatar_id: 26,
  });
  await expect(
    page
      .getByRole("button", { name: "Menú de usuario" })
      .getByAltText("Avatar de Juan Carlos De la Cruz")
  ).toBeVisible();
});

test("enfoca el dato inválido y advierte antes de perder cambios", async ({ page }) => {
  await prepararCuenta(page);
  await page.goto("/perfil");
  await page.getByRole("button", { name: "Editar perfil" }).click();
  await page.getByLabel("Apellido", { exact: true }).fill("123");
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(page.getByLabel("Apellido", { exact: true })).toBeFocused();
  await expect(page.locator("#apellido-error")).toContainText("Solo letras");

  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("link", { name: "FilmAI" }).click();
  await expect(page).toHaveURL(/\/perfil$/);
});
