// Correo de la cuenta que espera confirmación. Permite reenviar el enlace desde
// la pantalla de «enlace vencido», que solo conoce la clave del enlace.
const KEY = "filmai_pending_email";

export function savePendingEmail(email: string): void {
  try {
    sessionStorage.setItem(KEY, email);
  } catch {
    // Sin almacenamiento: el reenvío pedirá el correo.
  }
}

export function readPendingEmail(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function clearPendingEmail(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // Nada que limpiar.
  }
}

/** Segundos de espera entre reenvíos (también limita el abuso del endpoint). */
export const RESEND_COOLDOWN_SECONDS = 60;

export function formatCountdown(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
