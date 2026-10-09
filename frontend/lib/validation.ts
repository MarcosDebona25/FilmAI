// Reglas de validación del CU-001 (docs/02) para el formulario de registro.
// Cada validador devuelve null o un código independiente del idioma.

const NOMBRE_REGEX = /^\p{L}+(?: \p{L}+)*$/u;
export const USERNAME_REGEX = /^[A-Za-z0-9]{5,25}$/;
const CORREO_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const ESPECIAL_REGEX = /[@#$%&*!]/;

export function validarNombre(valor: string): string | null {
  const v = normalizarNombre(valor);
  if (!v) return "required";
  if (v.length > 50) return "max_length";
  if (!NOMBRE_REGEX.test(v)) return "person_name_invalid";
  return null;
}

export function normalizarNombre(valor: string): string {
  return valor.trim().replace(/\s+/g, " ");
}

export function validarApellido(valor: string): string | null {
  return validarNombre(valor);
}

export function validarNombreUsuario(valor: string): string | null {
  if (!valor) return "required";
  if (!USERNAME_REGEX.test(valor)) return "username_invalid";
  return null;
}

export function validarCorreo(valor: string): string | null {
  if (!valor) return "required";
  if (!CORREO_REGEX.test(valor)) return "invalid";
  return null;
}

function calcularEdad(fecha: Date): number {
  const hoy = new Date();
  const yaCumplio =
    hoy.getMonth() > fecha.getMonth() ||
    (hoy.getMonth() === fecha.getMonth() && hoy.getDate() >= fecha.getDate());
  return hoy.getFullYear() - fecha.getFullYear() - (yaCumplio ? 0 : 1);
}

export function validarFechaNacimiento(valor: string): string | null {
  if (!valor) return "required";
  const fecha = new Date(`${valor}T00:00:00`);
  if (Number.isNaN(fecha.getTime())) return "invalid";
  if (fecha > new Date()) return "birth_date_in_future";
  if (calcularEdad(fecha) < 13) return "minimum_age";
  return null;
}

export function validarPassword(valor: string): string | null {
  if (!valor) return "required";
  if (valor.length < 8 || valor.length > 20) return "password_too_short_or_long";
  if (!/[A-Z]/.test(valor)) return "password_no_upper";
  if (!/[a-z]/.test(valor)) return "password_no_lower";
  if (!/\d/.test(valor)) return "password_no_digit";
  if (!ESPECIAL_REGEX.test(valor)) return "password_no_special";
  return null;
}

export function validarConfirmacion(password: string, confirmacion: string): string | null {
  if (!confirmacion) return "required";
  if (password !== confirmacion) return "passwords_do_not_match";
  return null;
}
