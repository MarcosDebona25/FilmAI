import { useMemo } from "react";
import { useLocale } from "next-intl";
import * as validators from "./validation";
import { validationError } from "./validation-error";
import { translateError } from "./errors";

export function useValidation() {
  const locale = useLocale();
  return useMemo(() => {
    function message(code: string | null, field?: string) {
      const error = validationError(code);
      return error ? translateError(error, locale, field) : null;
    }
    return {
      validarNombre: (value: string) => message(validators.validarNombre(value), "nombre"),
      validarApellido: (value: string) => message(validators.validarApellido(value), "apellido"),
      validarNombreUsuario: (value: string) =>
        message(validators.validarNombreUsuario(value), "nombre_usuario"),
      validarCorreo: (value: string) => message(validators.validarCorreo(value), "correo"),
      validarFechaNacimiento: (value: string) =>
        message(validators.validarFechaNacimiento(value), "fecha_nacimiento"),
      validarPassword: (value: string) => message(validators.validarPassword(value)),
      validarConfirmacion: (value: string, confirmation: string) =>
        message(validators.validarConfirmacion(value, confirmation)),
    };
  }, [locale]);
}
