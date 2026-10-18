import { expect, test } from "@playwright/test";
import en from "../messages/en/common.json";
import es from "../messages/es/common.json";
import { prepararCuenta } from "./cuenta";

test.describe("idioma del documento sin prefijos", () => {
  test("una cookie soportada gana al encabezado", async ({ page, baseURL }) => {
    await page.context().addCookies([{ name: "filmai_locale", value: "en", url: baseURL! }]);
    await page.goto("/login");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: en.nav.account.logIn })).toBeVisible();
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

for (const locale of ["es", "en"] as const) {
  test(`los metadatos actuales usan ${locale} sin traducir las pantallas`, async ({
    page,
    baseURL,
  }) => {
    await prepararCuenta(page);
    await page.context().addCookies([{ name: "filmai_locale", value: locale, url: baseURL! }]);
    await page.route("**/api/reviews/mias/**", (route) =>
      route.fulfill({ json: { total: 0, next: null, results: [] } })
    );
    const catalog = locale === "es" ? es : en;
    const nav = catalog.nav.main;
    const description = catalog.auth.landing.description;
    for (const [path, title] of [
      ["/profile", nav.profile],
      ["/settings", nav.settings],
      ["/my-reviews", nav.ratingsReviews],
    ]) {
      await page.goto(path);
      await expect(page).toHaveTitle(`${title} | FilmAI`);
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
      await expect(page.locator('meta[name="description"]')).toHaveAttribute(
        "content",
        description
      );
    }
  });
}
