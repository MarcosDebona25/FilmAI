import { ApiError, apiFetch, storeTokens } from "@/lib/api";

const CAMPOS_FALTANTES = ["nombre_usuario", "fecha_nacimiento", "genero"];

export function esFaltaDeCamposGoogle(details: unknown): boolean {
  if (!details || typeof details !== "object") return false;
  const keys = Object.keys(details);
  return keys.some((k) => CAMPOS_FALTANTES.includes(k));
}

export type GoogleLoginResult =
  | { ok: true; usuario?: string }
  | { ok: false; faltaCampos: true }
  | { ok: false; faltaCampos: false; error: string };

export async function handleGoogleLogin(idToken: string): Promise<GoogleLoginResult> {
  try {
    const data = await apiFetch<{
      access: string;
      refresh: string;
      user?: { nombre_usuario?: string };
    }>("/api/auth/google/", {
      method: "POST",
      body: { id_token: idToken },
      auth: false,
    });
    storeTokens(data.access);
    return { ok: true, usuario: data.user?.nombre_usuario };
  } catch (err) {
    if (err instanceof ApiError && err.status === 400 && esFaltaDeCamposGoogle(err.details)) {
      sessionStorage.setItem("google_id_token", idToken);
      return { ok: false, faltaCampos: true };
    }
    return {
      ok: false,
      faltaCampos: false,
      error: err instanceof ApiError ? err.message : "Error al iniciar con Google.",
    };
  }
}
