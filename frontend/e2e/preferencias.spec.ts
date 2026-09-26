import { expect, test } from "@playwright/test";

import { prepararCuenta } from "./cuenta";

test("guarda el tema y muestra el alcance pendiente de las otras preferencias", async ({
  page,
}) => {
  const cuenta = await prepararCuenta(page);
  await page.goto("/preferencias");
  await expect(page.getByRole("heading", { name: "Preferencias" })).toBeVisible();
  await expect(page.getByRole("note")).toContainText("todavía no cambian la visibilidad");
  await page.getByRole("radio", { name: "Claro" }).check();
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  expect(cuenta.getPreferencias().tema).toBe("claro");
  await page.reload();
  await expect(page.getByRole("radio", { name: "Claro" })).toBeChecked();
});
