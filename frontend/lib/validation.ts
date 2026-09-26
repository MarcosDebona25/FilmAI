// Reglas de validación del CU-001 (docs/02) para el formulario de registro.
// Cada validador devuelve null si el valor es válido, o el mensaje de error.

const NOMBRE_REGEX = /^\p{L}+(?: \p{L}+)*$/u;
export const USERNAME_REGEX = /^[A-Za-z0-9]{5,25}$/;
const CORREO_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const ESPECIAL_REGEX = /[@#$%&*!]/;

export function validarNombre(valor: string): string | null {
  const v = normalizarNombre(valor);
  if (!v) return "Campo obligatorio.";
  if (v.length > 50) return "Máximo 50 caracteres.";
  if (!NOMBRE_REGEX.test(v)) return "Solo letras y espacios entre palabras.";
  return null;
}

export function normalizarNombre(valor: string): string {
  return valor.trim().replace(/\s+/g, " ");
}

export function validarApellido(valor: string): string | null {
  return validarNombre(valor);
}

export function validarNombreUsuario(valor: string): string | null {
  if (!valor) return "Campo obligatorio.";
  if (!USERNAME_REGEX.test(valor)) return "Alfanumérico, de 5 a 25 caracteres.";
  return null;
}

export function validarCorreo(valor: string): string | null {
  if (!valor) return "Campo obligatorio.";
  if (!CORREO_REGEX.test(valor)) return "Formato de correo inválido.";
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
  if (!valor) return "Campo obligatorio.";
  const fecha = new Date(`${valor}T00:00:00`);
  if (Number.isNaN(fecha.getTime())) return "Fecha inválida.";
  if (fecha > new Date()) return "No puede ser una fecha futura.";
  if (calcularEdad(fecha) < 13) return "Debés tener al menos 13 años.";
  return null;
}

export function validarPassword(valor: string): string | null {
  if (!valor) return "Campo obligatorio.";
  if (valor.length < 8 || valor.length > 20) return "Debe tener entre 8 y 20 caracteres.";
  if (!/[A-Z]/.test(valor)) return "Debe tener al menos una mayúscula.";
  if (!/[a-z]/.test(valor)) return "Debe tener al menos una minúscula.";
  if (!/\d/.test(valor)) return "Debe tener al menos un número.";
  if (!ESPECIAL_REGEX.test(valor)) return "Debe tener un carácter especial (@#$%&*!).";
  return null;
}

export function validarConfirmacion(password: string, confirmacion: string): string | null {
  if (!confirmacion) return "Campo obligatorio.";
  if (password !== confirmacion) return "Las contraseñas no coinciden.";
  return null;
}
