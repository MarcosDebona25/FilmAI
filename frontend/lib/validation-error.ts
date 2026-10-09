import type { CodedError } from "./errors";

/** Límites de las validaciones locales; la API conserva sus propios parámetros. */
export function validationError(code: string | null): CodedError | null {
  return code
    ? {
        code,
        params: {
          minAge: 13,
          minLength: code === "username_invalid" ? 5 : 8,
          maxLength: code === "max_length" ? 50 : code === "username_invalid" ? 25 : 20,
          specialCharacters: "@#$%&*!",
        },
      }
    : null;
}
