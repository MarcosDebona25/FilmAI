import { expect, test } from "@playwright/test";

import { prepararCuenta } from "./cuenta";

test("guarda el tema y muestra el alcance pendiente de las otras preferencias", async ({
  page,
}) => {
  const cuenta = await prepararCuenta(page);
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Preferencias" })).toBeVisible();
  await expect(page.getByRole("note")).toContainText("todavía no cambian la visibilidad");
  await page.getByRole("radio", { name: "Claro" }).check();
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  expect(cuenta.getPreferencias().tema).toBe("claro");
  await page.reload();
  await expect(page.getByRole("radio", { name: "Claro" })).toBeChecked();
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
  await expect(page.getByRole("dialog")).toContainText("Esta acción es irreversible.");
  await expect(page.getByRole("dialog")).toContainText(
    "Asegurate de querer dar de baja la cuenta antes de continuar."
  );
  await expect(page.getByRole("dialog")).not.toContainText("se conservarán");
  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  expect(calls).toBe(0);
  await page.getByRole("button", { name: "Dar de baja cuenta" }).click();
  await page.getByRole("button", { name: "Dar de baja", exact: true }).click();
  await expect(page).toHaveURL("http://127.0.0.1:3100/");
  expect(calls).toBe(1);
});
