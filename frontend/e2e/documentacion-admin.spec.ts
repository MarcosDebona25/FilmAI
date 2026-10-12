import { execFileSync } from "node:child_process";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

/**
 * Sección 12 del canvas: la página de acceso a la documentación interna la
 * sirve Django (`/api/docs/`, `/api/schema/`), no Next.js. Esta prueba usa el
 * backend real de Docker Compose y crea (y borra) sus propias cuentas.
 */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";
const RAIZ = path.resolve(__dirname, "../..");
const CLAVE = "Palomitas24!";
const SUFIJO = `${Date.now().toString(36)}`.slice(-6);
const STAFF = `e2estaff${SUFIJO}`;
const COMUN = `e2ecomun${SUFIJO}`;

const viewports = [
  { name: "escritorio", width: 1440, height: 900 },
  { name: "celular", width: 390, height: 844 },
] as const;

function django(codigo: string): string {
  return execFileSync(
    "docker",
    ["compose", "exec", "-T", "backend", "python", "manage.py", "shell", "-c", codigo],
    { cwd: RAIZ, encoding: "utf8" }
  ).trim();
}

function sesionDe(nombreUsuario: string): string {
  return django(`
from importlib import import_module
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from usuarios.models import Usuario
u = Usuario.objects.get(nombre_usuario="${nombreUsuario}")
s = import_module(settings.SESSION_ENGINE).SessionStore()
s[SESSION_KEY] = str(u.pk)
s[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
s[HASH_SESSION_KEY] = u.get_session_auth_hash()
s.save()
print(s.session_key)
`)
    .split("\n")
    .pop()!;
}

async function sinDesborde(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
}

test.beforeAll(() => {
  django(`
from usuarios.factories import UsuarioFactory
for nombre, staff in (("${STAFF}", True), ("${COMUN}", False)):
    u = UsuarioFactory(nombre_usuario=nombre, correo=nombre + "@example.com", is_staff=staff)
    u.set_password("${CLAVE}")
    u.save()
`);
});

test.afterAll(() => {
  django(`
from usuarios.models import Usuario
Usuario.objects.filter(nombre_usuario__in=["${STAFF}", "${COMUN}"]).delete()
`);
});

for (const viewport of viewports) {
  test.describe(`documentación interna en ${viewport.name}`, () => {
    test.use({
      viewport: { width: viewport.width, height: viewport.height },
      locale: "en-US",
      extraHTTPHeaders: { "Accept-Language": "en-US,en;q=0.9" },
    });

    test("visitante: formulario, error genérico y acceso con cuenta staff", async ({ page }) => {
      const respuesta = await page.goto(`${BACKEND}/api/docs/`);
      expect(respuesta?.status()).toBe(403);
      await expect(page.getByRole("heading", { name: "Admin access", level: 1 })).toBeVisible();
      await expect(page.getByText("Internal documentation", { exact: true })).toBeVisible();
      await expect(page.getByRole("alert")).toHaveCount(0);
      await expect(page.getByRole("link", { name: "Back to FilmAI" })).toBeVisible();
      await sinDesborde(page);

      // Una cuenta común con la contraseña correcta recibe el mismo aviso.
      await page.getByLabel("Email or username").fill(COMUN);
      await page.getByLabel("Password", { exact: true }).fill(CLAVE);
      await page.getByRole("button", { name: "Log in as admin" }).click();
      await expect(page.getByRole("alert")).toHaveText("Incorrect admin credentials.");
      await expect(page.getByLabel("Email or username")).toHaveAttribute("aria-invalid", "true");
      await sinDesborde(page);

      // Staff ingresa con el correo y vuelve a Swagger.
      await page.getByLabel("Email or username").fill(`${STAFF}@example.com`);
      await page.getByLabel("Password", { exact: true }).fill(CLAVE);
      await page.getByRole("button", { name: "Log in as admin" }).click();
      await expect(page).toHaveURL(`${BACKEND}/api/docs/`);
      await expect(page.locator("#swagger-ui")).toBeVisible();
    });

    test("el botón del ojo muestra y oculta la contraseña", async ({ page }) => {
      await page.goto(`${BACKEND}/api/schema/`);
      const clave = page.getByLabel("Password", { exact: true });
      await expect(clave).toHaveAttribute("type", "password");
      await page.getByRole("button", { name: "Show password" }).click();
      await expect(clave).toHaveAttribute("type", "text");
      await page.getByRole("button", { name: "Hide password" }).click();
      await expect(clave).toHaveAttribute("type", "password");
    });

    test("cuenta sin permisos: explica el caso y permite cambiar de cuenta", async ({
      page,
      context,
    }) => {
      await context.addCookies([{ name: "sessionid", value: sesionDe(COMUN), url: BACKEND }]);
      const respuesta = await page.goto(`${BACKEND}/api/docs/`);
      expect(respuesta?.status()).toBe(403);
      await expect(
        page.getByRole("heading", { name: "Your account has no access", level: 1 })
      ).toBeVisible();
      await expect(page.getByText(COMUN, { exact: true })).toBeVisible();
      await expect(page.getByRole("link", { name: "Back to Home" })).toBeVisible();
      await sinDesborde(page);

      await page.getByRole("link", { name: "Switch account" }).click();
      await expect(page.getByRole("heading", { name: "Admin access", level: 1 })).toBeVisible();
      await page.getByLabel("Email or username").fill(STAFF);
      await page.getByLabel("Password", { exact: true }).fill(CLAVE);
      await page.getByRole("button", { name: "Log in as admin" }).click();
      await expect(page).toHaveURL(`${BACKEND}/api/docs/`);
      await expect(page.locator("#swagger-ui")).toBeVisible();
    });
  });
}

test.describe("idioma", () => {
  test.use({ locale: "es-AR", extraHTTPHeaders: { "Accept-Language": "es-AR,es;q=0.9" } });

  test("la página se sirve en español según el navegador", async ({ page }) => {
    await page.goto(`${BACKEND}/api/schema/`);
    await expect(page.locator("html")).toHaveAttribute("lang", "es");
    await expect(
      page.getByRole("heading", { name: "Acceso de administración", level: 1 })
    ).toBeVisible();
    await page.getByLabel("Correo o nombre de usuario").fill("nadie");
    await page.getByLabel("Contraseña", { exact: true }).fill("incorrecta");
    await page.getByRole("button", { name: "Ingresar como administrador" }).click();
    await expect(page.getByRole("alert")).toHaveText("Credenciales de administración incorrectas.");
  });
});
