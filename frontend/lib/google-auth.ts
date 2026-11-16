import { translateError, type CodedError } from "./errors";
import { synchronizeAccountLocale } from "./account-locale";
import { ApiError, apiFetch } from "@/lib/api";

const CAMPOS_FALTANTES = ["nombre_usuario", "pais", "fecha_nacimiento", "genero"];

// Marca el flujo de registro con Google pendiente (protege /complete-signup).
// NO se guarda el id_token: es de un solo uso (anti-replay de allauth) y en la
// pantalla de completado se pide uno FRESCO a Google.
const MARKER_GOOGLE_PENDIENTE = "google_signup_pending";

export function esFaltaDeCamposGoogle(details: unknown): boolean {
  if (!details || typeof details !== "object") return false;
  return (
    Array.isArray(details) &&
    details.some(
      (error: { field?: string; code?: string }) =>
        error.field && CAMPOS_FALTANTES.includes(error.field) && error.code === "required"
    )
  );
}

/** Pantalla desde la que se tocó «Continue with Google»: a ella vuelve «Back». */
export type OrigenGoogle = "login" | "register";

export function marcarGooglePendiente(origen: OrigenGoogle): void {
  sessionStorage.setItem(MARKER_GOOGLE_PENDIENTE, origen);
}

/**
 * Origen del alta pendiente, o `null` si no hay ninguna. Cualquier otro valor
 * (el "1" de una pestaña abierta antes de guardar el origen) cuenta como Log in.
 */
export function origenGooglePendiente(): OrigenGoogle | null {
  if (typeof window === "undefined") return null;
  const valor = sessionStorage.getItem(MARKER_GOOGLE_PENDIENTE);
  if (valor === null) return null;
  return valor === "register" ? "register" : "login";
}

export function tieneGooglePendiente(): boolean {
  return origenGooglePendiente() !== null;
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
    const data = await apiFetch<{ user?: { nombre_usuario?: string } }>("/api/auth/google/", {
      method: "POST",
      body: { id_token: idToken },
    });
    await synchronizeAccountLocale();
    return { ok: true, usuario: data.user?.nombre_usuario };
  } catch (err) {
    if (err instanceof ApiError && err.status === 400 && esFaltaDeCamposGoogle(err.errors)) {
      // Cuenta nueva que arrancó por el botón de "Iniciar sesión": se la lleva
      // al completado de registro (con un id_token fresco).
      marcarGooglePendiente("login");
      return { ok: false, faltaCampos: true };
    }
    return {
      ok: false,
      faltaCampos: false,
      error:
        err instanceof ApiError
          ? err.message
          : translateError({ code: "google_authentication_failed" }),
    };
  }
}

/**
 * El error vuelve como código (no como texto) para que la pantalla lo traduzca
 * al renderizar: el selector EN|ES sigue activo durante el alta.
 */
export type CompletarGoogleResult =
  { ok: true; usuario?: string } | { ok: false; error: CodedError };

export async function completarRegistroGoogle(
  idToken: string,
  campos: {
    nombre_usuario: string;
    pais: string;
    fecha_nacimiento: string;
    genero: string;
    acepta_terminos: boolean;
    /** Opcional: sin él, el backend asigna el avatar por defecto. */
    avatar_id?: number;
  }
): Promise<CompletarGoogleResult> {
  try {
    const data = await apiFetch<{ user?: { nombre_usuario?: string } }>("/api/auth/google/", {
      method: "POST",
      body: { id_token: idToken, ...campos },
    });
    limpiarGooglePendiente();
    await synchronizeAccountLocale();
    return { ok: true, usuario: data.user?.nombre_usuario };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, error: { code: err.code, params: err.params, errors: err.errors } };
    }
    return { ok: false, error: { code: "unknown" } };
  }
}
