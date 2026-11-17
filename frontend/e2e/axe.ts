import { readFileSync } from "node:fs";

import { expect, type Page } from "@playwright/test";

type Infraccion = { id: string; impact: string; nodes: { target: string[] }[] };
type Axe = { run: (c: unknown, o: unknown) => Promise<{ violations: Infraccion[] }> };

// axe-core se inyecta en la página: no hace falta el paquete de Playwright.
const axeSource = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

/** Reglas WCAG 2.1 A y AA; falla con la lista de infracciones. */
export async function auditar(page: Page) {
  await page.addScriptTag({ content: axeSource });
  const infracciones = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: Axe }).axe;
    const resultado = await axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
    });
    return resultado.violations.map((v: Infraccion) => ({
      regla: v.id,
      impacto: v.impact,
      nodos: v.nodes.slice(0, 3).map((n: { target: string[] }) => n.target.join(" ")),
    }));
  });
  expect(infracciones).toEqual([]);
}
