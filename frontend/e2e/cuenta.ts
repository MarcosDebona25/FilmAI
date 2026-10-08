import type { AppLocale } from "@/i18n/config";
import type { Page } from "@playwright/test";

const initialProfile = {
  pk: 1,
  idioma: null as AppLocale | null,
  nombre: "Juan",
  apellido: "Pérez",
  nombre_usuario: "juanperez",
  correo: "juan@example.com",
  fecha_nacimiento: "1992-04-10",
  genero: "masculino",
  fecha_registro: "2026-09-01",
  avatar_id: 1,
  tiene_contrasena_local: true,
};

export async function prepararCuenta(page: Page, idioma: AppLocale | null = null) {
  let perfil = { ...initialProfile, idioma };
  let preferencias = {
    idioma,
    tema: "oscuro",
    perfil_publico: true,
    notif_recomendaciones: true,
    notif_resenas: true,
    notif_novedades: true,
  };
  await page.context().addCookies([
    { name: "access", value: "test-session", url: "http://127.0.0.1:3100" },
    { name: "csrftoken", value: "test-csrf", url: "http://127.0.0.1:3100" },
  ]);
  await page.route("**/api/profile/", async (route) => {
    if (route.request().method() === "PUT")
      perfil = { ...perfil, ...route.request().postDataJSON() };
    await route.fulfill({ json: perfil });
  });
  await page.route("**/api/avatars/", (route) =>
    route.fulfill({
      json: Array.from({ length: 26 }, (_, index) => ({
        id: index + 1,
        src: `/avatars/recortados/avatar%20(${index + 1}).png`,
      })),
    })
  );
  await page.route("**/api/preferences/", async (route) => {
    if (route.request().method() === "PUT") {
      preferencias = { ...preferencias, ...route.request().postDataJSON() };
      perfil = { ...perfil, idioma: preferencias.idioma };
    }
    await route.fulfill({ json: preferencias });
  });
  await page.route("**/api/auth/username-available/**", (route) =>
    route.fulfill({ json: { disponible: true } })
  );
  return { getPerfil: () => perfil, getPreferencias: () => preferencias };
}
