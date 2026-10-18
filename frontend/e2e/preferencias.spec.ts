import { expect, test } from "@playwright/test";

import { prepararCuenta } from "./cuenta";

test("la app es solo oscura: sin selector de tema", async ({ page }) => {
  await prepararCuenta(page);
  await page.goto("/settings");

  await expect(page.getByRole("heading", { name: "Preferencias", level: 1 })).toBeVisible();
  await expect(page.getByRole("radio", { name: "Claro" })).toHaveCount(0);
  await expect(page.locator("html")).toHaveClass(/dark/);
});

test("un interruptor guarda la preferencia y lo anuncia", async ({ page }) => {
  const cuenta = await prepararCuenta(page);
  await page.goto("/settings");
  await expect(page.getByRole("note")).toContainText("todavía no cambian la visibilidad");

  const semanal = page.getByRole("switch", { name: "Recomendaciones semanales" });
  const antes = cuenta.getPreferencias().notif_recomendaciones;
  await expect(semanal).toHaveAttribute("aria-checked", String(antes));
  await semanal.click();

  await expect(semanal).toHaveAttribute("aria-checked", String(!antes));
  expect(cuenta.getPreferencias().notif_recomendaciones).toBe(!antes);
  await expect(page.getByRole("switch", { name: "Perfil público" })).toBeVisible();
});

test("baja: advertencia aprobada, cancelar y confirmar", async ({ page }) => {
  await prepararCuenta(page);
  let calls = 0;
  await page.route("**/api/account/deactivate/", async (route) => {
    calls++;
    await route.fulfill({ status: 200, json: { code: "account_deactivated_successfully" } });
  });
  await page.goto("/settings");
  await page.getByRole("button", { name: "Dar de baja cuenta" }).click();
  const confirmacion = page.getByRole("alertdialog");
  await expect(confirmacion).toContainText("Esta acción es irreversible.");
  await expect(confirmacion).toContainText(
    "Asegurate de querer dar de baja la cuenta antes de continuar."
  );
  await expect(confirmacion).not.toContainText("se conservarán");
  await confirmacion.getByRole("button", { name: "Cancelar", exact: true }).click();
  expect(calls).toBe(0);
  await page.getByRole("button", { name: "Dar de baja cuenta" }).click();
  await page
    .getByRole("alertdialog")
    .getByRole("button", { name: "Dar de baja", exact: true })
    .click();
  await expect(page).toHaveURL("http://127.0.0.1:3100/");
  expect(calls).toBe(1);
});
