import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch } from "@/lib/api";
import {
  handleGoogleLogin,
  limpiarGooglePendiente,
  marcarGooglePendiente,
  origenGooglePendiente,
  tieneGooglePendiente,
} from "@/lib/google-auth";

vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}));
vi.mock("@/lib/account-locale", () => ({ synchronizeAccountLocale: vi.fn() }));

afterEach(() => {
  sessionStorage.clear();
  vi.clearAllMocks();
});

// La marca protege `/complete-signup` y recuerda desde qué pantalla se tocó
// «Continue with Google», que es a donde vuelve «Back» en el paso 2.
describe("marca del alta con Google pendiente", () => {
  it("sin marca no hay alta pendiente ni origen", () => {
    expect(tieneGooglePendiente()).toBe(false);
    expect(origenGooglePendiente()).toBeNull();
  });

  it.each(["register", "login"] as const)("guarda el origen (%s)", (origen) => {
    marcarGooglePendiente(origen);

    expect(tieneGooglePendiente()).toBe(true);
    expect(origenGooglePendiente()).toBe(origen);

    limpiarGooglePendiente();
    expect(tieneGooglePendiente()).toBe(false);
  });

  it("una marca anterior a guardar el origen sigue valiendo y cuenta como Log in", () => {
    sessionStorage.setItem("google_signup_pending", "1");

    expect(tieneGooglePendiente()).toBe(true);
    expect(origenGooglePendiente()).toBe("login");
  });

  it("una cuenta nueva que entra por Log in queda marcada con ese origen", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError(400, {
        code: "validation_error",
        params: {},
        errors: [{ field: "nombre_usuario", code: "required", params: {} }],
      })
    );

    expect(await handleGoogleLogin("token")).toEqual({ ok: false, faltaCampos: true });
    expect(origenGooglePendiente()).toBe("login");
  });
});
