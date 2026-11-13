import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import en from "../messages/en/common.json";
import es from "../messages/es/common.json";

// axe-core se inyecta en la página, como en a11y-axe.spec.ts.
const axeSource = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

type Axe = { run: (c: unknown, o: unknown) => Promise<{ violations: { id: string }[] }> };

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 390, height: 844 },
] as const;

async function sinSesion(page: Page) {
  await page.route("**/api/profile/", (route) =>
    route.fulfill({ status: 401, json: { code: "not_authenticated", params: {}, errors: [] } })
  );
}

/** WCAG 2.1 A y AA solo sobre la sección de créditos. */
async function auditarCreditos(page: Page) {
  await page.addScriptTag({ content: axeSource });
  const infracciones = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: Axe }).axe;
    const resultado = await axe.run(document.querySelector("#credits"), {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
    });
    return resultado.violations.map((v) => v.id);
  });
  expect(infracciones).toEqual([]);
}

// La app es solo oscura desde el 18/10/2026: no hay tema claro que probar.
for (const viewport of viewports) {
  for (const [locale, catalogo] of [
    ["en", en],
    ["es", es],
  ] as const) {
    test.describe(`créditos de TMDB · ${viewport.name} · ${locale}`, () => {
      test.use({ viewport: { width: viewport.width, height: viewport.height } });

      test.beforeEach(async ({ page, baseURL }) => {
        await page.context().addCookies([{ name: "filmai_locale", value: locale, url: baseURL! }]);
        await sinSesion(page);
      });

      test("/terms#credits muestra el aviso exacto y el logo oficial sin alterar", async ({
        page,
      }) => {
        await page.goto("/terms#credits");
        const seccion = page.locator("section#credits");
        await expect(seccion).toBeVisible();
        await expect(
          seccion.getByRole("heading", { name: catalogo.tmdb.credits.title })
        ).toBeVisible();
        await expect(
          seccion.getByText(catalogo.tmdb.credits.notice, { exact: true })
        ).toBeVisible();

        const logo = seccion.getByRole("img", { name: catalogo.tmdb.credits.logoAlt });
        await expect(logo).toBeVisible();
        // Carga de verdad (no un ícono roto) y ningún estilo lo recolorea ni lo deforma.
        expect(await logo.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
        expect(await logo.evaluate((img) => getComputedStyle(img).filter)).toBe("none");
        const caja = (await logo.boundingBox())!;
        expect(caja.width / caja.height).toBeCloseTo(273.42 / 35.52, 1);
        await expect(seccion.getByRole("link")).toHaveAttribute(
          "href",
          "https://www.themoviedb.org"
        );

        await auditarCreditos(page);
      });

      test("el enlace «Credits» del pie lleva a la sección", async ({ page }) => {
        await page.goto("/terms");
        const pie = page.getByRole("contentinfo");
        await expect(pie.getByText(catalogo.footer.main.tmdbAttribution)).toBeVisible();
        await pie.getByRole("link", { name: catalogo.footer.main.creditsLink }).click();
        await expect(page).toHaveURL(/\/terms#credits$/);
        await expect(page.locator("section#credits")).toBeInViewport();
      });
    });
  }
}
