import { expect, test } from "@playwright/test";

test.describe("idioma del documento sin prefijos", () => {
  test("una cookie soportada gana al encabezado", async ({ page, baseURL }) => {
    await page.context().addCookies([{ name: "filmai_locale", value: "en", url: baseURL! }]);
    await page.goto("/login");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  });

  test("sin cookie usa la región del navegador", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("html")).toHaveAttribute("lang", "es");
  });

  test("ignora la cookie inválida y usa los pesos del encabezado", async ({ request }) => {
    const response = await request.get("/login", {
      headers: { Cookie: "filmai_locale=fr", "Accept-Language": "en-US;q=0.2,es-MX;q=0.9" },
    });
    expect(await response.text()).toMatch(/<html[^>]*lang="es"/);
  });

  test("el encabezado no soportado usa inglés", async ({ request }) => {
    const response = await request.get("/login", { headers: { "Accept-Language": "fr-FR" } });
    expect(await response.text()).toMatch(/<html[^>]*lang="en"/);
  });
});
