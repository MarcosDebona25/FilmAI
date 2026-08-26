import { ApiError, apiFetch, extraerErroresPorCampo } from "@/lib/api";

const CAMPOS_FALTANTES = ["nombre_usuario", "fecha_nacimiento", "genero"];

// Marca el flujo de registro con Google pendiente (protege /completar-google).
// NO se guarda el id_token: es de un solo uso (anti-replay de allauth) y en la
// pantalla de completado se pide uno FRESCO a Google.
const MARKER_GOOGLE_PENDIENTE = "google_signup_pending";

export function esFaltaDeCamposGoogle(details: unknown): boolean {
  if (!details || typeof details !== "object") return false;
  const keys = Object.keys(details);
  return keys.some((k) => CAMPOS_FALTANTES.includes(k));
}

export function marcarGooglePendiente(): void {
  sessionStorage.setItem(MARKER_GOOGLE_PENDIENTE, "1");
}

export function tieneGooglePendiente(): boolean {
  return typeof window !== "undefined" && sessionStorage.getItem(MARKER_GOOGLE_PENDIENTE) === "1";
}

export function limpiarGooglePendiente(): void {
  sessionStorage.removeItem(MARKER_GOOGLE_PENDIENTE);
}

export type GoogleLoginResult =
  | { ok: true; usuario?: string }
  | { ok: false; faltaCampos: true }
  | { ok: false; faltaCampos: false; error: string };

export async function handleGoogleLogin(idToken: string): Promise<GoogleLoginResult> {
  try {
    const data = await apiFetch<{ user?: { nombre_usuario?: string } }>(
      "/api/auth/google/",
      { method: "POST", body: { id_token: idToken } }
    );
    return { ok: true, usuario: data.user?.nombre_usuario };
  } catch (err) {
    if (err instanceof ApiError && err.status === 400 && esFaltaDeCamposGoogle(err.details)) {
      // Cuenta nueva que arrancó por el botón de "Iniciar sesión": se la lleva
      // al completado de registro (con un id_token fresco).
      marcarGooglePendiente();
      return { ok: false, faltaCampos: true };
    }
    return {
      ok: false,
      faltaCampos: false,
      error: err instanceof ApiError ? err.message : "Error al iniciar con Google.",
    };
  }
}

export type CompletarGoogleResult =
  | { ok: true; usuario?: string }
  | { ok: false; error: string; erroresPorCampo?: Record<string, string> };

export async function completarRegistroGoogle(
  idToken: string,
  campos: { nombre_usuario: string; fecha_nacimiento: string; genero: string }
): Promise<CompletarGoogleResult> {
  try {
    const data = await apiFetch<{ user?: { nombre_usuario?: string } }>(
      "/api/auth/google/",
      { method: "POST", body: { id_token: idToken, ...campos } }
    );
    limpiarGooglePendiente();
    return { ok: true, usuario: data.user?.nombre_usuario };
  } catch (err) {
    if (err instanceof ApiError) {
      return {
        ok: false,
        error: err.message,
        erroresPorCampo: extraerErroresPorCampo(err.details),
      };
    }
    return { ok: false, error: "No se pudo completar tu cuenta." };
  }
}
