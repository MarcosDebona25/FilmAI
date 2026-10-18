import { expect, test, type Locator } from "@playwright/test";
import { prepararCuenta } from "./cuenta";

async function colors(button: Locator) {
  await button.evaluate(async (element) => {
    await Promise.all(
      element.getAnimations().map((animation) => animation.finished.catch(() => {}))
    );
  });
  return button.evaluate((element) => {
    const style = getComputedStyle(element);
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 1;
    const context = canvas.getContext("2d")!;
    const parse = (color: string) => {
      context.clearRect(0, 0, 1, 1);
      context.fillStyle = color;
      context.fillRect(0, 0, 1, 1);
      const rgba = Array.from(context.getImageData(0, 0, 1, 1).data);
      return [rgba[0], rgba[1], rgba[2], rgba[3] / 255];
    };
    let background = [255, 255, 255];
    const ancestors: Element[] = [];
    let current: Element | null = element;
    while (current) {
      ancestors.unshift(current);
      current = current.parentElement;
    }
    for (const node of ancestors) {
      const rgba = parse(getComputedStyle(node).backgroundColor);
      const alpha = rgba[3] ?? 1;
      background = background.map((value, index) => rgba[index] * alpha + value * (1 - alpha));
    }
    const luminance = (rgb: number[]) =>
      rgb
        .slice(0, 3)
        .map((value) => {
          const normalized = value / 255;
          return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
        })
        .reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
    const a = luminance(parse(style.color));
    const b = luminance(background);
    return {
      color: style.color,
      background: style.backgroundColor,
      contrast: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05),
    };
  });
}

for (const width of [390, 1440])
  test(`avatar temporal, título único y modal sin mover la página a ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const state = await prepararCuenta(page);
    await page.goto("/profile");
    await page.getByRole("button", { name: "Editar perfil" }).click();
    const trigger = page.getByRole("button", { name: "Cambiar avatar" });
    await expect(trigger).toHaveCSS("cursor", "pointer");
    await page.addStyleTag({ content: "body { min-height: 1600px; }" });
    await page.evaluate(() => window.scrollTo(0, 80));
    const bounds = await page.locator("main").boundingBox();
    // El avatar del encabezado; el botón «Cambiar avatar» va encima, aparte.
    const image = page.getByRole("main").getByAltText("Tu avatar");
    const original = await image.getAttribute("src");
    const scroll = await page.evaluate(() => scrollY);
    await trigger.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Elegí un avatar", { exact: true })).toHaveCount(1);
    expect(await page.locator("main").boundingBox()).toEqual(bounds);
    expect(await page.evaluate(() => scrollY)).toBe(scroll);
    await dialog.getByRole("radio", { name: "Avatar 26", exact: true }).check();
    await expect(dialog).toBeVisible();
    expect(await image.getAttribute("src")).toBe(original);
    expect(state.getPerfil().avatar_id).toBe(1);
    await dialog.getByRole("button", { name: "Cancelar", exact: true }).click();
    expect(await image.getAttribute("src")).toBe(original);
    expect(await page.locator("main").boundingBox()).toEqual(bounds);
    await trigger.click();
    await expect(dialog.getByRole("radio", { name: "Avatar 1", exact: true })).toBeChecked();
    await dialog.getByRole("radio", { name: "Avatar 2", exact: true }).check();
    await dialog.getByRole("button", { name: "Guardar", exact: true }).click();
    await expect(dialog).not.toBeVisible();
    await expect(image).not.toHaveAttribute("src", original!);
    expect(state.getPerfil().avatar_id).toBe(1);
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByRole("button", { name: "Editar perfil" })).toBeVisible();
    expect(state.getPerfil().avatar_id).toBe(2);
  });

test("botones consistentes y contraste al menos 4.5", async ({ page }) => {
  await prepararCuenta(page);
  await page.route("**/api/preferences/", (route) =>
    route.fulfill({ json: { perfil_publico: true } })
  );
  await page.goto("/profile");
  await expect(page.locator("html")).toHaveCSS("color-scheme", "dark");
  // Canvas: «Editar perfil» es secundario y los «Guardar» son de acento; los
  // de acento comparten colores y todos alcanzan el contraste.
  const edit = await colors(page.getByRole("button", { name: "Editar perfil" }));
  expect(edit.contrast).toBeGreaterThanOrEqual(4.5);
  await page.getByRole("button", { name: "Editar perfil" }).click();
  const saveProfile = await colors(page.getByRole("button", { name: "Guardar cambios" }));
  expect(saveProfile.contrast).toBeGreaterThanOrEqual(4.5);
  await page.getByRole("button", { name: "Cambiar avatar" }).click();
  const save = page.getByRole("dialog").getByRole("button", { name: "Guardar", exact: true });
  const saveColors = await colors(save);
  expect(saveColors.color).toBe(saveProfile.color);
  expect(saveColors.background).toBe(saveProfile.background);
  expect(saveColors.contrast).toBeGreaterThanOrEqual(4.5);
  await save.hover();
  expect((await colors(save)).contrast).toBeGreaterThanOrEqual(4.5);
  const cancel = page.getByRole("dialog").getByRole("button", { name: "Cancelar" });
  expect((await colors(cancel)).contrast).toBeGreaterThanOrEqual(4.5);
  await cancel.hover();
  expect((await colors(cancel)).contrast).toBeGreaterThanOrEqual(4.5);
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  await page.goto("/settings");
  await expect(page.locator("html")).toHaveCSS("color-scheme", "dark");
  const deactivate = page.getByRole("button", { name: "Dar de baja cuenta" });
  const danger = await colors(deactivate);
  expect(danger.contrast).toBeGreaterThanOrEqual(4.5);
  await deactivate.hover();
  expect((await colors(deactivate)).contrast).toBeGreaterThanOrEqual(4.5);
  await deactivate.click();
  // Canvas: el botón de la página es un contorno rojo y el de confirmar, rojo
  // lleno, dentro de un `alertdialog`. Ya no comparten colores; los dos
  // tienen que alcanzar el contraste.
  const confirm = page
    .getByRole("alertdialog")
    .getByRole("button", { name: "Dar de baja", exact: true });
  await page.mouse.move(0, 0);
  const confirmColors = await colors(confirm);
  expect(confirmColors.contrast).toBeGreaterThanOrEqual(4.5);
});
