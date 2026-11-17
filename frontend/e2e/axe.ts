import { readFileSync } from "node:fs";

import { expect, type Page } from "@playwright/test";

type Infraccion = { id: string; impact: string; nodes: { target: string[] }[] };
type Axe = { run: (c: unknown, o: unknown) => Promise<{ violations: Infraccion[] }> };

// axe-core se inyecta en la página: no hace falta el paquete de Playwright.
const axeSource = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");

/** Reglas WCAG 2.1 A y AA; falla con la lista de infracciones. */
export async function auditar(page: Page, { esperar = true } = {}) {
  // axe lee el color que se ve en ese instante: con un aviso (sonner) entrando,
  // su opacidad es parcial y el contraste da mal. Se espera a que terminen las
  // transiciones y animaciones cortas. Las largas (la barra de tiempo del aviso,
  // 6 s) no se esperan: el aviso se iría antes de auditarlo.
  if (esperar) {
    await page.evaluate(
      () =>
        new Promise<void>((listo) =>
          requestAnimationFrame(() => requestAnimationFrame(() => listo()))
        )
    );
    await page.waitForFunction(() =>
      document
        .getAnimations()
        .every(
          (a) =>
            a.playState !== "running" || Number(a.effect?.getComputedTiming().endTime ?? 0) > 1000
        )
    );
  }
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
